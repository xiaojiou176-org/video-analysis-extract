from __future__ import annotations

import concurrent.futures
import importlib
import json
import re
from pathlib import Path
from typing import Any, Literal, cast

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from ..config import Settings
from ..errors import ApiTimeoutError

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

_RETRIEVAL_MODES = {"keyword", "semantic", "hybrid"}
_EMBEDDING_DIMENSION = 768

RetrievalMode = Literal["keyword", "semantic", "hybrid"]


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
        mode: RetrievalMode = "keyword",
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        normalized_filters = self._normalize_filters(filters)
        normalized_mode = self._normalize_mode(mode)
        keyword_hits = self._search_keyword(
            query=normalized_query,
            top_k=top_k,
            filters=normalized_filters,
        )
        if normalized_mode == "keyword":
            hits = keyword_hits
        else:
            semantic_hits = self._search_semantic(
                query=normalized_query,
                top_k=top_k,
                filters=normalized_filters,
            )
            if normalized_mode == "semantic":
                hits = semantic_hits
            else:
                hits = self._merge_hybrid_hits(keyword_hits=keyword_hits, semantic_hits=semantic_hits, top_k=top_k)

        return {
            "query": normalized_query,
            "top_k": top_k,
            "filters": normalized_filters,
            "items": hits[:top_k],
        }

    def _normalize_mode(self, mode: str) -> RetrievalMode:
        normalized = str(mode).strip().lower()
        if normalized not in _RETRIEVAL_MODES:
            return "keyword"
        return cast(RetrievalMode, normalized)

    def _search_keyword(self, *, query: str, top_k: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._list_candidate_jobs(top_k=top_k, filters=filters)
        hits: list[dict[str, Any]] = []
        for row in rows:
            artifact_root = row.get("artifact_root")
            if not isinstance(artifact_root, str) or not artifact_root.strip():
                continue
            for source, content in self._iter_artifact_texts(artifact_root):
                match = self._match_content(content=content, query=query)
                if match is None:
                    continue
                score, snippet = match
                hits.append(
                    self._build_hit(
                        row=row,
                        source=source,
                        snippet=snippet,
                        score=score,
                    )
                )
        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:top_k]

    def _search_semantic(self, *, query: str, top_k: int, filters: dict[str, Any]) -> list[dict[str, Any]]:
        query_embedding = self._build_query_embedding(query)
        if not query_embedding:
            return []
        params: dict[str, Any] = {
            "query_embedding": self._to_vector_literal(query_embedding),
            "platform": filters.get("platform"),
            "job_id": filters.get("job_id"),
            "video_id": filters.get("video_id"),
            "video_uid": filters.get("video_uid"),
            "kind": filters.get("kind"),
            "mode": filters.get("mode"),
            "limit": min(max(top_k * 4, 20), 120),
        }
        statement = text(
            """
            SELECT
                j.id AS job_id,
                j.video_id AS video_id,
                j.kind AS kind,
                j.mode AS mode,
                v.platform AS platform,
                v.video_uid AS video_uid,
                v.source_url AS source_url,
                v.title AS title,
                ve.content_type AS source,
                ve.chunk_text AS snippet,
                1 - (ve.embedding <=> CAST(:query_embedding AS vector(768))) AS score
            FROM video_embeddings ve
            JOIN jobs j ON j.id = ve.job_id
            JOIN videos v ON v.id = ve.video_id
            WHERE j.status = 'succeeded'
              AND (:platform IS NULL OR v.platform = :platform)
              AND (:job_id IS NULL OR CAST(j.id AS TEXT) = :job_id)
              AND (:video_id IS NULL OR CAST(v.id AS TEXT) = :video_id)
              AND (:video_uid IS NULL OR v.video_uid = :video_uid)
              AND (:kind IS NULL OR j.kind = :kind)
              AND (:mode IS NULL OR j.mode = :mode)
            ORDER BY ve.embedding <=> CAST(:query_embedding AS vector(768)) ASC
            LIMIT :limit
            """
        )
        try:
            rows = self.db.execute(statement, params).mappings().all()
        except DBAPIError:
            self.db.rollback()
            return []

        hits: list[dict[str, Any]] = []
        for row in rows:
            source = str(row.get("source") or "").strip().lower()
            if source not in {"transcript", "outline"}:
                source = "transcript"
            score_raw = row.get("score")
            if not isinstance(score_raw, (int, float)):
                continue
            snippet = re.sub(r"\s+", " ", str(row.get("snippet") or "")).strip()
            if not snippet:
                continue
            hits.append(
                self._build_hit(
                    row=row,
                    source=source,
                    snippet=snippet[:400],
                    score=float(score_raw),
                )
            )

        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:top_k]

    @staticmethod
    def _merge_hybrid_hits(
        *,
        keyword_hits: list[dict[str, Any]],
        semantic_hits: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in keyword_hits + semantic_hits:
            key = (
                str(item.get("job_id") or ""),
                str(item.get("source") or ""),
                str(item.get("snippet") or ""),
            )
            existing = merged.get(key)
            if existing is None or float(item.get("score") or 0.0) > float(existing.get("score") or 0.0):
                merged[key] = item
        ordered = sorted(merged.values(), key=lambda item: float(item.get("score") or 0.0), reverse=True)
        return ordered[:top_k]

    def _build_query_embedding(self, query: str) -> list[float] | None:
        normalized_query = query.strip()
        if not normalized_query:
            return None
        settings = Settings.from_env()
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            return None
        model = (settings.gemini_embedding_model or "gemini-embedding-001").strip() or "gemini-embedding-001"
        try:
            genai = importlib.import_module("google.genai")  # type: ignore[assignment]
            genai_types = importlib.import_module("google.genai.types")  # type: ignore[assignment]
        except Exception:
            return None

        def _embed_content() -> Any:
            client = genai.Client(api_key=api_key)
            return client.models.embed_content(
                model=model,
                contents=[normalized_query],
                config=genai_types.EmbedContentConfig(output_dimensionality=_EMBEDDING_DIMENSION),
            )

        def _raise_embedding_timeout(timeout_seconds: float, exc: Exception) -> None:
            raise ApiTimeoutError(
                detail=f"retrieval embedding timed out after {timeout_seconds:.1f}s",
                error_code="RETRIEVAL_EMBEDDING_TIMEOUT",
            ) from exc

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                response = executor.submit(_embed_content).result(
                    timeout=settings.api_retrieval_embedding_timeout_seconds
                )
        except concurrent.futures.TimeoutError as exc:
            _raise_embedding_timeout(settings.api_retrieval_embedding_timeout_seconds, exc)
        except Exception as exc:
            if isinstance(exc, TimeoutError) or exc.__class__.__name__ == "TimeoutError":
                _raise_embedding_timeout(settings.api_retrieval_embedding_timeout_seconds, exc)
            return None
        return self._extract_embedding_values(response)

    def _extract_embedding_values(self, response: Any) -> list[float] | None:
        embeddings = getattr(response, "embeddings", None)
        if isinstance(embeddings, list) and embeddings:
            candidate = embeddings[0]
            values = self._extract_values(candidate)
            if values:
                return values
        return self._extract_values(response)

    def _extract_values(self, value: Any) -> list[float] | None:
        embedding = getattr(value, "embedding", None)
        if embedding is not None:
            values = getattr(embedding, "values", None)
            if isinstance(values, list) and values:
                return [float(v) for v in values]
        values = getattr(value, "values", None)
        if isinstance(values, list) and values:
            return [float(v) for v in values]
        if isinstance(value, dict):
            candidate = value.get("values")
            if isinstance(candidate, list) and candidate:
                return [float(v) for v in candidate]
            nested = value.get("embedding")
            if isinstance(nested, dict):
                nested_values = nested.get("values")
                if isinstance(nested_values, list) and nested_values:
                    return [float(v) for v in nested_values]
        return None

    @staticmethod
    def _to_vector_literal(values: list[float]) -> str:
        if not values:
            raise ValueError("embedding vector is empty")
        return "[" + ",".join(f"{float(value):.10f}" for value in values) + "]"

    def _build_hit(
        self,
        *,
        row: dict[str, Any],
        source: str,
        snippet: str,
        score: float,
    ) -> dict[str, Any]:
        return {
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
            "score": float(score),
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
