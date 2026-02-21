from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from html import escape
from os import getpid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
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

from worker.config import Settings
from worker.rss.normalizer import normalize_entry
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore
from worker.temporal.activities_cleanup import cleanup_workspace_media_files
from worker.temporal.activities_email import (
    is_sensitive_query_key as _is_sensitive_query_key,
    normalize_email as _normalize_email,
    render_markdown_html as _render_markdown_html,
    sanitize_text_preview as _sanitize_text_preview,
    sanitize_url_for_payload as _sanitize_url_for_payload,
    send_with_resend as _send_with_resend,
    to_html as _to_html,
)
from sqlalchemy import text

PIPELINE_FINAL_STATUSES = {"succeeded", "partial", "failed"}
DELIVERY_MAX_ATTEMPTS = 5
DELIVERY_RETRY_BACKOFF_MINUTES = [2, 5, 15, 30, 60]
HEALTH_CHECK_KINDS = ("rsshub", "youtube_data_api", "gemini", "resend")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _coerce_int(value: Any, *, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith(("+", "-")):
            sign = -1 if raw.startswith("-") else 1
            raw = raw[1:]
        else:
            sign = 1
        if raw.isdigit():
            return int(raw) * sign
    return fallback


def _local_tz_from_offset(offset_minutes: int) -> timezone:
    return timezone(timedelta(minutes=offset_minutes))


def _resolve_local_timezone(
    *,
    timezone_name: str | None,
    offset_minutes: int,
) -> tuple[tzinfo, str]:
    if isinstance(timezone_name, str) and timezone_name.strip():
        normalized = timezone_name.strip()
        try:
            return ZoneInfo(normalized), normalized
        except ZoneInfoNotFoundError:
            pass
    return _local_tz_from_offset(offset_minutes), f"offset:{offset_minutes}"


def _resolve_local_digest_date(
    *,
    digest_date: str | None,
    timezone_name: str | None = None,
    offset_minutes: int = 0,
) -> date:
    if digest_date:
        return date.fromisoformat(digest_date)
    local_tz, _ = _resolve_local_timezone(
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )
    local_now = datetime.now(timezone.utc).astimezone(local_tz)
    return local_now.date()


def _build_local_day_window_utc(
    *,
    local_day: date,
    timezone_name: str | None = None,
    offset_minutes: int = 0,
) -> tuple[datetime, datetime]:
    local_tz, _ = _resolve_local_timezone(
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )
    start_local = datetime.combine(local_day, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


@activity.defn(name="resolve_daily_digest_timing_activity")
async def resolve_daily_digest_timing_activity(
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = payload or {}
    run_once = bool(config.get("run_once", False))
    timezone_name = str(config.get("timezone_name") or "").strip() or None
    offset_minutes = _coerce_int(config.get("timezone_offset_minutes"), fallback=0)
    target_hour = max(0, min(23, _coerce_int(config.get("local_hour"), fallback=9)))

    local_tz, resolved_timezone = _resolve_local_timezone(
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    scheduled_today = now_local.replace(hour=target_hour, minute=0, second=0, microsecond=0)

    wait_before_seconds = 0
    run_local = now_local
    if now_local < scheduled_today and not run_once:
        wait_before_seconds = int((scheduled_today - now_local).total_seconds())
        run_local = scheduled_today

    digest_date = run_local.date().isoformat()
    run_utc = run_local.astimezone(timezone.utc)
    next_run_local = datetime.combine(
        run_local.date() + timedelta(days=1),
        time(hour=target_hour),
        tzinfo=local_tz,
    )
    wait_after_seconds = int((next_run_local.astimezone(timezone.utc) - run_utc).total_seconds())
    if wait_after_seconds < 1:
        wait_after_seconds = 60

    return {
        "ok": True,
        "digest_date": digest_date,
        "wait_before_run_seconds": wait_before_seconds,
        "wait_after_run_seconds": wait_after_seconds,
        "timezone_name": resolved_timezone,
        "timezone_offset_minutes": int(
            now_local.utcoffset().total_seconds() // 60
        )
        if now_local.utcoffset()
        else offset_minutes,
    }


def _safe_read_text(path: str | None) -> str | None:
    if not path:
        return None
    try:
        file_path = Path(path).expanduser()
    except OSError:
        return None
    if not file_path.is_file():
        return None
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _build_video_digest_markdown(job: dict[str, Any], digest_markdown: str | None) -> str:
    source_url = str(job.get("source_url") or "").strip()
    digest_body = str(digest_markdown or "").strip()
    if not digest_body:
        digest_body = "## 视频摘要\n\n（摘要文件不存在或为空）"

    metadata_lines = [
        "## 投递信息",
        "",
        f"- Job ID：{job['job_id']}",
        f"- 平台：{job.get('platform') or 'unknown'}",
        f"- 视频 UID：{job.get('video_uid') or 'unknown'}",
        f"- 状态：{job.get('status') or 'unknown'}",
    ]
    if source_url:
        metadata_lines.append(f"- 原视频：{source_url}")

    return f"{digest_body}\n\n---\n\n" + "\n".join(metadata_lines).strip()


def _build_daily_digest_markdown(
    *,
    digest_day: date,
    offset_minutes: int = 0,
    timezone_name: str | None = None,
    jobs: list[dict[str, Any]],
) -> str:
    local_tz, tz_label = _resolve_local_timezone(
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )
    generated_at = datetime.now(timezone.utc).astimezone(local_tz).replace(microsecond=0)
    succeeded_count = sum(1 for item in jobs if str(item.get("status")) == "succeeded")
    partial_count = sum(1 for item in jobs if str(item.get("status")) == "partial")

    lines = [
        f"# Daily Digest {digest_day.isoformat()}",
        "",
        f"- Generated at: {generated_at.isoformat()}",
        f"- Timezone: {tz_label}",
        f"- Timezone offset minutes: {int(generated_at.utcoffset().total_seconds() // 60) if generated_at.utcoffset() else 0}",
        f"- Total jobs: {len(jobs)}",
        f"- Succeeded: {succeeded_count}",
        f"- Partial: {partial_count}",
        "",
    ]

    if not jobs:
        lines.append("_No succeeded/partial jobs for this date._")
        return "\n".join(lines).strip()

    lines.extend(
        [
            "| Updated (UTC) | Job ID | Status | Platform | Title |",
            "|---|---|---|---|---|",
        ]
    )
    for item in jobs:
        updated_at = item.get("updated_at")
        updated_text = (
            updated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat()
            if isinstance(updated_at, datetime)
            else "-"
        )
        title = str(item.get("title") or "Untitled").replace("|", "\\|")
        lines.append(
            "| {updated} | {job_id} | {status} | {platform} | {title} |".format(
                updated=updated_text,
                job_id=item.get("job_id") or "-",
                status=item.get("status") or "-",
                platform=item.get("platform") or "-",
                title=title,
            )
        )

    return "\n".join(lines).strip()


def _resolve_feed_url(settings: Settings, rsshub_route: str) -> str:
    if rsshub_route.startswith("http://") or rsshub_route.startswith("https://"):
        return rsshub_route
    base = settings.rsshub_base_url.rstrip("/")
    path = rsshub_route if rsshub_route.startswith("/") else f"/{rsshub_route}"
    return f"{base}{path}"


def _to_pipeline_final_status(value: Any, *, fallback: str | None) -> str | None:
    for candidate in (value, fallback):
        if not isinstance(candidate, str):
            continue
        normalized = candidate.strip().lower()
        if normalized in PIPELINE_FINAL_STATUSES:
            return normalized
    return None


def _coerce_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            return int(raw)
    return None


def _resolve_degradation_count(payload: dict[str, Any]) -> int | None:
    explicit = _coerce_non_negative_int(payload.get("degradation_count"))
    if explicit is not None:
        return explicit
    degradations = payload.get("degradations")
    if isinstance(degradations, list):
        return len(degradations)
    return 0


def _sanitize_error_code(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().splitlines()[0].strip()
    if not code:
        return None
    return code[:128]


def _derive_error_code(value: Any) -> str | None:
    raw = _sanitize_error_code(value)
    if raw is None:
        return None
    prefix = raw.split(":", 1)[0].strip()
    return (prefix or raw)[:128]


def _resolve_last_error_code(payload: dict[str, Any]) -> str | None:
    direct = _sanitize_error_code(payload.get("last_error_code")) or _sanitize_error_code(
        payload.get("error_code")
    )
    if direct is not None:
        return direct

    degradations = payload.get("degradations")
    if isinstance(degradations, list):
        for item in reversed(degradations):
            if not isinstance(item, dict):
                continue
            for key in ("error_code", "error_kind", "reason"):
                candidate = _sanitize_error_code(item.get(key))
                if candidate is not None:
                    return candidate

    return _derive_error_code(payload.get("fatal_error")) or _derive_error_code(payload.get("error"))


async def run_poll_feeds_once(
    settings: Settings,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from worker.rss.fetcher import RSSHubFetcher

    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)
    lock_owner = f"pid-{getpid()}"
    lock_key = "phase2.poll_feeds"

    if not sqlite_store.acquire_lock(lock_key, lock_owner, settings.lock_ttl_seconds):
        return {"ok": True, "skipped": True, "reason": "lock_not_acquired"}

    filters = filters or {}
    try:
        subscriptions = pg_store.list_subscriptions(
            subscription_id=filters.get("subscription_id"),
            platform=filters.get("platform"),
        )

        feed_to_subscription: dict[str, dict[str, Any]] = {}
        for item in subscriptions:
            feed_url = _resolve_feed_url(settings, item["rsshub_route"])
            feed_to_subscription[feed_url] = item

        feed_urls = list(feed_to_subscription.keys())
        fetcher = RSSHubFetcher(
            timeout_seconds=settings.request_timeout_seconds,
            retry_attempts=settings.request_retry_attempts,
            retry_backoff_seconds=settings.request_retry_backoff_seconds,
        )
        fetched = await fetcher.fetch_many(feed_urls)

        created_job_ids: list[str] = []
        candidates: list[dict[str, Any]] = []
        max_new = int(filters.get("max_new_videos") or 50)

        entries_fetched = 0
        entries_normalized = 0
        ingest_events_created = 0
        ingest_event_duplicates = 0
        job_duplicates = 0

        for feed_url, raw_entries in fetched.items():
            subscription = feed_to_subscription.get(feed_url)
            if not subscription:
                continue

            entries_fetched += len(raw_entries)
            for raw_entry in raw_entries:
                normalized = normalize_entry(raw_entry, feed_url)
                entries_normalized += 1

                platform = normalized.get("video_platform")
                if platform not in {"bilibili", "youtube"}:
                    continue

                video = pg_store.upsert_video(
                    platform=platform,
                    video_uid=normalized["video_uid"],
                    source_url=normalized.get("link") or feed_url,
                    title=normalized.get("title") or None,
                    published_at=normalized.get("published_at"),
                )

                ingest_event, event_created = pg_store.create_ingest_event(
                    subscription_id=subscription["id"],
                    feed_guid=normalized.get("guid"),
                    feed_link=normalized.get("link"),
                    entry_hash=normalized["entry_hash"],
                    video_id=video["id"],
                )
                if event_created:
                    ingest_events_created += 1
                else:
                    ingest_event_duplicates += 1

                existing_job = pg_store.find_active_job(
                    idempotency_key=normalized["idempotency_key"]
                )
                if existing_job is not None:
                    job_duplicates += 1
                    continue

                job, created = pg_store.create_queued_job(
                    video_id=video["id"],
                    idempotency_key=normalized["idempotency_key"],
                )
                if not created:
                    job_duplicates += 1
                    continue

                created_job_ids.append(job["id"])
                if len(candidates) < max_new:
                    candidates.append(
                        {
                            "job_id": job["id"],
                            "video_id": video["id"],
                            "platform": video["platform"],
                            "video_uid": video["video_uid"],
                            "source_url": video["source_url"],
                            "title": video.get("title"),
                            "published_at": video.get("published_at"),
                            "entry_hash": normalized["entry_hash"],
                            "ingest_event_id": ingest_event["id"],
                        }
                    )

        return {
            "ok": True,
            "phase": "phase2",
            "feeds_polled": len(feed_urls),
            "entries_fetched": entries_fetched,
            "entries_normalized": entries_normalized,
            "ingest_events_created": ingest_events_created,
            "ingest_event_duplicates": ingest_event_duplicates,
            "jobs_created": len(created_job_ids),
            "job_duplicates": job_duplicates,
            "created_job_ids": created_job_ids,
            "candidates": candidates,
            "at": _utc_now_iso(),
            "filters": filters,
        }
    finally:
        sqlite_store.release_lock(lock_key, lock_owner)


@activity.defn(name="poll_feeds_activity")
async def poll_feeds_activity(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    return await run_poll_feeds_once(settings, filters=filters)


@activity.defn(name="mark_running_activity")
async def mark_running_activity(job_id: str) -> dict[str, Any]:
    settings = Settings.from_env()
    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)

    attempt = sqlite_store.next_attempt(job_id=job_id)
    sqlite_store.mark_step_running(job_id=job_id, step_name="mark_running", attempt=attempt)

    running_job = pg_store.mark_job_running(job_id=job_id)
    if running_job.get("status") != "running":
        sqlite_store.mark_step_finished(
            job_id=job_id,
            step_name="mark_running",
            attempt=attempt,
            status="failed",
            error_payload={"reason": f"invalid_status:{running_job.get('status')}"},
        )
        raise ValueError(f"job {job_id} is not runnable, status={running_job.get('status')}")

    sqlite_store.mark_step_finished(
        job_id=job_id,
        step_name="mark_running",
        attempt=attempt,
        status="succeeded",
    )
    sqlite_store.update_checkpoint(job_id=job_id, last_completed_step="mark_running")
    return {"job_id": job_id, "attempt": attempt, "status": "running"}


@activity.defn(name="run_pipeline_activity")
async def run_pipeline_activity(payload: dict[str, Any]) -> dict[str, Any]:
    from worker.pipeline.runner import run_pipeline

    settings = Settings.from_env()
    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)

    job_id = str(payload["job_id"])
    attempt = int(payload["attempt"])
    mode = str(payload.get("mode") or "").strip() or None
    payload_overrides = payload.get("overrides")
    overrides = dict(payload_overrides) if isinstance(payload_overrides, dict) else None
    if mode is None or overrides is None:
        job_record = pg_store.get_job_with_video(job_id=job_id)
        if mode is None:
            mode = str(job_record.get("mode") or "").strip() or "full"
        if overrides is None:
            job_overrides = job_record.get("overrides_json")
            if isinstance(job_overrides, dict):
                overrides = dict(job_overrides)

    return await run_pipeline(
        settings,
        sqlite_store,
        pg_store,
        job_id=job_id,
        attempt=attempt,
        mode=mode,
        overrides=overrides,
    )


@activity.defn(name="mark_succeeded_activity")
async def mark_succeeded_activity(payload: dict[str, Any]) -> dict[str, Any]:
    settings = Settings.from_env()
    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)

    job_id = str(payload["job_id"])
    attempt = int(payload["attempt"])
    final_status = str(payload.get("final_status", "succeeded"))
    artifacts = payload.get("artifacts") or {}
    digest_path = artifacts.get("digest")
    artifact_root = payload.get("artifact_dir")
    pipeline_final_status = _to_pipeline_final_status(
        payload.get("pipeline_final_status"), fallback=final_status
    ) or "succeeded"
    degradation_count = _resolve_degradation_count(payload)
    last_error_code = _resolve_last_error_code(payload)
    step_name = "mark_succeeded"

    sqlite_store.mark_step_running(job_id=job_id, step_name=step_name, attempt=attempt)
    job = pg_store.mark_job_succeeded(
        job_id=job_id,
        status="partial" if final_status == "partial" else "succeeded",
        artifact_digest_md=str(digest_path) if digest_path else None,
        artifact_root=str(artifact_root) if artifact_root else None,
        pipeline_final_status=pipeline_final_status,
        degradation_count=degradation_count,
        last_error_code=last_error_code,
    )
    sqlite_store.mark_step_finished(
        job_id=job_id,
        step_name=step_name,
        attempt=attempt,
        status="succeeded",
    )
    sqlite_store.update_checkpoint(job_id=job_id, last_completed_step=step_name)
    # Keep database status compatible with existing API/contracts while allowing
    # workflow-level partial status for degraded pipeline runs.
    return {
        "job_id": job_id,
        "attempt": attempt,
        "status": final_status,
        "db_status": job["status"],
        "pipeline_final_status": job.get("pipeline_final_status"),
        "degradation_count": job.get("degradation_count"),
        "last_error_code": job.get("last_error_code"),
    }


@activity.defn(name="mark_failed_activity")
async def mark_failed_activity(payload: dict[str, Any]) -> dict[str, Any]:
    settings = Settings.from_env()
    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)

    job_id = str(payload["job_id"])
    attempt = int(payload["attempt"])
    error = str(payload.get("error", "unknown_error"))
    pipeline_final_status = _to_pipeline_final_status(
        payload.get("pipeline_final_status"), fallback="failed"
    ) or "failed"
    degradation_count = _resolve_degradation_count(payload)
    last_error_code = _resolve_last_error_code(payload)
    step_name = "mark_failed"

    sqlite_store.mark_step_running(job_id=job_id, step_name=step_name, attempt=attempt)
    job = pg_store.mark_job_failed(
        job_id=job_id,
        error_message=error,
        pipeline_final_status=pipeline_final_status,
        degradation_count=degradation_count,
        last_error_code=last_error_code,
    )
    sqlite_store.mark_step_finished(
        job_id=job_id,
        step_name=step_name,
        attempt=attempt,
        status="failed",
        error_payload={"error": error, "last_error_code": last_error_code},
    )
    sqlite_store.update_checkpoint(job_id=job_id, last_completed_step=step_name)
    return {
        "job_id": job_id,
        "attempt": attempt,
        "status": job["status"],
        "last_error_code": job.get("last_error_code"),
    }


def _get_or_init_notification_config(conn: Any) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT
                enabled,
                to_email,
                daily_digest_enabled
            FROM notification_configs
            WHERE singleton_key = 1
            LIMIT 1
            """
        )
    ).mappings().first()
    if row is not None:
        return dict(row)

    conn.execute(
        text(
            """
            INSERT INTO notification_configs (
                singleton_key,
                enabled,
                daily_digest_enabled,
                failure_alert_enabled,
                created_at,
                updated_at
            )
            VALUES (1, FALSE, FALSE, TRUE, NOW(), NOW())
            ON CONFLICT (singleton_key) DO NOTHING
            """
        )
    )
    loaded = conn.execute(
        text(
            """
            SELECT
                enabled,
                to_email,
                daily_digest_enabled
            FROM notification_configs
            WHERE singleton_key = 1
            LIMIT 1
            """
        )
    ).mappings().first()
    if loaded is None:
        return {"enabled": False, "to_email": None, "daily_digest_enabled": False}
    return dict(loaded)


def _prepare_delivery_skip_reason(
    *,
    config: dict[str, Any],
    recipient_email: str | None,
    notification_enabled: bool,
    require_daily_digest: bool = False,
) -> str | None:
    if recipient_email is None:
        return "notification recipient email is not configured"
    if not notification_enabled:
        return "notification is disabled by environment"
    if not bool(config.get("enabled")):
        return "notification config is disabled"
    if require_daily_digest and not bool(config.get("daily_digest_enabled")):
        return "daily digest is disabled"
    return None


def _classify_delivery_error(error_message: str) -> str:
    normalized = error_message.strip().lower()
    if not normalized:
        return "transient"

    if "not configured" in normalized:
        return "config_error"
    if "401" in normalized or "403" in normalized or "unauthorized" in normalized:
        return "auth"
    if "429" in normalized or "rate limit" in normalized:
        return "rate_limit"
    if any(
        token in normalized
        for token in (
            "timeout",
            "timed out",
            "connection",
            "network",
            "tempor",
            "dns",
            "502",
            "503",
            "504",
        )
    ):
        return "transient"
    return "transient"


def _resolve_retry_backoff_minutes(*, attempt_count: int) -> int:
    index = max(0, min(attempt_count - 1, len(DELIVERY_RETRY_BACKOFF_MINUTES) - 1))
    return DELIVERY_RETRY_BACKOFF_MINUTES[index]


def _resolve_next_retry_at(
    *,
    attempt_count: int,
    error_kind: str | None,
    now_utc: datetime | None = None,
) -> datetime | None:
    if error_kind in {"auth", "config_error"}:
        return None
    if attempt_count >= DELIVERY_MAX_ATTEMPTS:
        return None
    baseline = now_utc or datetime.now(timezone.utc)
    backoff_minutes = _resolve_retry_backoff_minutes(attempt_count=attempt_count)
    return baseline + timedelta(minutes=backoff_minutes)


def _mark_delivery_state(
    pg_store: PostgresBusinessStore,
    *,
    delivery_id: str,
    status: str,
    error_message: str | None = None,
    provider_message_id: str | None = None,
    sent: bool = False,
    record_attempt: bool = False,
    last_error_kind: str | None = None,
    next_retry_at: datetime | None = None,
    clear_retry_meta: bool = False,
) -> dict[str, Any]:
    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        row = conn.execute(
            text(
                """
                UPDATE notification_deliveries
                SET
                    status = :status,
                    error_message = :error_message,
                    provider_message_id = :provider_message_id,
                    sent_at = CASE WHEN :sent THEN NOW() ELSE sent_at END,
                    attempt_count = CASE
                        WHEN :record_attempt THEN attempt_count + 1
                        ELSE attempt_count
                    END,
                    last_attempt_at = CASE
                        WHEN :record_attempt THEN NOW()
                        ELSE last_attempt_at
                    END,
                    last_error_kind = CASE
                        WHEN :clear_retry_meta THEN NULL
                        WHEN CAST(:last_error_kind AS TEXT) IS NULL THEN last_error_kind
                        ELSE CAST(:last_error_kind AS TEXT)
                    END,
                    next_retry_at = CASE
                        WHEN :clear_retry_meta THEN NULL
                        ELSE CAST(:next_retry_at AS TIMESTAMPTZ)
                    END
                WHERE id = CAST(:delivery_id AS UUID)
                RETURNING
                    id::text AS delivery_id,
                    status,
                    provider_message_id,
                    error_message,
                    sent_at,
                    attempt_count,
                    last_attempt_at,
                    next_retry_at,
                    last_error_kind
                """
            ),
            {
                "delivery_id": delivery_id,
                "status": status,
                "error_message": error_message,
                "provider_message_id": provider_message_id,
                "sent": sent,
                "record_attempt": record_attempt,
                "last_error_kind": last_error_kind,
                "next_retry_at": next_retry_at,
                "clear_retry_meta": clear_retry_meta,
            },
        ).mappings().one()
    return dict(row)


def _fetch_job_digest_record(conn: Any, *, job_id: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT
                j.id::text AS job_id,
                j.status,
                j.pipeline_final_status,
                j.artifact_digest_md,
                j.updated_at,
                v.platform,
                v.video_uid,
                v.title,
                v.source_url
            FROM jobs j
            JOIN videos v ON v.id = j.video_id
            WHERE j.id = CAST(:job_id AS UUID)
            LIMIT 1
            """
        ),
        {"job_id": job_id},
    ).mappings().first()
    if row is None:
        raise ValueError(f"job not found: {job_id}")
    return dict(row)


def _insert_video_digest_delivery(
    conn: Any,
    *,
    job: dict[str, Any],
    recipient_email: str,
    subject: str,
    payload_json: dict[str, Any],
) -> dict[str, Any] | None:
    conn.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"video_digest:{job['job_id']}"},
    )
    existing = conn.execute(
        text(
            """
            SELECT
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                provider_message_id,
                error_message,
                sent_at,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            FROM notification_deliveries
            WHERE kind = 'video_digest'
              AND job_id = CAST(:job_id AS UUID)
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"job_id": job["job_id"]},
    ).mappings().first()
    if existing is not None:
        return None

    created = conn.execute(
        text(
            """
            INSERT INTO notification_deliveries (
                kind,
                status,
                recipient_email,
                subject,
                provider,
                payload_json,
                job_id,
                created_at
            )
            VALUES (
                'video_digest',
                'queued',
                :recipient_email,
                :subject,
                'resend',
                CAST(:payload_json AS JSONB),
                CAST(:job_id AS UUID),
                NOW()
            )
            RETURNING
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            """
        ),
        {
            "recipient_email": recipient_email,
            "subject": subject,
            "payload_json": json.dumps(payload_json, ensure_ascii=False),
            "job_id": job["job_id"],
        },
    ).mappings().one()
    return dict(created)


def _insert_daily_digest_delivery(
    conn: Any,
    *,
    digest_date: date,
    recipient_email: str,
    subject: str,
    payload_json: dict[str, Any],
) -> dict[str, Any] | None:
    conn.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"daily_digest:{digest_date.isoformat()}"},
    )
    existing = conn.execute(
        text(
            """
            SELECT
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                provider_message_id,
                error_message,
                sent_at,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            FROM notification_deliveries
            WHERE kind = 'daily_digest'
              AND job_id IS NULL
              AND COALESCE(payload_json->>'digest_scope', '') = 'daily'
              AND COALESCE(payload_json->>'digest_date', '') = :digest_date
              AND status IN ('queued', 'sent', 'skipped')
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"digest_date": digest_date.isoformat()},
    ).mappings().first()
    if existing is not None:
        return None

    created = conn.execute(
        text(
            """
            INSERT INTO notification_deliveries (
                kind,
                status,
                recipient_email,
                subject,
                provider,
                payload_json,
                created_at
            )
            VALUES (
                'daily_digest',
                'queued',
                :recipient_email,
                :subject,
                'resend',
                CAST(:payload_json AS JSONB),
                NOW()
            )
            RETURNING
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            """
        ),
        {
            "recipient_email": recipient_email,
            "subject": subject,
            "payload_json": json.dumps(payload_json, ensure_ascii=False),
        },
    ).mappings().one()
    return dict(created)


def _get_existing_video_digest(conn: Any, *, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                provider_message_id,
                error_message,
                sent_at,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            FROM notification_deliveries
            WHERE kind = 'video_digest'
              AND job_id = CAST(:job_id AS UUID)
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"job_id": job_id},
    ).mappings().first()
    return dict(row) if row is not None else None


def _get_existing_daily_digest(conn: Any, *, digest_date: date) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT
                id::text AS delivery_id,
                status,
                recipient_email,
                subject,
                provider_message_id,
                error_message,
                sent_at,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            FROM notification_deliveries
            WHERE kind = 'daily_digest'
              AND job_id IS NULL
              AND COALESCE(payload_json->>'digest_scope', '') = 'daily'
              AND COALESCE(payload_json->>'digest_date', '') = :digest_date
              AND status IN ('queued', 'sent', 'skipped')
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"digest_date": digest_date.isoformat()},
    ).mappings().first()
    return dict(row) if row is not None else None


def _load_due_failed_deliveries(
    conn: Any,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                id::text AS delivery_id,
                kind,
                status,
                recipient_email,
                subject,
                payload_json,
                job_id::text AS job_id,
                attempt_count,
                last_attempt_at,
                next_retry_at,
                last_error_kind
            FROM notification_deliveries
            WHERE status = 'failed'
              AND next_retry_at IS NOT NULL
              AND next_retry_at <= NOW()
            ORDER BY next_retry_at ASC, created_at ASC
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
            """
        ),
        {"limit": limit},
    ).mappings().all()
    return [dict(item) for item in rows]


def _extract_daily_digest_date(payload_json: Any) -> date | None:
    if not isinstance(payload_json, dict):
        return None
    raw = payload_json.get("digest_date")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _extract_timezone_name(payload_json: Any) -> str | None:
    if not isinstance(payload_json, dict):
        return None
    raw = payload_json.get("timezone_name")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _extract_timezone_offset_minutes(payload_json: Any) -> int:
    if not isinstance(payload_json, dict):
        return 0
    return _coerce_int(payload_json.get("timezone_offset_minutes"), fallback=0)


def _load_daily_digest_jobs(
    conn: Any,
    *,
    digest_day: date,
    timezone_name: str | None,
    offset_minutes: int,
) -> list[dict[str, Any]]:
    window_start_utc, window_end_utc = _build_local_day_window_utc(
        local_day=digest_day,
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )
    rows = conn.execute(
        text(
            """
            SELECT
                j.id::text AS job_id,
                j.status,
                j.updated_at,
                j.artifact_digest_md,
                v.platform,
                v.video_uid,
                v.title,
                v.source_url
            FROM jobs j
            JOIN videos v ON v.id = j.video_id
            WHERE j.status IN ('succeeded', 'partial')
              AND j.updated_at >= :window_start_utc
              AND j.updated_at < :window_end_utc
            ORDER BY j.updated_at DESC
            """
        ),
        {
            "window_start_utc": window_start_utc,
            "window_end_utc": window_end_utc,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def _classify_http_error_kind(*, status_code: int | None, error_message: str) -> str:
    if status_code in {401, 403}:
        return "auth"
    if status_code == 429:
        return "rate_limit"
    if status_code is not None and status_code >= 500:
        return "transient"
    return _classify_delivery_error(error_message)


def _http_probe(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    timeout_seconds: int = 8,
) -> dict[str, Any]:
    sanitized_url = _sanitize_url_for_payload(url)
    request = Request(url, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(response.status)
            body_preview = _sanitize_text_preview(
                response.read(512).decode("utf-8", errors="replace")
            )
    except HTTPError as exc:
        error_body = _sanitize_text_preview(exc.read().decode("utf-8", errors="replace"))
        error_kind = _classify_http_error_kind(status_code=exc.code, error_message=error_body)
        status = "warn" if error_kind == "rate_limit" else "fail"
        return {
            "status": status,
            "error_kind": error_kind,
            "message": f"http_error:{exc.code}",
            "payload_json": {
                "url": sanitized_url,
                "status_code": exc.code,
                "body": error_body,
            },
        }
    except URLError as exc:
        reason = _sanitize_text_preview(str(exc.reason))
        return {
            "status": "fail",
            "error_kind": "transient",
            "message": f"network_error:{reason}",
            "payload_json": {"url": sanitized_url},
        }

    if 200 <= status_code < 300:
        return {
            "status": "ok",
            "error_kind": None,
            "message": "ok",
            "payload_json": {"url": sanitized_url, "status_code": status_code},
        }

    error_kind = _classify_http_error_kind(status_code=status_code, error_message=body_preview)
    return {
        "status": "warn" if error_kind == "rate_limit" else "fail",
        "error_kind": error_kind,
        "message": f"http_status:{status_code}",
        "payload_json": {
            "url": sanitized_url,
            "status_code": status_code,
            "body": body_preview,
        },
    }


def _record_provider_health_check(
    conn: Any,
    *,
    check_kind: str,
    status: str,
    error_kind: str | None,
    message: str,
    payload_json: dict[str, Any] | None,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO provider_health_checks (
                check_kind,
                status,
                error_kind,
                message,
                payload_json,
                checked_at
            )
            VALUES (
                :check_kind,
                :status,
                :error_kind,
                :message,
                CAST(:payload_json AS JSONB),
                NOW()
            )
            """
        ),
        {
            "check_kind": check_kind,
            "status": status,
            "error_kind": error_kind,
            "message": message,
            "payload_json": (
                json.dumps(payload_json, ensure_ascii=False) if payload_json is not None else None
            ),
        },
    )


def _build_retry_failure_payload(
    *,
    error_message: str,
    attempt_count: int,
) -> tuple[str, datetime | None]:
    error_kind = _classify_delivery_error(error_message)
    next_retry_at = _resolve_next_retry_at(
        attempt_count=attempt_count,
        error_kind=error_kind,
    )
    return error_kind, next_retry_at


@activity.defn(name="retry_failed_deliveries_activity")
async def retry_failed_deliveries_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    pg_store = PostgresBusinessStore(settings.database_url)
    payload = payload or {}
    limit = max(1, _coerce_int(payload.get("limit"), fallback=50))

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        due_deliveries = _load_due_failed_deliveries(conn, limit=limit)

    result = {
        "ok": True,
        "checked": len(due_deliveries),
        "retried": 0,
        "sent": 0,
        "failed": 0,
        "retry_scheduled": 0,
        "attempted_delivery_ids": [item["delivery_id"] for item in due_deliveries],
    }

    for item in due_deliveries:
        delivery_id = str(item["delivery_id"])
        kind = str(item.get("kind") or "")
        recipient_email = _normalize_email(item.get("recipient_email"))
        subject = str(item.get("subject") or "")
        payload_json = item.get("payload_json") if isinstance(item.get("payload_json"), dict) else {}
        base_attempt_count = int(item.get("attempt_count") or 0)
        next_attempt = base_attempt_count + 1
        result["retried"] += 1

        if recipient_email is None:
            error_message = "notification recipient email is not configured"
            error_kind, next_retry_at = _build_retry_failure_payload(
                error_message=error_message,
                attempt_count=next_attempt,
            )
            failed = _mark_delivery_state(
                pg_store,
                delivery_id=delivery_id,
                status="failed",
                error_message=error_message,
                sent=False,
                record_attempt=True,
                last_error_kind=error_kind,
                next_retry_at=next_retry_at,
            )
            result["failed"] += 1
            if failed.get("next_retry_at") is not None:
                result["retry_scheduled"] += 1
            continue

        try:
            if kind == "video_digest":
                job_id = str(item.get("job_id") or "").strip()
                if not job_id:
                    raise RuntimeError("missing job_id for video_digest delivery")
                with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
                    job = _fetch_job_digest_record(conn, job_id=job_id)
                digest_markdown = _safe_read_text(str(job.get("artifact_digest_md") or ""))
                body_markdown = _build_video_digest_markdown(job, digest_markdown)
            elif kind == "daily_digest":
                digest_day = _extract_daily_digest_date(payload_json)
                timezone_name = _extract_timezone_name(payload_json)
                offset_minutes = _extract_timezone_offset_minutes(payload_json)
                if digest_day is None:
                    digest_day = _resolve_local_digest_date(
                        digest_date=None,
                        timezone_name=timezone_name,
                        offset_minutes=offset_minutes,
                    )
                with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
                    jobs = _load_daily_digest_jobs(
                        conn,
                        digest_day=digest_day,
                        timezone_name=timezone_name,
                        offset_minutes=offset_minutes,
                    )
                body_markdown = _build_daily_digest_markdown(
                    digest_day=digest_day,
                    timezone_name=timezone_name,
                    offset_minutes=offset_minutes,
                    jobs=jobs,
                )
            else:
                raise RuntimeError(f"unsupported retry kind: {kind}")

            provider_message_id = _send_with_resend(
                to_email=recipient_email,
                subject=subject,
                text_body=body_markdown,
                resend_api_key=settings.resend_api_key,
                resend_from_email=settings.resend_from_email,
            )
        except Exception as exc:
            error_message = str(exc)
            error_kind, next_retry_at = _build_retry_failure_payload(
                error_message=error_message,
                attempt_count=next_attempt,
            )
            failed = _mark_delivery_state(
                pg_store,
                delivery_id=delivery_id,
                status="failed",
                error_message=error_message,
                sent=False,
                record_attempt=True,
                last_error_kind=error_kind,
                next_retry_at=next_retry_at,
            )
            result["failed"] += 1
            if failed.get("next_retry_at") is not None:
                result["retry_scheduled"] += 1
            continue

        _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="sent",
            provider_message_id=provider_message_id,
            error_message=None,
            sent=True,
            record_attempt=True,
            clear_retry_meta=True,
        )
        result["sent"] += 1

    return result


@activity.defn(name="provider_canary_activity")
async def provider_canary_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    pg_store = PostgresBusinessStore(settings.database_url)
    payload = payload or {}
    timeout_seconds = max(3, _coerce_int(payload.get("timeout_seconds"), fallback=8))

    checks: list[dict[str, Any]] = []

    rsshub_url = f"{settings.rsshub_base_url.rstrip('/')}/healthz"
    checks.append(
        {
            "check_kind": "rsshub",
            **_http_probe(url=rsshub_url, timeout_seconds=timeout_seconds),
        }
    )

    if settings.youtube_api_key:
        youtube_query = urlencode(
            {
                "part": "id",
                "id": "dQw4w9WgXcQ",
                "maxResults": 1,
                "key": settings.youtube_api_key,
            }
        )
        youtube_url = f"https://www.googleapis.com/youtube/v3/videos?{youtube_query}"
        checks.append(
            {
                "check_kind": "youtube_data_api",
                **_http_probe(url=youtube_url, timeout_seconds=timeout_seconds),
            }
        )
    else:
        checks.append(
            {
                "check_kind": "youtube_data_api",
                "status": "warn",
                "error_kind": "config_error",
                "message": "YOUTUBE_API_KEY is not configured",
                "payload_json": {},
            }
        )

    if settings.gemini_api_key:
        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models"
            f"?{urlencode({'key': settings.gemini_api_key})}"
        )
        checks.append(
            {
                "check_kind": "gemini",
                **_http_probe(url=gemini_url, timeout_seconds=timeout_seconds),
            }
        )
    else:
        checks.append(
            {
                "check_kind": "gemini",
                "status": "warn",
                "error_kind": "config_error",
                "message": "GEMINI_API_KEY is not configured",
                "payload_json": {},
            }
        )

    if settings.resend_api_key and settings.resend_from_email:
        checks.append(
            {
                "check_kind": "resend",
                **_http_probe(
                    url="https://api.resend.com/domains",
                    headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                    timeout_seconds=timeout_seconds,
                ),
            }
        )
    else:
        checks.append(
            {
                "check_kind": "resend",
                "status": "warn",
                "error_kind": "config_error",
                "message": "RESEND_API_KEY or RESEND_FROM_EMAIL is not configured",
                "payload_json": {},
            }
        )

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        for check in checks:
            kind = str(check.get("check_kind") or "")
            if kind not in HEALTH_CHECK_KINDS:
                continue
            _record_provider_health_check(
                conn,
                check_kind=kind,
                status=str(check.get("status") or "fail"),
                error_kind=(
                    str(check.get("error_kind"))
                    if isinstance(check.get("error_kind"), str)
                    else None
                ),
                message=str(check.get("message") or ""),
                payload_json=(
                    check.get("payload_json")
                    if isinstance(check.get("payload_json"), dict)
                    else {}
                ),
            )

    summary = {"ok": 0, "warn": 0, "fail": 0}
    for check in checks:
        status = str(check.get("status") or "fail")
        if status not in summary:
            status = "fail"
        summary[status] += 1

    return {
        "ok": True,
        "checks": checks,
        "summary": summary,
    }


@activity.defn(name="send_video_digest_activity")
async def send_video_digest_activity(payload: dict[str, Any]) -> dict[str, Any]:
    settings = Settings.from_env()
    pg_store = PostgresBusinessStore(settings.database_url)
    job_id = str(payload["job_id"])

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        job = _fetch_job_digest_record(conn, job_id=job_id)
        config = _get_or_init_notification_config(conn)
        recipient_email = _normalize_email(config.get("to_email"))
        skip_reason = _prepare_delivery_skip_reason(
            config=config,
            recipient_email=recipient_email,
            notification_enabled=settings.notification_enabled,
            require_daily_digest=False,
        )
        subject_title = str(job.get("title") or job.get("video_uid") or job_id)
        subject = f"[Video Digestor] Video digest {subject_title}"
        digest_markdown = _safe_read_text(str(job.get("artifact_digest_md") or ""))
        body_markdown = _build_video_digest_markdown(job, digest_markdown)
        insert_payload = {
            "digest_scope": "video",
            "job_id": job_id,
            "job_status": str(job.get("status") or ""),
            "pipeline_final_status": str(job.get("pipeline_final_status") or ""),
        }
        created = _insert_video_digest_delivery(
            conn,
            job=job,
            recipient_email=recipient_email or "unknown@example.invalid",
            subject=subject,
            payload_json=insert_payload,
        )
        if created is None:
            existing = _get_existing_video_digest(conn, job_id=job_id) or {}
            return {
                "ok": True,
                "job_id": job_id,
                "skipped": True,
                "reason": "duplicate_delivery",
                "delivery_id": existing.get("delivery_id"),
                "status": existing.get("status"),
            }
        delivery = created

    delivery_id = str(delivery["delivery_id"])
    if skip_reason is not None:
        skipped = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="skipped",
            error_message=skip_reason,
            sent=False,
            clear_retry_meta=True,
        )
        return {
            "ok": True,
            "job_id": job_id,
            "delivery_id": delivery_id,
            "status": skipped["status"],
            "skipped": True,
            "reason": skip_reason,
        }

    if recipient_email is None:
        error_message = "notification recipient email is not configured"
        error_kind = _classify_delivery_error(error_message)
        next_attempt = int(delivery.get("attempt_count") or 0) + 1
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=error_message,
            sent=False,
            record_attempt=True,
            last_error_kind=error_kind,
            next_retry_at=_resolve_next_retry_at(
                attempt_count=next_attempt,
                error_kind=error_kind,
            ),
        )
        return {
            "ok": False,
            "job_id": job_id,
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "last_error_kind": failed.get("last_error_kind"),
            "attempt_count": failed.get("attempt_count"),
            "next_retry_at": (
                failed.get("next_retry_at").isoformat()
                if isinstance(failed.get("next_retry_at"), datetime)
                else None
            ),
        }

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=str(delivery["subject"]),
            text_body=body_markdown,
            resend_api_key=settings.resend_api_key,
            resend_from_email=settings.resend_from_email,
        )
    except RuntimeError as exc:
        error_message = str(exc)
        error_kind = _classify_delivery_error(error_message)
        next_attempt = int(delivery.get("attempt_count") or 0) + 1
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=error_message,
            sent=False,
            record_attempt=True,
            last_error_kind=error_kind,
            next_retry_at=_resolve_next_retry_at(
                attempt_count=next_attempt,
                error_kind=error_kind,
            ),
        )
        return {
            "ok": False,
            "job_id": job_id,
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "last_error_kind": failed.get("last_error_kind"),
            "attempt_count": failed.get("attempt_count"),
            "next_retry_at": (
                failed.get("next_retry_at").isoformat()
                if isinstance(failed.get("next_retry_at"), datetime)
                else None
            ),
        }

    sent = _mark_delivery_state(
        pg_store,
        delivery_id=delivery_id,
        status="sent",
        provider_message_id=provider_message_id,
        error_message=None,
        sent=True,
        record_attempt=True,
        clear_retry_meta=True,
    )
    return {
        "ok": True,
        "job_id": job_id,
        "delivery_id": delivery_id,
        "status": sent["status"],
        "provider_message_id": sent.get("provider_message_id"),
        "sent_at": sent.get("sent_at").isoformat() if sent.get("sent_at") else None,
        "attempt_count": sent.get("attempt_count"),
    }


@activity.defn(name="send_daily_digest_activity")
async def send_daily_digest_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    pg_store = PostgresBusinessStore(settings.database_url)
    payload = payload or {}
    timezone_name = str(payload.get("timezone_name") or "").strip() or None
    offset_minutes = _coerce_int(payload.get("timezone_offset_minutes"), fallback=0)
    digest_day = _resolve_local_digest_date(
        digest_date=str(payload.get("digest_date") or "") or None,
        timezone_name=timezone_name,
        offset_minutes=offset_minutes,
    )

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        job_rows = _load_daily_digest_jobs(
            conn,
            digest_day=digest_day,
            timezone_name=timezone_name,
            offset_minutes=offset_minutes,
        )
        digest_markdown = _build_daily_digest_markdown(
            digest_day=digest_day,
            timezone_name=timezone_name,
            offset_minutes=offset_minutes,
            jobs=job_rows,
        )

        config = _get_or_init_notification_config(conn)
        recipient_email = _normalize_email(config.get("to_email"))
        skip_reason = _prepare_delivery_skip_reason(
            config=config,
            recipient_email=recipient_email,
            notification_enabled=settings.notification_enabled,
            require_daily_digest=True,
        )
        subject = f"[Video Digestor] Daily digest {digest_day.isoformat()}"
        insert_payload = {
            "digest_scope": "daily",
            "digest_date": digest_day.isoformat(),
            "timezone_name": timezone_name,
            "timezone_offset_minutes": offset_minutes,
            "job_count": len(job_rows),
        }
        created = _insert_daily_digest_delivery(
            conn,
            digest_date=digest_day,
            recipient_email=recipient_email or "unknown@example.invalid",
            subject=subject,
            payload_json=insert_payload,
        )
        if created is None:
            existing = _get_existing_daily_digest(conn, digest_date=digest_day) or {}
            return {
                "ok": True,
                "digest_date": digest_day.isoformat(),
                "skipped": True,
                "reason": "duplicate_delivery",
                "delivery_id": existing.get("delivery_id"),
                "status": existing.get("status"),
                "jobs": len(job_rows),
            }
        delivery = created

    delivery_id = str(delivery["delivery_id"])
    if skip_reason is not None:
        skipped = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="skipped",
            error_message=skip_reason,
            sent=False,
            clear_retry_meta=True,
        )
        return {
            "ok": True,
            "digest_date": digest_day.isoformat(),
            "delivery_id": delivery_id,
            "status": skipped["status"],
            "skipped": True,
            "reason": skip_reason,
            "jobs": len(job_rows),
        }

    if recipient_email is None:
        error_message = "notification recipient email is not configured"
        error_kind = _classify_delivery_error(error_message)
        next_attempt = int(delivery.get("attempt_count") or 0) + 1
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=error_message,
            sent=False,
            record_attempt=True,
            last_error_kind=error_kind,
            next_retry_at=_resolve_next_retry_at(
                attempt_count=next_attempt,
                error_kind=error_kind,
            ),
        )
        return {
            "ok": False,
            "digest_date": digest_day.isoformat(),
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "jobs": len(job_rows),
            "last_error_kind": failed.get("last_error_kind"),
            "attempt_count": failed.get("attempt_count"),
            "next_retry_at": (
                failed.get("next_retry_at").isoformat()
                if isinstance(failed.get("next_retry_at"), datetime)
                else None
            ),
        }

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=str(delivery["subject"]),
            text_body=digest_markdown,
            resend_api_key=settings.resend_api_key,
            resend_from_email=settings.resend_from_email,
        )
    except RuntimeError as exc:
        error_message = str(exc)
        error_kind = _classify_delivery_error(error_message)
        next_attempt = int(delivery.get("attempt_count") or 0) + 1
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=error_message,
            sent=False,
            record_attempt=True,
            last_error_kind=error_kind,
            next_retry_at=_resolve_next_retry_at(
                attempt_count=next_attempt,
                error_kind=error_kind,
            ),
        )
        return {
            "ok": False,
            "digest_date": digest_day.isoformat(),
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "jobs": len(job_rows),
            "last_error_kind": failed.get("last_error_kind"),
            "attempt_count": failed.get("attempt_count"),
            "next_retry_at": (
                failed.get("next_retry_at").isoformat()
                if isinstance(failed.get("next_retry_at"), datetime)
                else None
            ),
        }

    sent = _mark_delivery_state(
        pg_store,
        delivery_id=delivery_id,
        status="sent",
        provider_message_id=provider_message_id,
        error_message=None,
        sent=True,
        record_attempt=True,
        clear_retry_meta=True,
    )
    return {
        "ok": True,
        "digest_date": digest_day.isoformat(),
        "delivery_id": delivery_id,
        "status": sent["status"],
        "provider_message_id": sent.get("provider_message_id"),
        "jobs": len(job_rows),
        "sent_at": sent.get("sent_at").isoformat() if sent.get("sent_at") else None,
        "attempt_count": sent.get("attempt_count"),
    }


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
