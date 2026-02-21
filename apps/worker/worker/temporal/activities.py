from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from html import escape
from os import getpid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
from sqlalchemy import text

PIPELINE_FINAL_STATUSES = {"succeeded", "partial", "failed"}
RESEND_API_URL = "https://api.resend.com/emails"
PRESERVED_ARTIFACT_FILES = {"digest.md", "meta.json", "comments.json", "outline.json"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".flv", ".avi", ".m4v", ".m4a", ".mp3"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


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


def _normalize_email(raw_email: Any) -> str | None:
    if not isinstance(raw_email, str):
        return None
    cleaned = raw_email.strip()
    return cleaned or None


def _to_html(text_value: str) -> str:
    lines = [escape(line) for line in text_value.splitlines()]
    return f"<div>{'<br/>'.join(lines)}</div>"


def _send_with_resend(*, to_email: str, subject: str, text_body: str) -> str | None:
    resend_api_key = os.getenv("RESEND_API_KEY")
    resend_from_email = os.getenv("RESEND_FROM_EMAIL")
    if not resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")
    if not resend_from_email:
        raise RuntimeError("RESEND_FROM_EMAIL is not configured")

    payload = {
        "from": resend_from_email,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": _to_html(text_body),
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        RESEND_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API returned {exc.code}: {error_body[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Resend request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        return None
    message_id = parsed.get("id")
    if isinstance(message_id, str):
        return message_id
    return None


def _local_tz_from_offset(offset_minutes: int) -> timezone:
    return timezone(timedelta(minutes=offset_minutes))


def _resolve_local_digest_date(*, digest_date: str | None, offset_minutes: int) -> date:
    if digest_date:
        return date.fromisoformat(digest_date)
    local_now = datetime.now(timezone.utc).astimezone(_local_tz_from_offset(offset_minutes))
    return local_now.date()


def _build_local_day_window_utc(*, local_day: date, offset_minutes: int) -> tuple[datetime, datetime]:
    local_tz = _local_tz_from_offset(offset_minutes)
    start_local = datetime.combine(local_day, time.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


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
    title = str(job.get("title") or "Untitled")
    source_url = str(job.get("source_url") or "").strip()
    lines = [
        f"# Video Digest: {title}",
        "",
        f"- Job ID: {job['job_id']}",
        f"- Platform: {job.get('platform') or 'unknown'}",
        f"- Video UID: {job.get('video_uid') or 'unknown'}",
        f"- Status: {job.get('status') or 'unknown'}",
    ]
    if source_url:
        lines.append(f"- Source: {source_url}")
    lines.extend(["", "---", ""])
    if digest_markdown:
        lines.append(digest_markdown)
    else:
        lines.append("_digest markdown artifact is unavailable_")
    return "\n".join(lines).strip()


def _build_daily_digest_markdown(
    *,
    digest_day: date,
    offset_minutes: int,
    jobs: list[dict[str, Any]],
) -> str:
    local_tz = _local_tz_from_offset(offset_minutes)
    generated_at = datetime.now(timezone.utc).astimezone(local_tz).replace(microsecond=0)
    succeeded_count = sum(1 for item in jobs if str(item.get("status")) == "succeeded")
    partial_count = sum(1 for item in jobs if str(item.get("status")) == "partial")

    lines = [
        f"# Daily Digest {digest_day.isoformat()}",
        "",
        f"- Generated at: {generated_at.isoformat()}",
        f"- Timezone offset minutes: {offset_minutes}",
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


def _is_cleanup_candidate(path: Path) -> bool:
    name = path.name.lower()
    if name in PRESERVED_ARTIFACT_FILES:
        return False
    suffix = path.suffix.lower()
    if "frames" in path.parts and suffix in IMAGE_EXTENSIONS:
        return True
    if "downloads" in path.parts and suffix in VIDEO_EXTENSIONS.union(IMAGE_EXTENSIONS):
        return True
    if name.startswith("frame_") and suffix in IMAGE_EXTENSIONS:
        return True
    if name.startswith("media.") and suffix in VIDEO_EXTENSIONS:
        return True
    return False


def cleanup_workspace_media_files(
    *,
    workspace_dir: str,
    older_than_hours: int = 24,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_dir).expanduser()
    if not workspace.exists():
        return {
            "ok": True,
            "workspace_dir": str(workspace),
            "deleted_files": 0,
            "deleted_dirs": 0,
            "deleted_paths_sample": [],
            "skipped": True,
            "reason": "workspace_not_found",
        }

    reference = now_utc or datetime.now(timezone.utc)
    cutoff = reference - timedelta(hours=max(1, older_than_hours))
    deleted_files = 0
    deleted_dirs = 0
    deleted_paths_sample: list[str] = []

    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if not _is_cleanup_candidate(path):
            continue
        try:
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if modified_at >= cutoff:
            continue
        try:
            path.unlink()
        except OSError:
            continue
        deleted_files += 1
        if len(deleted_paths_sample) < 20:
            deleted_paths_sample.append(str(path))

    for path in sorted(workspace.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not path.is_dir():
            continue
        try:
            next(path.iterdir())
            continue
        except StopIteration:
            pass
        except OSError:
            continue
        try:
            path.rmdir()
        except OSError:
            continue
        deleted_dirs += 1

    return {
        "ok": True,
        "workspace_dir": str(workspace),
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
        "deleted_paths_sample": deleted_paths_sample,
        "older_than_hours": max(1, older_than_hours),
        "cutoff_utc": cutoff.replace(microsecond=0).isoformat(),
    }


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
    if mode is None:
        job_record = pg_store.get_job_with_video(job_id=job_id)
        mode = str(job_record.get("mode") or "").strip() or "full"

    return await run_pipeline(
        settings,
        sqlite_store,
        pg_store,
        job_id=job_id,
        attempt=attempt,
        mode=mode,
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
) -> str | None:
    if recipient_email is None:
        return "notification recipient email is not configured"
    if not bool(config.get("enabled")):
        return "notification config is disabled"
    if not bool(config.get("daily_digest_enabled")):
        return "daily digest is disabled"
    return None


def _mark_delivery_state(
    pg_store: PostgresBusinessStore,
    *,
    delivery_id: str,
    status: str,
    error_message: str | None = None,
    provider_message_id: str | None = None,
    sent: bool = False,
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
                    sent_at = CASE WHEN :sent THEN NOW() ELSE sent_at END
                WHERE id = CAST(:delivery_id AS UUID)
                RETURNING
                    id::text AS delivery_id,
                    status,
                    provider_message_id,
                    error_message,
                    sent_at
                """
            ),
            {
                "delivery_id": delivery_id,
                "status": status,
                "error_message": error_message,
                "provider_message_id": provider_message_id,
                "sent": sent,
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
                sent_at
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
                subject
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
                sent_at
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
                subject
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
                sent_at
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
                sent_at
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
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message="notification recipient email is not configured",
            sent=False,
        )
        return {
            "ok": False,
            "job_id": job_id,
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
        }

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=str(delivery["subject"]),
            text_body=body_markdown,
        )
    except RuntimeError as exc:
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=str(exc),
            sent=False,
        )
        return {
            "ok": False,
            "job_id": job_id,
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
        }

    sent = _mark_delivery_state(
        pg_store,
        delivery_id=delivery_id,
        status="sent",
        provider_message_id=provider_message_id,
        error_message=None,
        sent=True,
    )
    return {
        "ok": True,
        "job_id": job_id,
        "delivery_id": delivery_id,
        "status": sent["status"],
        "provider_message_id": sent.get("provider_message_id"),
        "sent_at": sent.get("sent_at").isoformat() if sent.get("sent_at") else None,
    }


@activity.defn(name="send_daily_digest_activity")
async def send_daily_digest_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    pg_store = PostgresBusinessStore(settings.database_url)
    payload = payload or {}
    offset_minutes = _coerce_int(payload.get("timezone_offset_minutes"), fallback=0)
    digest_day = _resolve_local_digest_date(
        digest_date=str(payload.get("digest_date") or "") or None,
        offset_minutes=offset_minutes,
    )
    window_start_utc, window_end_utc = _build_local_day_window_utc(
        local_day=digest_day,
        offset_minutes=offset_minutes,
    )

    with pg_store._engine.begin() as conn:  # type: ignore[attr-defined]
        jobs = conn.execute(
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
        job_rows = [dict(row) for row in jobs]
        digest_markdown = _build_daily_digest_markdown(
            digest_day=digest_day,
            offset_minutes=offset_minutes,
            jobs=job_rows,
        )

        config = _get_or_init_notification_config(conn)
        recipient_email = _normalize_email(config.get("to_email"))
        skip_reason = _prepare_delivery_skip_reason(
            config=config,
            recipient_email=recipient_email,
        )
        subject = f"[Video Digestor] Daily digest {digest_day.isoformat()}"
        insert_payload = {
            "digest_scope": "daily",
            "digest_date": digest_day.isoformat(),
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
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message="notification recipient email is not configured",
            sent=False,
        )
        return {
            "ok": False,
            "digest_date": digest_day.isoformat(),
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "jobs": len(job_rows),
        }

    try:
        provider_message_id = _send_with_resend(
            to_email=recipient_email,
            subject=str(delivery["subject"]),
            text_body=digest_markdown,
        )
    except RuntimeError as exc:
        failed = _mark_delivery_state(
            pg_store,
            delivery_id=delivery_id,
            status="failed",
            error_message=str(exc),
            sent=False,
        )
        return {
            "ok": False,
            "digest_date": digest_day.isoformat(),
            "delivery_id": delivery_id,
            "status": failed["status"],
            "error": failed["error_message"],
            "jobs": len(job_rows),
        }

    sent = _mark_delivery_state(
        pg_store,
        delivery_id=delivery_id,
        status="sent",
        provider_message_id=provider_message_id,
        error_message=None,
        sent=True,
    )
    return {
        "ok": True,
        "digest_date": digest_day.isoformat(),
        "delivery_id": delivery_id,
        "status": sent["status"],
        "provider_message_id": sent.get("provider_message_id"),
        "jobs": len(job_rows),
        "sent_at": sent.get("sent_at").isoformat() if sent.get("sent_at") else None,
    }


@activity.defn(name="cleanup_workspace_activity")
async def cleanup_workspace_activity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    payload = payload or {}
    older_than_hours = max(1, _coerce_int(payload.get("older_than_hours"), fallback=24))
    return cleanup_workspace_media_files(
        workspace_dir=str(payload.get("workspace_dir") or settings.pipeline_workspace_dir),
        older_than_hours=older_than_hours,
    )
