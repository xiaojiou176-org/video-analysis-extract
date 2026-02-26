from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .source_names import resolve_source_name


class FeedService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_digest_feed(
        self,
        *,
        source: str | None = None,
        category: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(limit, 100))
        cursor_ts, cursor_job_id = self._parse_cursor(cursor)
        params: dict[str, Any] = {
            "limit": safe_limit + 1,
            "source": source,
            "category": category.strip().lower()
            if isinstance(category, str) and category.strip()
            else None,
            "since": since,
            "cursor_ts": cursor_ts,
            "cursor_job_id": cursor_job_id,
        }

        rows = self.db.execute(
            text(
                """
                WITH base AS (
                    SELECT
                        CAST(j.id AS TEXT) AS job_id,
                        v.source_url,
                        v.platform AS source,
                        v.title,
                        v.video_uid,
                        v.published_at,
                        j.created_at,
                        COALESCE(v.published_at, j.created_at) AS sort_ts,
                        COALESCE(
                            (
                                SELECT s.category
                                FROM ingest_events ie
                                JOIN subscriptions s ON s.id = ie.subscription_id
                                WHERE ie.video_id = v.id
                                ORDER BY ie.created_at DESC
                                LIMIT 1
                            ),
                            'misc'
                        ) AS category,
                        COALESCE(
                            (
                                SELECT s.source_type
                                FROM ingest_events ie
                                JOIN subscriptions s ON s.id = ie.subscription_id
                                WHERE ie.video_id = v.id
                                ORDER BY ie.created_at DESC
                                LIMIT 1
                            ),
                            ''
                        ) AS subscription_source_type,
                        COALESCE(
                            (
                                SELECT s.source_value
                                FROM ingest_events ie
                                JOIN subscriptions s ON s.id = ie.subscription_id
                                WHERE ie.video_id = v.id
                                ORDER BY ie.created_at DESC
                                LIMIT 1
                            ),
                            ''
                        ) AS subscription_source_value,
                        j.artifact_digest_md,
                        j.artifact_root
                    FROM jobs j
                    JOIN videos v ON v.id = j.video_id
                    WHERE j.kind = 'video_digest_v1'
                      AND j.status = 'succeeded'
                      AND (CAST(:source AS TEXT) IS NULL OR v.platform = CAST(:source AS TEXT))
                      AND (CAST(:since AS TIMESTAMPTZ) IS NULL OR j.created_at >= CAST(:since AS TIMESTAMPTZ))
                )
                SELECT *
                FROM base
                WHERE (CAST(:category AS TEXT) IS NULL OR base.category = CAST(:category AS TEXT))
                  AND (
                    CAST(:cursor_ts AS TIMESTAMPTZ) IS NULL
                    OR base.sort_ts < CAST(:cursor_ts AS TIMESTAMPTZ)
                    OR (
                      base.sort_ts = CAST(:cursor_ts AS TIMESTAMPTZ)
                      AND base.job_id < CAST(:cursor_job_id AS TEXT)
                    )
                  )
                ORDER BY base.sort_ts DESC, base.job_id DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings()

        items: list[dict[str, Any]] = []
        for row in rows:
            summary_md, artifact_type = self._resolve_summary(
                digest_path=row.get("artifact_digest_md"),
                artifact_root=row.get("artifact_root"),
            )
            if not summary_md:
                continue

            job_id = str(row.get("job_id") or "").strip()
            if not job_id:
                continue

            source_url = str(row.get("source_url") or "").strip()
            published_at = row.get("published_at") or row.get("sort_ts") or row.get("created_at")
            sort_ts = row.get("sort_ts") or row.get("created_at")
            source_platform = str(row.get("source") or "")
            source_type = str(row.get("subscription_source_type") or "")
            source_value = str(row.get("subscription_source_value") or "")
            items.append(
                {
                    "feed_id": f"{self._iso(sort_ts)}__{job_id}",
                    "job_id": job_id,
                    "video_url": source_url,
                    "title": self._resolve_title(row),
                    "source": source_platform,
                    "source_name": resolve_source_name(
                        source_type=source_type,
                        source_value=source_value,
                        fallback=source_platform,
                    ),
                    "category": str(row.get("category") or "misc"),
                    "published_at": self._iso(published_at),
                    "summary_md": summary_md,
                    "artifact_type": artifact_type,
                    "_cursor_sort_ts": self._iso(sort_ts),
                }
            )

        has_more = len(items) > safe_limit
        if has_more:
            items = items[:safe_limit]

        next_cursor: str | None = None
        if has_more and items:
            last = items[-1]
            next_cursor = f"{last['_cursor_sort_ts']}__{last['job_id']}"
        for item in items:
            item.pop("_cursor_sort_ts", None)

        return {
            "items": items,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    def _resolve_summary(self, *, digest_path: Any, artifact_root: Any) -> tuple[str | None, str]:
        digest = self._read_digest_file(digest_path)
        if digest:
            return digest, "digest"

        outline = self._read_outline_fallback(artifact_root)
        if outline:
            return outline, "outline"
        return None, "outline"

    def _read_digest_file(self, digest_path: Any) -> str | None:
        if not isinstance(digest_path, str) or not digest_path.strip():
            return None
        path = Path(digest_path).expanduser()
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            return None
        if not resolved.is_file():
            return None
        try:
            text_payload = resolved.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return text_payload or None

    def _read_outline_fallback(self, artifact_root: Any) -> str | None:
        if not isinstance(artifact_root, str) or not artifact_root.strip():
            return None
        outline_path = Path(artifact_root).expanduser() / "outline.json"
        try:
            resolved = outline_path.resolve(strict=True)
        except FileNotFoundError:
            return None
        if not resolved.is_file():
            return None
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        title = str(payload.get("title") or "").strip() or "Outline"
        summary = str(payload.get("summary") or "").strip()
        if summary:
            return f"# {title}\n\n{summary}"
        return f"# {title}\n\nOutline generated successfully."

    def _resolve_title(self, row: dict[str, Any]) -> str:
        title = str(row.get("title") or "").strip()
        if title:
            return title
        uid = str(row.get("video_uid") or "").strip()
        if uid:
            return uid
        source_url = str(row.get("source_url") or "").strip()
        if source_url:
            return source_url
        return "Untitled"

    def _iso(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str) and value.strip():
            return value
        return datetime.utcnow().isoformat()

    def _parse_cursor(self, cursor: str | None) -> tuple[str | None, str | None]:
        if not cursor or "__" not in cursor:
            return None, None
        raw_ts, raw_job_id = cursor.split("__", 1)
        ts = raw_ts.strip()
        job_id = raw_job_id.strip()
        if not ts or not job_id:
            return None, None
        return ts, job_id
