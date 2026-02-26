from __future__ import annotations

import concurrent.futures
import json
import sys
import types
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError

from apps.api.app.services.retrieval import RetrievalService


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls = 0
        self.rollback_calls = 0

    def execute(self, _statement: Any, _params: dict[str, Any] | None = None) -> _RowsResult:
        self.calls += 1
        return _RowsResult(self.rows)

    def rollback(self) -> None:
        self.rollback_calls += 1


class _ErrorDB(_FakeDB):
    def execute(self, _statement: Any, _params: dict[str, Any] | None = None) -> _RowsResult:
        raise DBAPIError("SELECT", {}, Exception("boom"))


def test_retrieval_service_search_matches_digest_and_applies_top_k(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "digest.md").write_text(
        "Provider timeout detected and retried.", encoding="utf-8"
    )
    (artifact_root / "transcript.txt").write_text("Everything is normal here.", encoding="utf-8")

    db = _FakeDB(
        [
            {
                "job_id": uuid.uuid4(),
                "video_id": uuid.uuid4(),
                "kind": "video_digest_v1",
                "mode": "full",
                "artifact_root": str(artifact_root),
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
            }
        ]
    )
    service = RetrievalService(db)  # type: ignore[arg-type]

    payload = service.search(
        query="timeout", top_k=1, mode="keyword", filters={"platform": "youtube"}
    )

    assert payload["query"] == "timeout"
    assert payload["top_k"] == 1
    assert payload["filters"] == {"platform": "youtube"}
    assert len(payload["items"]) == 1
    assert payload["items"][0]["source"] == "digest"
    assert "timeout detected" in payload["items"][0]["snippet"].lower()


def test_retrieval_service_ignores_unsupported_filters(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "digest.md").write_text("quick summary", encoding="utf-8")

    db = _FakeDB(
        [
            {
                "job_id": uuid.uuid4(),
                "video_id": uuid.uuid4(),
                "kind": "video_digest_v1",
                "mode": "full",
                "artifact_root": str(artifact_root),
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
            }
        ]
    )
    service = RetrievalService(db)  # type: ignore[arg-type]

    payload = service.search(
        query="quick", top_k=5, mode="keyword", filters={"unknown": "x", "platform": "youtube"}
    )

    assert payload["filters"] == {"platform": "youtube"}


def test_retrieval_service_semantic_mode_uses_embedding_path(monkeypatch) -> None:
    db = _FakeDB([])
    service = RetrievalService(db)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "_search_keyword", lambda **kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(
        service,
        "_search_semantic",
        lambda **kwargs: [
            {
                "job_id": "job-1",
                "video_id": "video-1",
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
                "kind": "video_digest_v1",
                "mode": "full",
                "source": "transcript",
                "snippet": "timeout due to network jitter",
                "score": 0.91,
            }
        ],
    )

    payload = service.search(
        query="timeout issue", top_k=3, mode="semantic", filters={"platform": "youtube"}
    )

    assert payload["query"] == "timeout issue"
    assert payload["top_k"] == 3
    assert payload["items"][0]["source"] == "transcript"
    assert payload["items"][0]["score"] == 0.91


def test_retrieval_service_hybrid_mode_merges_and_deduplicates(monkeypatch) -> None:
    db = _FakeDB([])
    service = RetrievalService(db)  # type: ignore[arg-type]

    monkeypatch.setattr(
        service,
        "_search_keyword",
        lambda **kwargs: [
            {
                "job_id": "job-1",
                "video_id": "video-1",
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
                "kind": "video_digest_v1",
                "mode": "full",
                "source": "transcript",
                "snippet": "provider timeout in transcript chunk",
                "score": 1.2,
            }
        ],
    )
    monkeypatch.setattr(
        service,
        "_search_semantic",
        lambda **kwargs: [
            {
                "job_id": "job-1",
                "video_id": "video-1",
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
                "kind": "video_digest_v1",
                "mode": "full",
                "source": "transcript",
                "snippet": "provider timeout in transcript chunk",
                "score": 0.82,
            },
            {
                "job_id": "job-2",
                "video_id": "video-2",
                "platform": "youtube",
                "video_uid": "def456",
                "source_url": "https://www.youtube.com/watch?v=def456",
                "title": "Demo 2",
                "kind": "video_digest_v1",
                "mode": "full",
                "source": "outline",
                "snippet": "error budget and retry policy",
                "score": 0.79,
            },
        ],
    )

    payload = service.search(
        query="timeout", top_k=5, mode="hybrid", filters={"platform": "youtube"}
    )

    assert len(payload["items"]) == 2
    assert payload["items"][0]["job_id"] == "job-1"
    assert payload["items"][0]["score"] == 1.2
    assert payload["items"][1]["job_id"] == "job-2"


def test_retrieval_service_search_hits_three_sources(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "digest.md").write_text("alpha found in digest", encoding="utf-8")
    (artifact_root / "transcript.txt").write_text("alpha found in transcript", encoding="utf-8")
    (artifact_root / "outline.json").write_text(
        '{"summary":"alpha found in outline"}', encoding="utf-8"
    )

    db = _FakeDB(
        [
            {
                "job_id": uuid.uuid4(),
                "video_id": uuid.uuid4(),
                "kind": "video_digest_v1",
                "mode": "full",
                "artifact_root": str(artifact_root),
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://www.youtube.com/watch?v=abc123",
                "title": "Demo",
            }
        ]
    )
    service = RetrievalService(db)  # type: ignore[arg-type]

    payload = service.search(query="alpha", top_k=3, filters={"platform": "youtube"})
    sources = {item["source"] for item in payload["items"]}

    assert len(payload["items"]) == 3
    assert sources == {"digest", "transcript", "outline"}


def test_normalize_mode_invalid_defaults_to_keyword() -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    assert service._normalize_mode("invalid") == "keyword"
    assert service._normalize_mode(" HYBRID ") == "hybrid"


def test_search_keyword_skips_invalid_artifact_roots() -> None:
    db = _FakeDB(
        [
            {"artifact_root": None},
            {"artifact_root": "   "},
        ]
    )
    service = RetrievalService(db)  # type: ignore[arg-type]
    assert service._search_keyword(query="x", top_k=5, filters={}) == []


def test_search_semantic_rolls_back_on_db_error() -> None:
    db = _ErrorDB([])
    service = RetrievalService(db)  # type: ignore[arg-type]
    service._build_query_embedding = lambda query: [0.1, 0.2]  # type: ignore[method-assign]

    assert service._search_semantic(query="x", top_k=3, filters={}) == []
    assert db.rollback_calls == 1


def test_search_semantic_filters_invalid_rows(monkeypatch) -> None:
    db = _FakeDB(
        [
            {
                "job_id": "job-1",
                "video_id": "video-1",
                "kind": "video_digest_v1",
                "mode": "full",
                "platform": "youtube",
                "video_uid": "abc123",
                "source_url": "https://x",
                "title": "Demo",
                "source": "unknown",
                "snippet": "  alpha\n beta  ",
                "score": 0.7,
            },
            {
                "job_id": "job-2",
                "video_id": "video-2",
                "kind": "video_digest_v1",
                "mode": "full",
                "platform": "youtube",
                "video_uid": "def456",
                "source_url": "https://y",
                "title": "Demo2",
                "source": "outline",
                "snippet": "",
                "score": 0.8,
            },
            {
                "job_id": "job-3",
                "video_id": "video-3",
                "kind": "video_digest_v1",
                "mode": "full",
                "platform": "youtube",
                "video_uid": "ghi789",
                "source_url": "https://z",
                "title": "Demo3",
                "source": "transcript",
                "snippet": "ok",
                "score": "bad",
            },
        ]
    )
    service = RetrievalService(db)  # type: ignore[arg-type]
    monkeypatch.setattr(service, "_build_query_embedding", lambda query: [0.1, 0.2])

    hits = service._search_semantic(query="x", top_k=5, filters={})

    assert len(hits) == 1
    assert hits[0]["source"] == "transcript"
    assert hits[0]["snippet"] == "alpha beta"


def test_build_query_embedding_returns_none_for_blank_query_or_no_key(monkeypatch) -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    assert service._build_query_embedding("   ") is None

    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert service._build_query_embedding("hello") is None


def test_build_query_embedding_handles_import_error(monkeypatch) -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    monkeypatch.setattr(
        "apps.api.app.services.retrieval.Settings.from_env",
        lambda: SimpleNamespace(
            gemini_api_key="key",
            gemini_embedding_model="x",
            api_retrieval_embedding_timeout_seconds=1.0,
        ),
    )

    monkeypatch.setitem(sys.modules, "google", None)
    monkeypatch.setitem(sys.modules, "google.genai", None)

    assert service._build_query_embedding("hello") is None


def test_build_query_embedding_timeout_raises_api_timeout(monkeypatch) -> None:
    retrieval_module = __import__(
        "apps.api.app.services.retrieval",
        fromlist=["RetrievalService", "Settings", "ApiTimeoutError"],
    )
    retrieval_module = __import__("importlib").reload(retrieval_module)
    service = retrieval_module.RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    monkeypatch.setattr(
        retrieval_module.Settings,
        "from_env",
        lambda: types.SimpleNamespace(
            gemini_api_key="key",
            gemini_embedding_model="gemini-embedding-001",
            api_retrieval_embedding_timeout_seconds=0.5,
        ),
    )

    class _FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = types.SimpleNamespace(
                embed_content=lambda **kwargs: {"values": [0.1, 0.2]}
            )

    fake_types_module = types.ModuleType("google.genai.types")

    class _EmbedContentConfig:
        def __init__(self, output_dimensionality: int):
            self.output_dimensionality = output_dimensionality

    fake_types_module.EmbedContentConfig = _EmbedContentConfig
    fake_genai_module = types.ModuleType("google.genai")
    fake_genai_module.Client = _FakeClient
    fake_genai_module.types = fake_types_module
    fake_genai_module.__path__ = []

    def _fake_import(name: str):
        if name == "google.genai":
            return fake_genai_module
        if name == "google.genai.types":
            return fake_types_module
        raise ImportError(name)

    monkeypatch.setattr(retrieval_module.importlib, "import_module", _fake_import)

    class _Future:
        def result(self, timeout: float):
            del timeout
            raise concurrent.futures.TimeoutError

    class _Executor:
        def __init__(self, max_workers: int):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn):
            del fn
            return _Future()

    monkeypatch.setattr(retrieval_module.concurrent.futures, "ThreadPoolExecutor", _Executor)

    with pytest.raises(retrieval_module.ApiTimeoutError, match="retrieval embedding timed out"):
        service._build_query_embedding("hello")


def test_build_query_embedding_returns_none_on_runtime_exception(monkeypatch) -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    monkeypatch.setattr(
        "apps.api.app.services.retrieval.Settings.from_env",
        lambda: types.SimpleNamespace(
            gemini_api_key="key",
            gemini_embedding_model="gemini-embedding-001",
            api_retrieval_embedding_timeout_seconds=0.5,
        ),
    )

    class _FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = types.SimpleNamespace(
                embed_content=lambda **kwargs: {"values": [0.1, 0.2]}
            )

    fake_types_module = types.ModuleType("google.genai.types")

    class _EmbedContentConfig:
        def __init__(self, output_dimensionality: int):
            self.output_dimensionality = output_dimensionality

    fake_types_module.EmbedContentConfig = _EmbedContentConfig
    fake_genai_module = types.ModuleType("google.genai")
    fake_genai_module.Client = _FakeClient
    fake_genai_module.types = fake_types_module
    fake_genai_module.__path__ = []

    def _fake_import(name: str):
        if name == "google.genai":
            return fake_genai_module
        if name == "google.genai.types":
            return fake_types_module
        raise ImportError(name)

    monkeypatch.setattr("apps.api.app.services.retrieval.importlib.import_module", _fake_import)

    class _Future:
        def result(self, timeout: float):
            del timeout
            raise RuntimeError("bad")

    class _Executor:
        def __init__(self, max_workers: int):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn):
            del fn
            return _Future()

    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", _Executor)
    assert service._build_query_embedding("hello") is None


def test_extract_embedding_values_and_extract_values_paths() -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]

    response = types.SimpleNamespace(
        embeddings=[types.SimpleNamespace(embedding=types.SimpleNamespace(values=[1, 2, 3]))]
    )
    assert service._extract_embedding_values(response) == [1.0, 2.0, 3.0]

    assert service._extract_values(types.SimpleNamespace(values=[4, 5])) == [4.0, 5.0]
    assert service._extract_values({"values": [6, 7]}) == [6.0, 7.0]
    assert service._extract_values({"embedding": {"values": [8, 9]}}) == [8.0, 9.0]
    assert service._extract_values({"embedding": {"values": []}}) is None


def test_to_vector_literal_and_empty_vector() -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    assert service._to_vector_literal([1, 2.5]) == "[1.0000000000,2.5000000000]"
    with pytest.raises(ValueError, match="empty"):
        service._to_vector_literal([])


def test_list_candidate_jobs_rolls_back_on_db_error() -> None:
    db = _ErrorDB([])
    service = RetrievalService(db)  # type: ignore[arg-type]
    rows = service._list_candidate_jobs(top_k=10, filters={})
    assert rows == []
    assert db.rollback_calls == 1


def test_iter_artifact_texts_and_read_text_json_paths(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    root.mkdir(parents=True, exist_ok=True)
    (root / "digest.md").write_text("digest", encoding="utf-8")
    (root / "outline.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    (root / "comments.json").write_text("{bad-json", encoding="utf-8")

    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    payload = dict(service._iter_artifact_texts(str(root)))

    assert payload["digest"] == "digest"
    assert payload["outline"] == '{"a": 1}'
    assert payload["comments"] == "{bad-json"


def test_match_content_branches() -> None:
    service = RetrievalService(_FakeDB([]))  # type: ignore[arg-type]
    assert service._match_content(content="", query="x") is None
    assert service._match_content(content="hello", query="zzz") is None

    matched = service._match_content(content="alpha beta alpha", query="alpha")
    assert matched is not None
    score, snippet = matched
    assert score > 0
    assert "alpha" in snippet
