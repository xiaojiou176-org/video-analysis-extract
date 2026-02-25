from __future__ import annotations

from typing import Any

from worker.config import Settings
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore
from worker.temporal.activities_cleanup import cleanup_workspace_media_files
from worker.temporal.activities_delivery import (
    _claim_due_failed_deliveries,
    _build_retry_failure_payload,
    _classify_delivery_error,
    _extract_daily_digest_date,
    _extract_timezone_name,
    _extract_timezone_offset_minutes,
    _fetch_job_digest_record,
    _get_existing_daily_digest,
    _get_existing_video_digest,
    _get_or_init_notification_config,
    _insert_daily_digest_delivery,
    _insert_video_digest_delivery,
    _load_due_failed_deliveries,
    _mark_delivery_state,
    _prepare_delivery_skip_reason,
    _resolve_next_retry_at,
    retry_failed_deliveries_activity,
    send_daily_digest_activity,
    send_video_digest_activity,
)
from worker.temporal.activities_email import (
    is_sensitive_query_key as _is_sensitive_query_key,
    normalize_email as _normalize_email,
    render_markdown_html as _render_markdown_html,
    sanitize_text_preview as _sanitize_text_preview,
    sanitize_url_for_payload as _sanitize_url_for_payload,
    send_with_resend as _send_with_resend,
    to_html as _to_html,
)
from worker.temporal.activities_health import provider_canary_activity
from worker.temporal.activities_job_state import (
    _resolve_degradation_count,
    _resolve_last_error_code,
    _to_pipeline_final_status,
    mark_failed_activity,
    mark_running_activity,
    mark_succeeded_activity,
    reconcile_stale_queued_jobs_activity,
    run_pipeline_activity,
)
from worker.temporal.activities_poll import poll_feeds_activity, run_poll_feeds_once
from worker.temporal.activities_reports import (
    _build_daily_digest_markdown,
    _build_video_digest_markdown,
    _load_daily_digest_jobs,
    _safe_read_text,
)
from worker.temporal.activities_timing import (
    _build_local_day_window_utc,
    _coerce_int,
    _resolve_local_digest_date,
    _resolve_local_timezone,
    _utc_now_iso,
    resolve_daily_digest_timing_activity,
)

try:
    from temporalio import activity
except ModuleNotFoundError:  # pragma: no cover
    class _ActivityFallback:
        @staticmethod
        def defn(name: str | None = None):
            def _decorator(func):
                return func

            return _decorator

    activity = _ActivityFallback()


@activity.defn(name="cleanup_workspace_activity")
async def cleanup_workspace_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    payload = payload or {}
    older_than_hours = max(1, _coerce_int(payload.get("older_than_hours"), fallback=24))
    cache_older_than_hours = max(
        1,
        _coerce_int(
            payload.get("cache_older_than_hours"),
            fallback=older_than_hours,
        ),
    )
    cache_max_size_mb = max(
        1,
        _coerce_int(
            payload.get("cache_max_size_mb"),
            fallback=1024,
        ),
    )
    return cleanup_workspace_media_files(
        workspace_dir=str(payload.get("workspace_dir") or settings.pipeline_workspace_dir),
        older_than_hours=older_than_hours,
        cache_dir=(
            str(payload.get("cache_dir"))
            if isinstance(payload.get("cache_dir"), str) and str(payload.get("cache_dir")).strip()
            else None
        ),
        cache_older_than_hours=cache_older_than_hours,
        cache_max_size_mb=cache_max_size_mb,
    )


__all__ = [
    "Settings",
    "SQLiteStateStore",
    "PostgresBusinessStore",
    "_utc_now_iso",
    "_coerce_int",
    "_resolve_local_timezone",
    "_resolve_local_digest_date",
    "_build_local_day_window_utc",
    "resolve_daily_digest_timing_activity",
    "run_poll_feeds_once",
    "poll_feeds_activity",
    "_to_pipeline_final_status",
    "_resolve_degradation_count",
    "_resolve_last_error_code",
    "mark_running_activity",
    "reconcile_stale_queued_jobs_activity",
    "run_pipeline_activity",
    "mark_succeeded_activity",
    "mark_failed_activity",
    "_safe_read_text",
    "_build_video_digest_markdown",
    "_build_daily_digest_markdown",
    "_load_daily_digest_jobs",
    "_get_or_init_notification_config",
    "_prepare_delivery_skip_reason",
    "_classify_delivery_error",
    "_resolve_next_retry_at",
    "_mark_delivery_state",
    "_fetch_job_digest_record",
    "_insert_video_digest_delivery",
    "_insert_daily_digest_delivery",
    "_get_existing_video_digest",
    "_get_existing_daily_digest",
    "_claim_due_failed_deliveries",
    "_load_due_failed_deliveries",
    "_extract_daily_digest_date",
    "_extract_timezone_name",
    "_extract_timezone_offset_minutes",
    "_build_retry_failure_payload",
    "retry_failed_deliveries_activity",
    "provider_canary_activity",
    "send_video_digest_activity",
    "send_daily_digest_activity",
    "cleanup_workspace_media_files",
    "cleanup_workspace_activity",
    "_normalize_email",
    "_is_sensitive_query_key",
    "_sanitize_url_for_payload",
    "_sanitize_text_preview",
    "_render_markdown_html",
    "_to_html",
    "_send_with_resend",
]
