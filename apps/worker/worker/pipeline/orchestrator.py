from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from worker.comments import (
    BilibiliCommentCollector,
    YouTubeCommentCollector,
    empty_comments_payload,
)
from worker.config import Settings
from worker.pipeline.policies import (
    build_comments_policy,
    build_frame_policy,
    build_llm_policy,
    normalize_llm_input_mode,
    normalize_overrides_payload,
    normalize_pipeline_mode,
    refresh_llm_media_input_dimension,
)
from worker.pipeline.step_executor import (
    build_mode_skip_step,
    ensure_dir,
    execute_step,
    run_command,
    utc_now_iso,
)
from worker.pipeline.steps import (
    step_collect_comments,
    step_collect_subtitles,
    step_download_media,
    step_extract_frames,
    step_fetch_metadata,
    step_llm_digest,
    step_llm_outline,
    step_write_artifacts,
)
from worker.pipeline.steps.llm import gemini_generate
from worker.pipeline.steps.subtitles import fetch_youtube_transcript_text
from worker.pipeline.types import (
    PIPELINE_MODE_FORCE_STEPS,
    PIPELINE_MODE_SKIP_STEPS,
    PIPELINE_STEPS,
    PipelineContext,
    PipelineStatus,
)
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore

StepHandler = Callable[[PipelineContext, dict[str, Any]], Any]


def build_context(
    settings: Settings,
    sqlite_store: SQLiteStateStore,
    pg_store: PostgresBusinessStore,
    *,
    job_id: str,
    attempt: int,
) -> PipelineContext:
    job_record = pg_store.get_job_with_video(job_id=job_id)

    root = ensure_dir(Path(settings.pipeline_workspace_dir).expanduser())
    work_dir = ensure_dir(root / job_id)
    cache_dir = ensure_dir(work_dir / "cache")
    download_dir = ensure_dir(work_dir / "downloads")
    frames_dir = ensure_dir(work_dir / "frames")
    artifact_root = ensure_dir(Path(settings.pipeline_artifact_root).expanduser())

    platform = str(job_record.get("platform") or "unknown")
    video_uid = str(job_record.get("video_uid") or "unknown")
    artifacts_dir = ensure_dir(artifact_root / platform / video_uid / job_id)

    return PipelineContext(
        settings=settings,
        sqlite_store=sqlite_store,
        pg_store=pg_store,
        job_id=job_id,
        attempt=attempt,
        job_record=job_record,
        work_dir=work_dir,
        cache_dir=cache_dir,
        download_dir=download_dir,
        frames_dir=frames_dir,
        artifacts_dir=artifacts_dir,
    )


def resolve_pipeline_status(
    step_records: dict[str, dict[str, Any]],
    degradations: list[dict[str, Any]] | None = None,
) -> PipelineStatus:
    statuses = [record.get("status") for record in step_records.values()]
    if any(status == "failed" for status in statuses):
        return "failed"

    if not all(status in {"succeeded", "skipped"} for status in statuses):
        return "failed"

    if degradations:
        return "degraded"

    return "succeeded"


def resolve_llm_gate(step_records: dict[str, dict[str, Any]]) -> tuple[bool, bool, str | None]:
    llm_steps = ("llm_outline", "llm_digest")
    llm_required = True
    hard_fail_reason: str | None = None

    for step_name in llm_steps:
        record = dict(step_records.get(step_name) or {})
        status = str(record.get("status") or "").strip().lower()
        if status == "failed":
            hard_fail_reason = (
                str(record.get("reason") or record.get("error") or "llm_step_failed").strip()
                or "llm_step_failed"
            )
            return llm_required, False, hard_fail_reason

    all_present = all(step_name in step_records for step_name in llm_steps)
    all_passed = all(
        str((step_records.get(step_name) or {}).get("status") or "").strip().lower()
        in {"succeeded", "skipped"}
        for step_name in llm_steps
    )
    if all_present and all_passed:
        return llm_required, True, None
    return llm_required, False, "llm_step_missing"


async def run_pipeline(
    settings: Settings,
    sqlite_store: SQLiteStateStore,
    pg_store: PostgresBusinessStore,
    *,
    job_id: str,
    attempt: int,
    mode: str = "full",
    overrides: dict[str, Any] | None = None,
    step_handlers: list[tuple[str, StepHandler, bool]] | None = None,
) -> dict[str, Any]:
    pipeline_mode = normalize_pipeline_mode(mode)
    llm_input_mode = normalize_llm_input_mode(getattr(settings, "pipeline_llm_input_mode", "auto"))
    ctx = build_context(settings, sqlite_store, pg_store, job_id=job_id, attempt=attempt)

    resolved_overrides = normalize_overrides_payload(overrides)
    if not resolved_overrides:
        resolved_overrides = normalize_overrides_payload(ctx.job_record.get("overrides_json"))

    platform = str(ctx.job_record.get("platform") or "").strip().lower()
    comments_policy = build_comments_policy(settings, resolved_overrides, platform=platform)
    frame_policy = build_frame_policy(settings, resolved_overrides)
    llm_policy = build_llm_policy(settings, resolved_overrides)

    checkpoint = sqlite_store.get_checkpoint(job_id)
    checkpoint_step = str((checkpoint or {}).get("last_completed_step") or "")
    checkpoint_payload = dict((checkpoint or {}).get("payload") or {})
    resume_upto_idx = (
        PIPELINE_STEPS.index(checkpoint_step) if checkpoint_step in PIPELINE_STEPS else -1
    )

    state: dict[str, Any] = {
        "job_id": job_id,
        "attempt": attempt,
        "mode": pipeline_mode,
        "source_url": ctx.job_record.get("source_url"),
        "title": ctx.job_record.get("title"),
        "platform": ctx.job_record.get("platform"),
        "video_uid": ctx.job_record.get("video_uid"),
        "published_at": ctx.job_record.get("published_at"),
        "overrides": resolved_overrides,
        "comments_policy": comments_policy,
        "frame_policy": frame_policy,
        "llm_policy": llm_policy,
        "metadata": {},
        "media_path": None,
        "download_mode": "text_only",
        "subtitle_files": [],
        "transcript": "",
        "comments": empty_comments_payload(),
        "frames": [],
        "llm_input_mode": llm_input_mode,
        "llm_media_input": {"video_available": False, "frame_count": 0},
        "outline": {},
        "digest": {},
        "artifacts": {},
        "degradations": [],
        "steps": {},
        "resume": {
            "checkpoint_step": checkpoint_step or None,
            "checkpoint_payload": checkpoint_payload,
            "resume_upto_idx": resume_upto_idx,
        },
    }
    refresh_llm_media_input_dimension(state)

    if step_handlers is None:
        step_handlers = [
            (
                "fetch_metadata",
                lambda ctx, state: step_fetch_metadata(ctx, state, run_command=run_command),
                False,
            ),
            (
                "download_media",
                lambda ctx, state: step_download_media(ctx, state, run_command=run_command),
                False,
            ),
            (
                "collect_subtitles",
                lambda ctx, state: step_collect_subtitles(
                    ctx,
                    state,
                    run_command=run_command,
                    fetch_youtube_transcript_text_fn=fetch_youtube_transcript_text,
                ),
                False,
            ),
            (
                "collect_comments",
                lambda ctx, state: step_collect_comments(
                    ctx,
                    state,
                    bilibili_collector_cls=BilibiliCommentCollector,
                    youtube_collector_cls=YouTubeCommentCollector,
                ),
                False,
            ),
            (
                "extract_frames",
                lambda ctx, state: step_extract_frames(ctx, state, run_command=run_command),
                False,
            ),
            (
                "llm_outline",
                lambda ctx, state: step_llm_outline(ctx, state, gemini_generate_fn=gemini_generate),
                True,
            ),
            (
                "llm_digest",
                lambda ctx, state: step_llm_digest(ctx, state, gemini_generate_fn=gemini_generate),
                True,
            ),
            ("write_artifacts", step_write_artifacts, True),
        ]

    mode_skip_steps = PIPELINE_MODE_SKIP_STEPS.get(pipeline_mode, set())
    mode_force_steps = PIPELINE_MODE_FORCE_STEPS.get(pipeline_mode, set())

    for step_idx, (step_name, handler, critical) in enumerate(step_handlers):
        is_mode_skipped = step_name in mode_skip_steps
        force_run = step_name in mode_force_steps or is_mode_skipped
        step_record = await execute_step(
            ctx,
            state,
            step_name=step_name,
            step_func=build_mode_skip_step(step_name, pipeline_mode)
            if is_mode_skipped
            else handler,
            critical=critical,
            resume_hint=(step_idx <= resume_upto_idx) and not force_run,
            force_run=force_run,
        )
        # LLM gate failed: stop the remaining pipeline steps immediately.
        # Continuing after a hard LLM failure can leave jobs in long-running states
        # while downstream steps wait on unavailable model responses.
        if step_name in {"llm_outline", "llm_digest"} and step_record.get("status") == "failed":
            state["fatal_error"] = f"{step_name}:{step_record.get('error') or step_record.get('reason') or 'failed'}"
            break

    final_status = resolve_pipeline_status(
        state["steps"],
        degradations=list(state.get("degradations") or []),
    )
    llm_required, llm_gate_passed, hard_fail_reason = resolve_llm_gate(state["steps"])

    return {
        "job_id": job_id,
        "attempt": attempt,
        "mode": pipeline_mode,
        "final_status": final_status,
        "steps": state["steps"],
        "artifact_dir": state.get("artifact_dir"),
        "artifacts": state.get("artifacts", {}),
        "degradations": state.get("degradations", []),
        "llm_required": llm_required,
        "llm_gate_passed": llm_gate_passed,
        "hard_fail_reason": hard_fail_reason,
        "llm_input_mode": state.get("llm_input_mode"),
        "llm_media_input": state.get("llm_media_input"),
        "resume": state.get("resume", {}),
        "fatal_error": state.get("fatal_error"),
        "completed_at": utc_now_iso(),
    }
