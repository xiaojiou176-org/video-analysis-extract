from __future__ import annotations

from os import getpid
from typing import Any

from worker.config import Settings
from worker.rss.normalizer import normalize_entry
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


def _resolve_feed_url(settings: Settings, rsshub_route: str) -> str:
    if rsshub_route.startswith("http://") or rsshub_route.startswith("https://"):
        return rsshub_route
    base = settings.rsshub_base_url.rstrip("/")
    path = rsshub_route if rsshub_route.startswith("/") else f"/{rsshub_route}"
    return f"{base}{path}"


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
