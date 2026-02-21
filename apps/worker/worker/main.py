from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from uuid import uuid4

from worker.config import Settings


async def _connect_temporal(settings: Settings):
    from temporalio.client import Client

    return await Client.connect(
        settings.temporal_target_host,
        namespace=settings.temporal_namespace,
    )


async def run_temporal_worker(settings: Settings) -> None:
    from temporalio.worker import Worker

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
    from worker.temporal.workflows import (
        CleanupWorkspaceWorkflow,
        DailyDigestWorkflow,
        PollFeedsWorkflow,
        ProcessJobWorkflow,
    )

    client = await _connect_temporal(settings)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            PollFeedsWorkflow,
            ProcessJobWorkflow,
            DailyDigestWorkflow,
            CleanupWorkspaceWorkflow,
        ],
        activities=[
            poll_feeds_activity,
            mark_running_activity,
            run_pipeline_activity,
            mark_succeeded_activity,
            mark_failed_activity,
            send_video_digest_activity,
            send_daily_digest_activity,
            cleanup_workspace_activity,
        ],
    )
    await worker.run()


async def start_poll_workflow(
    settings: Settings,
    *,
    subscription_id: str | None = None,
    platform: str | None = None,
    max_new_videos: int = 50,
) -> dict:
    from worker.temporal.workflows import PollFeedsWorkflow

    client = await _connect_temporal(settings)
    filters = {
        "subscription_id": subscription_id,
        "platform": platform,
        "max_new_videos": max_new_videos,
    }
    handle = await client.start_workflow(
        PollFeedsWorkflow.run,
        filters,
        id=f"poll-feeds-{uuid4()}",
        task_queue=settings.temporal_task_queue,
    )
    return await handle.result()


async def start_process_workflow(settings: Settings, job_id: str) -> dict:
    from worker.temporal.workflows import ProcessJobWorkflow

    client = await _connect_temporal(settings)
    handle = await client.start_workflow(
        ProcessJobWorkflow.run,
        job_id,
        id=f"process-job-{job_id}-{uuid4()}",
        task_queue=settings.temporal_task_queue,
    )
    return await handle.result()


def _local_utc_offset_minutes() -> int:
    offset = datetime.now().astimezone().utcoffset()
    if offset is None:
        return 0
    return int(offset.total_seconds() // 60)


async def start_daily_workflow(
    settings: Settings,
    *,
    run_once: bool = False,
    local_hour: int = 9,
    timezone_offset_minutes: int | None = None,
    workflow_id: str = "daily-digest-workflow",
) -> dict:
    from temporalio.exceptions import WorkflowAlreadyStartedError

    from worker.temporal.workflows import DailyDigestWorkflow

    offset_minutes = (
        timezone_offset_minutes
        if timezone_offset_minutes is not None
        else _local_utc_offset_minutes()
    )
    client = await _connect_temporal(settings)
    payload = {
        "run_once": run_once,
        "local_hour": int(local_hour),
        "timezone_offset_minutes": int(offset_minutes),
    }
    try:
        handle = await client.start_workflow(
            DailyDigestWorkflow.run,
            payload,
            id=workflow_id if not run_once else f"{workflow_id}-{uuid4()}",
            task_queue=settings.temporal_task_queue,
        )
    except WorkflowAlreadyStartedError:
        return {
            "ok": True,
            "workflow_id": workflow_id,
            "status": "already_running",
            "run_once": run_once,
        }

    if run_once:
        return await handle.result()

    run_id = getattr(handle, "first_execution_run_id", None) or getattr(handle, "run_id", None)
    return {
        "ok": True,
        "workflow_id": handle.id,
        "run_id": run_id,
        "status": "started",
        "run_once": False,
        "local_hour": int(local_hour),
        "timezone_offset_minutes": int(offset_minutes),
    }


async def start_cleanup_workflow(
    settings: Settings,
    *,
    older_than_hours: int = 24,
    workspace_dir: str | None = None,
) -> dict:
    from worker.temporal.workflows import CleanupWorkspaceWorkflow

    client = await _connect_temporal(settings)
    handle = await client.start_workflow(
        CleanupWorkspaceWorkflow.run,
        {
            "older_than_hours": max(1, int(older_than_hours)),
            "workspace_dir": workspace_dir,
        },
        id=f"cleanup-workspace-{uuid4()}",
        task_queue=settings.temporal_task_queue,
    )
    return await handle.result()


async def _main_async(args: argparse.Namespace) -> None:
    settings = Settings.from_env()

    if args.command == "run-worker":
        await run_temporal_worker(settings)
        return
    if args.command == "start-poll-workflow":
        output = await start_poll_workflow(
            settings,
            subscription_id=args.subscription_id,
            platform=args.platform,
            max_new_videos=args.max_new_videos,
        )
    elif args.command == "start-process-workflow":
        output = await start_process_workflow(settings, job_id=args.job_id)
    elif args.command == "start-daily-workflow":
        output = await start_daily_workflow(
            settings,
            run_once=args.run_once,
            local_hour=args.local_hour,
            timezone_offset_minutes=args.timezone_offset_minutes,
            workflow_id=args.workflow_id,
        )
    elif args.command == "start-cleanup-workflow":
        output = await start_cleanup_workflow(
            settings,
            older_than_hours=args.older_than_hours,
            workspace_dir=args.workspace_dir,
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(json.dumps(output, ensure_ascii=False, indent=2))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Worker entrypoint")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run-worker", help="Run Temporal worker loop")

    start_poll = sub.add_parser(
        "start-poll-workflow",
        help="Start PollFeedsWorkflow via Temporal",
    )
    start_poll.add_argument("--subscription-id", default=None)
    start_poll.add_argument("--platform", default=None, choices=["bilibili", "youtube"])
    start_poll.add_argument("--max-new-videos", type=int, default=50)

    start_process = sub.add_parser(
        "start-process-workflow",
        help="Start ProcessJobWorkflow via Temporal",
    )
    start_process.add_argument("--job-id", required=True, help="Job UUID to process")

    start_daily = sub.add_parser(
        "start-daily-workflow",
        help="Start DailyDigestWorkflow via Temporal",
    )
    start_daily.add_argument(
        "--run-once",
        action="store_true",
        help="Run once immediately and wait for result",
    )
    start_daily.add_argument(
        "--local-hour",
        type=int,
        default=9,
        help="Daily local trigger hour for scheduler mode",
    )
    start_daily.add_argument(
        "--timezone-offset-minutes",
        type=int,
        default=None,
        help="UTC offset minutes for local time; defaults to host local offset",
    )
    start_daily.add_argument(
        "--workflow-id",
        default="daily-digest-workflow",
        help="Temporal workflow id used for scheduler mode",
    )

    start_cleanup = sub.add_parser(
        "start-cleanup-workflow",
        help="Start CleanupWorkspaceWorkflow via Temporal",
    )
    start_cleanup.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="Delete workspace media/frame files older than this many hours",
    )
    start_cleanup.add_argument(
        "--workspace-dir",
        default=None,
        help="Optional workspace root override",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
