from __future__ import annotations

import logging
from os import getpid
from typing import Any

from worker.config import Settings
from worker.rss.adapters import poll_subscription_entries, resolve_feed_url
from worker.state.postgres_store import PostgresBusinessStore
from worker.state.sqlite_store import SQLiteStateStore
from worker.temporal.activities_timing import _utc_now_iso

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

logger = logging.getLogger(__name__)


async def run_poll_feeds_once(
    settings: Settings,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from worker.rss.fetcher import RSSHubFetcher

    sqlite_store = SQLiteStateStore(settings.sqlite_path)
    pg_store = PostgresBusinessStore(settings.database_url)
    lock_owner = f"pid-{getpid()}"
    lock_key = "phase2.poll_feeds"
    lock_backend: str | None = None
    pg_lock_lease = None

    advisory_supported, pg_lock_lease, advisory_reason = pg_store.try_acquire_advisory_lock(
        lock_key=lock_key
    )
    if advisory_supported:
        if pg_lock_lease is None:
            return {"ok": True, "skipped": True, "reason": "lock_not_acquired"}
        lock_backend = "postgres_advisory"
    else:
        logger.warning(
            "poll_advisory_lock_unavailable",
            extra={
                "trace_id": "missing_trace",
                "user": "poll_feeds_activity",
                "lock_key": lock_key,
                "reason": advisory_reason,
                "error": "advisory_lock_unavailable",
            },
        )
        if not sqlite_store.acquire_lock(lock_key, lock_owner, settings.lock_ttl_seconds):
            return {"ok": True, "skipped": True, "reason": "lock_not_acquired"}
        lock_backend = "sqlite_local"

    filters = filters or {}
    try:
        subscriptions = pg_store.list_subscriptions(
            subscription_id=filters.get("subscription_id"),
            platform=filters.get("platform"),
        )

        feed_to_subscription: dict[str, dict[str, Any]] = {}
        for item in subscriptions:
            try:
                feed_url = resolve_feed_url(settings, item)
            except ValueError:
                continue
            feed_to_subscription[feed_url] = item

        feed_urls = list(feed_to_subscription.keys())
        fetcher = RSSHubFetcher(
            timeout_seconds=settings.request_timeout_seconds,
            retry_attempts=settings.request_retry_attempts,
            retry_backoff_seconds=settings.request_retry_backoff_seconds,
            public_fallback_base_url=settings.rsshub_public_fallback_base_url,
            public_fallback_base_urls=settings.rsshub_fallback_base_urls,
        )
        created_job_ids: list[str] = []
        candidates: list[dict[str, Any]] = []
        max_new = int(filters.get("max_new_videos") or 50)

        entries_fetched = 0
        entries_normalized = 0
        ingest_events_created = 0
        ingest_event_duplicates = 0
        job_duplicates = 0

        for feed_url in feed_urls:
            subscription = feed_to_subscription.get(feed_url)
            if not subscription:
                continue
            try:
                _, normalized_entries = await poll_subscription_entries(
                    settings=settings,
                    fetcher=fetcher,
                    subscription=subscription,
                )
            except ValueError:
                normalized_entries = []

            entries_fetched += len(normalized_entries)
            for normalized in normalized_entries:
                entries_normalized += 1

                platform = _resolve_platform(normalized=normalized, subscription=subscription)
                video_uid = _resolve_video_uid(normalized=normalized)

                video = pg_store.upsert_video(
                    platform=platform,
                    video_uid=video_uid,
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

                adapter_type = str(subscription.get("adapter_type") or "rsshub_route")
                pipeline_mode: str | None = "text_only" if adapter_type == "rss_generic" else None

                job, created = pg_store.create_queued_job(
                    video_id=video["id"],
                    idempotency_key=normalized["idempotency_key"],
                    mode=pipeline_mode,
                )
                if not created:
                    job_duplicates += 1
                    continue

                created_job_ids.append(job["id"])
                if len(candidates) < max_new:
                    rss_transcript = _build_rss_transcript(normalized)
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
                            "pipeline_mode": pipeline_mode,
                            "rss_transcript": rss_transcript,
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
        if lock_backend == "postgres_advisory" and pg_lock_lease is not None:
            pg_store.release_advisory_lock(pg_lock_lease)
        elif lock_backend == "sqlite_local":
            sqlite_store.release_lock(lock_key, lock_owner)


def _resolve_platform(*, normalized: dict[str, Any], subscription: dict[str, Any]) -> str:
    normalized_platform = str(normalized.get("video_platform") or "").strip().lower()
    if normalized_platform:
        return normalized_platform
    fallback_platform = str(subscription.get("platform") or "").strip().lower()
    return fallback_platform or "generic"


def _resolve_video_uid(*, normalized: dict[str, Any]) -> str:
    candidate = str(normalized.get("video_uid") or "").strip()
    if candidate:
        return candidate
    entry_hash = str(normalized.get("entry_hash") or "").strip()
    if entry_hash:
        return entry_hash
    return "unknown"


def _build_rss_transcript(normalized: dict[str, Any]) -> str | None:
    """Assemble a plain-text transcript from RSS entry fields for text-only pipeline."""
    parts: list[str] = []
    title = str(normalized.get("title") or "").strip()
    if title:
        parts.append(f"# {title}\n")
    content = str(normalized.get("content") or normalized.get("summary") or "").strip()
    if content:
        parts.append(content)
    link = str(normalized.get("link") or "").strip()
    if link:
        parts.append(f"\nSource: {link}")
    published = str(normalized.get("published_at") or "").strip()
    if published:
        parts.append(f"Published: {published}")
    return "\n".join(parts) if parts else None


@activity.defn(name="poll_feeds_activity")
async def poll_feeds_activity(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = Settings.from_env()
    return await run_poll_feeds_once(settings, filters=filters)
