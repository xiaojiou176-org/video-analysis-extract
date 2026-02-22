from __future__ import annotations

from typing import Any

from worker.comments import (
    BilibiliCommentCollector,
    YouTubeCommentCollector,
)
from worker.config import Settings
from worker.pipeline import orchestrator
from worker.pipeline.policies import (
    apply_comments_policy as _apply_comments_policy,
    build_comments_policy as _build_comments_policy,
    build_frame_policy as _build_frame_policy,
    build_llm_policy as _build_llm_policy,
    build_llm_policy_section as _build_llm_policy_section,
    build_retry_policy as _build_retry_policy_impl,
    classify_error as _classify_error_impl,
    coerce_bool as _coerce_bool,
    coerce_float as _coerce_float,
    coerce_int as _coerce_int,
    coerce_str_list as _coerce_str_list,
    dedupe_keep_order as _dedupe_keep_order,
    default_comment_sort_for_platform as _default_comment_sort_for_platform,
    digest_is_chinese as _digest_is_chinese,
    extract_json_object as _extract_json_object,
    frame_paths_from_frames as _frame_paths_from_frames,
    llm_media_input_dimension as _llm_media_input_dimension,
    normalize_llm_input_mode as _normalize_llm_input_mode,
    normalize_overrides_payload as _normalize_overrides_payload,
    normalize_pipeline_mode as _normalize_pipeline_mode,
    outline_is_chinese as _outline_is_chinese,
    override_section as _override_section,
    refresh_llm_media_input_dimension as _refresh_llm_media_input_dimension,
    retry_delay_seconds as _retry_delay_seconds_impl,
)
from worker.pipeline.runner_rendering import (
    build_artifact_asset_url as _build_artifact_asset_url,
    build_chapters_markdown as _build_chapters_markdown,
    build_chapters_toc_markdown as _build_chapters_toc_markdown,
    build_code_blocks_markdown as _build_code_blocks_markdown,
    build_comments_markdown as _build_comments_markdown,
    build_comments_prompt_context as _build_comments_prompt_context,
    build_fallback_notes_markdown as _build_fallback_notes_markdown,
    build_frames_embedded_markdown as _build_frames_embedded_markdown,
    build_frames_markdown as _build_frames_markdown,
    build_frames_prompt_context as _build_frames_prompt_context,
    build_timestamp_refs_markdown as _build_timestamp_refs_markdown,
    collect_code_blocks as _collect_code_blocks,
    estimate_duration_seconds as _estimate_duration_seconds,
    extract_code_snippets as _extract_code_snippets,
    format_seconds as _format_seconds,
    load_digest_template as _load_digest_template,
    materialize_frames_for_artifacts as _materialize_frames_for_artifacts,
    parse_duration_seconds as _parse_duration_seconds,
    render_template as _render_template,
    should_include_frame_prompt as _should_include_frame_prompt,
    timestamp_link as _timestamp_link,
)
from worker.pipeline.step_executor import (
    append_degradation as _append_degradation,
    apply_state_updates as _apply_state_updates,
    build_mode_skip_step as _build_mode_skip_step,
    build_step_cache_info as _build_step_cache_info,
    execute_step as _execute_step,
    run_command as _run_command,
    run_command_once as _run_command_once,
)
from worker.pipeline.steps.artifacts import step_write_artifacts as _step_write_artifacts_impl
from worker.pipeline.steps.comments import step_collect_comments as _step_collect_comments_impl
from worker.pipeline.steps.embedding import step_build_embeddings as _step_build_embeddings_impl
from worker.pipeline.steps.frames import step_extract_frames as _step_extract_frames_impl
from worker.pipeline.steps.llm import (
    gemini_generate as _gemini_generate,
    normalize_digest_payload as _normalize_digest_payload,
    normalize_outline_payload as _normalize_outline_payload,
    step_llm_digest as _step_llm_digest_impl,
    step_llm_outline as _step_llm_outline_impl,
)
from worker.pipeline.steps.media import step_download_media as _step_download_media_impl
from worker.pipeline.steps.metadata import step_fetch_metadata as _step_fetch_metadata_impl
from worker.pipeline.steps.subtitles import (
    fetch_youtube_transcript_text as _fetch_youtube_transcript_text,
    step_collect_subtitles as _step_collect_subtitles_impl,
)
from worker.pipeline.types import (
    PIPELINE_STEPS,
    CommandResult,
    LLMInputMode,
    PIPELINE_MODE_FORCE_STEPS,
    PIPELINE_MODE_SKIP_STEPS,
    PIPELINE_MODE_SKIP_UPDATES,
    PipelineContext,
    PipelineMode,
    PipelineStatus,
    RetryCategory,
    STEP_INPUT_KEYS,
    STEP_SETTING_KEYS,
    STEP_VERSIONS,
    StepExecution,
    StepStatus,
)
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore


_build_context = orchestrator.build_context
_resolve_pipeline_status = orchestrator.resolve_pipeline_status


def _build_retry_policy(settings: Settings, step_name: str = "write_artifacts") -> dict[str, dict[str, float | int]]:
    return _build_retry_policy_impl(settings, step_name=step_name, llm_policy=None)


def _retry_delay_seconds(policy: dict[str, float | int], retries_used: int) -> float:
    return _retry_delay_seconds_impl(policy, retries_used)


def _classify_error(reason: str | None, error: str | None) -> RetryCategory:
    return _classify_error_impl(reason, error)


async def _step_fetch_metadata(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_fetch_metadata_impl(ctx, state, run_command=_run_command)


async def _step_download_media(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_download_media_impl(ctx, state, run_command=_run_command)


async def _step_collect_subtitles(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_collect_subtitles_impl(
        ctx,
        state,
        run_command=_run_command,
        fetch_youtube_transcript_text_fn=_fetch_youtube_transcript_text,
    )


async def _step_collect_comments(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_collect_comments_impl(
        ctx,
        state,
        bilibili_collector_cls=BilibiliCommentCollector,
        youtube_collector_cls=YouTubeCommentCollector,
    )


async def _step_extract_frames(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_extract_frames_impl(ctx, state, run_command=_run_command)


async def _step_llm_outline(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_llm_outline_impl(ctx, state, gemini_generate_fn=_gemini_generate)


async def _step_llm_digest(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_llm_digest_impl(ctx, state, gemini_generate_fn=_gemini_generate)


async def _step_write_artifacts(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_write_artifacts_impl(ctx, state)


async def _step_build_embeddings(ctx: PipelineContext, state: dict[str, Any]) -> StepExecution:
    return await _step_build_embeddings_impl(ctx, state)


async def run_pipeline(
    settings: Settings,
    sqlite_store: SQLiteStateStore,
    pg_store: PostgresBusinessStore,
    *,
    job_id: str,
    attempt: int,
    mode: str = "full",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    step_handlers = [
        ("fetch_metadata", _step_fetch_metadata, False),
        ("download_media", _step_download_media, False),
        ("collect_subtitles", _step_collect_subtitles, False),
        ("collect_comments", _step_collect_comments, False),
        ("extract_frames", _step_extract_frames, False),
        ("llm_outline", _step_llm_outline, False),
        ("llm_digest", _step_llm_digest, False),
        ("build_embeddings", _step_build_embeddings, False),
        ("write_artifacts", _step_write_artifacts, True),
    ]
    return await orchestrator.run_pipeline(
        settings,
        sqlite_store,
        pg_store,
        job_id=job_id,
        attempt=attempt,
        mode=mode,
        overrides=overrides,
        step_handlers=step_handlers,
    )
