from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.temporal.activities import (
        cleanup_workspace_activity,
        mark_failed_activity,
        mark_running_activity,
        mark_succeeded_activity,
        poll_feeds_activity,
        run_pipeline_activity,
        send_daily_digest_activity,
        send_video_digest_activity,
    )


@workflow.defn(name="PollFeedsWorkflow")
class PollFeedsWorkflow:
    @workflow.run
    async def run(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        poll_result = await workflow.execute_activity(
            poll_feeds_activity,
            filters or {},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        created_job_ids = list(poll_result.get("created_job_ids", []))
        process_results: list[dict[str, Any]] = []
        for job_id in created_job_ids:
            child_result = await workflow.execute_child_workflow(
                ProcessJobWorkflow.run,
                str(job_id),
                id=f"process-job-{job_id}-{workflow.info().run_id}",
                task_queue=workflow.info().task_queue,
            )
            process_results.append(child_result)

        return {
            **poll_result,
            "dispatched_process_workflows": len(created_job_ids),
            "process_results": process_results,
        }


@workflow.defn(name="ProcessJobWorkflow")
class ProcessJobWorkflow:
    @workflow.run
    async def run(self, job: str | dict[str, Any]) -> dict[str, Any]:
        requested_mode: str | None = None
        requested_overrides: dict[str, Any] | None = None
        if isinstance(job, dict):
            job_id = str(job.get("job_id") or "").strip()
            if not job_id:
                raise ValueError("ProcessJobWorkflow requires job_id")
            mode_raw = job.get("mode")
            if isinstance(mode_raw, str):
                requested_mode = mode_raw.strip() or None
            overrides_raw = job.get("overrides")
            if isinstance(overrides_raw, dict):
                requested_overrides = dict(overrides_raw)
        else:
            job_id = str(job).strip()
            if not job_id:
                raise ValueError("ProcessJobWorkflow requires job_id")

        running = await workflow.execute_activity(
            mark_running_activity,
            job_id,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        payload = {"job_id": job_id, "attempt": int(running["attempt"])}
        if requested_mode is not None:
            payload["mode"] = requested_mode
        if requested_overrides is not None:
            payload["overrides"] = requested_overrides

        try:
            pipeline_result = await workflow.execute_activity(
                run_pipeline_activity,
                payload,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            final_status = str(pipeline_result.get("final_status", "failed"))
            if final_status == "failed":
                failed = await workflow.execute_activity(
                    mark_failed_activity,
                    {
                        **payload,
                        "error": str(
                            pipeline_result.get("fatal_error")
                            or "pipeline_failed"
                        ),
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
                return {
                    "ok": False,
                    "job_id": job_id,
                    "attempt": payload["attempt"],
                    "status": failed["status"],
                    "pipeline": pipeline_result,
                    "error": str(
                        pipeline_result.get("fatal_error") or "pipeline_failed"
                    ),
                }

            succeeded = await workflow.execute_activity(
                mark_succeeded_activity,
                {
                    **payload,
                    "final_status": final_status,
                    "artifacts": pipeline_result.get("artifacts", {}),
                    "artifact_dir": pipeline_result.get("artifact_dir"),
                },
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
            try:
                notification_result = await workflow.execute_activity(
                    send_video_digest_activity,
                    {
                        "job_id": job_id,
                        "final_status": final_status,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
            except Exception as notification_exc:
                notification_result = {
                    "ok": False,
                    "job_id": job_id,
                    "error": str(notification_exc),
                    "status": "failed",
                }
            return {
                "ok": final_status != "failed",
                "job_id": job_id,
                "attempt": payload["attempt"],
                "pipeline": pipeline_result,
                "status": succeeded["status"],
                "db_status": succeeded.get("db_status"),
                "video_digest": notification_result,
            }
        except Exception as exc:
            failed = await workflow.execute_activity(
                mark_failed_activity,
                {**payload, "error": str(exc)},
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            return {
                "ok": False,
                "job_id": job_id,
                "attempt": payload["attempt"],
                "status": failed["status"],
                "error": str(exc),
            }


@workflow.defn(name="DailyDigestWorkflow")
class DailyDigestWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        config = payload or {}
        run_once = bool(config.get("run_once", False))
        offset_minutes = int(config.get("timezone_offset_minutes", 0))
        target_hour = max(0, min(23, int(config.get("local_hour", 9))))

        latest_result: dict[str, Any] = {
            "ok": True,
            "runs": 0,
        }
        run_count = 0

        while True:
            now_utc = workflow.now()
            now_local = now_utc + timedelta(minutes=offset_minutes)
            scheduled_today = now_local.replace(
                hour=target_hour,
                minute=0,
                second=0,
                microsecond=0,
            )
            if now_local < scheduled_today and not run_once:
                await workflow.sleep(scheduled_today - now_local)
                now_utc = workflow.now()
                now_local = now_utc + timedelta(minutes=offset_minutes)

            digest_date = now_local.date().isoformat()
            activity_result = await workflow.execute_activity(
                send_daily_digest_activity,
                {
                    "digest_date": digest_date,
                    "timezone_offset_minutes": offset_minutes,
                },
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
            run_count += 1
            latest_result = {
                **activity_result,
                "runs": run_count,
            }

            if run_once:
                return latest_result

            next_run_local = scheduled_today + timedelta(days=1)
            now_local = workflow.now() + timedelta(minutes=offset_minutes)
            sleep_for = next_run_local - now_local
            if sleep_for.total_seconds() < 1:
                sleep_for = timedelta(minutes=1)
            await workflow.sleep(sleep_for)


@workflow.defn(name="CleanupWorkspaceWorkflow")
class CleanupWorkspaceWorkflow:
    @workflow.run
    async def run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await workflow.execute_activity(
            cleanup_workspace_activity,
            payload or {},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
