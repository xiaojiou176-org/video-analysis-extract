from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

_ALLOWED_FILTERS = {
    "platform",
    "job_id",
    "video_id",
    "video_uid",
    "kind",
    "mode",
}

_SEARCH_FILES = (
    ("digest", "digest.md"),
    ("transcript", "transcript.txt"),
    ("outline", "outline.json"),
    ("comments", "comments.json"),
    ("meta", "meta.json"),
)


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        normalized_filters = self._normalize_filters(filters)
        rows = self._list_candidate_jobs(
            top_k=top_k,
            filters=normalized_filters,
        )

        hits: list[dict[str, Any]] = []
        for row in rows:
            artifact_root = row.get("artifact_root")
            if not isinstance(artifact_root, str) or not artifact_root.strip():
                continue

            for source, content in self._iter_artifact_texts(artifact_root):
                match = self._match_content(content=content, query=normalized_query)
                if match is None:
                    continue
                score, snippet = match
                hits.append(
                    {
                        "job_id": str(row.get("job_id")),
                        "video_id": str(row.get("video_id")),
                        "platform": str(row.get("platform") or ""),
                        "video_uid": str(row.get("video_uid") or ""),
                        "source_url": str(row.get("source_url") or ""),
                        "title": row.get("title"),
                        "kind": str(row.get("kind") or ""),
                        "mode": row.get("mode"),
                        "source": source,
                        "snippet": snippet,
                        "score": score,
                    }
                )

        hits.sort(key=lambda item: item["score"], reverse=True)
        return {
            "query": normalized_query,
            "top_k": top_k,
            "filters": normalized_filters,
            "items": hits[:top_k],
        }

    def _normalize_filters(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(filters, dict):
            return {}
        normalized: dict[str, Any] = {}
        for key, value in filters.items():
            if key not in _ALLOWED_FILTERS:
                continue
            if value is None:
                continue
            value_str = str(value).strip()
            if value_str:
                normalized[key] = value_str
        return normalized

    def _list_candidate_jobs(self, *, top_k: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        limit = min(max(top_k * 8, 50), 200)
        params: dict[str, Any] = {
            "platform": filters.get("platform"),
            "job_id": filters.get("job_id"),
            "video_id": filters.get("video_id"),
            "video_uid": filters.get("video_uid"),
            "kind": filters.get("kind"),
            "mode": filters.get("mode"),
            "limit": limit,
        }
        statement = text(
            """
            SELECT
                j.id AS job_id,
                j.video_id AS video_id,
                j.kind AS kind,
                j.mode AS mode,
                j.artifact_root AS artifact_root,
                v.platform AS platform,
                v.video_uid AS video_uid,
                v.source_url AS source_url,
                v.title AS title
            FROM jobs j
            JOIN videos v ON v.id = j.video_id
            WHERE j.status = 'succeeded'
              AND j.artifact_root IS NOT NULL
              AND (:platform IS NULL OR v.platform = :platform)
              AND (:job_id IS NULL OR CAST(j.id AS TEXT) = :job_id)
              AND (:video_id IS NULL OR CAST(v.id AS TEXT) = :video_id)
              AND (:video_uid IS NULL OR v.video_uid = :video_uid)
              AND (:kind IS NULL OR j.kind = :kind)
              AND (:mode IS NULL OR j.mode = :mode)
            ORDER BY j.updated_at DESC
            LIMIT :limit
            """
        )
        try:
            rows = self.db.execute(statement, params).mappings().all()
        except DBAPIError:
            self.db.rollback()
            return []
        return [dict(row) for row in rows]

    def _iter_artifact_texts(self, artifact_root: str) -> list[tuple[str, str]]:
        root = Path(artifact_root).expanduser()
        if not root.exists() or not root.is_dir():
            return []

        payload: list[tuple[str, str]] = []
        for source, filename in _SEARCH_FILES:
            path = root / filename
            if not path.exists() or not path.is_file():
                continue
            text_value = self._read_text(path)
            if text_value:
                payload.append((source, text_value))
        return payload

    def _read_text(self, path: Path) -> str:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return ""

        if path.suffix == ".json":
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                return raw
        return raw

    def _match_content(self, *, content: str, query: str) -> tuple[float, str] | None:
        content_norm = content.strip()
        if not content_norm:
            return None

        query_norm = query.lower()
        haystack = content_norm.lower()
        first_index = haystack.find(query_norm)
        if first_index < 0:
            return None

        occurrences = haystack.count(query_norm)
        score = float(occurrences) + max(0.0, (2000.0 - min(2000, first_index)) / 2000.0)

        start = max(0, first_index - 80)
        end = min(len(content_norm), first_index + len(query) + 160)
        snippet = re.sub(r"\s+", " ", content_norm[start:end]).strip()
        return score, snippet
