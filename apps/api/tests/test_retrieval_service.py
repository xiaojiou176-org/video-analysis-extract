from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from apps.api.app.services.retrieval import RetrievalService


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_RowsResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls = 0

    def execute(self, _statement: Any, _params: dict[str, Any] | None = None) -> _RowsResult:
        self.calls += 1
        return _RowsResult(self.rows)

    def rollback(self) -> None:
        return None


def test_retrieval_service_search_matches_digest_and_applies_top_k(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "digest.md").write_text("Provider timeout detected and retried.", encoding="utf-8")
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

    payload = service.search(query="timeout", top_k=1, mode="keyword", filters={"platform": "youtube"})

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

    payload = service.search(query="quick", top_k=5, mode="keyword", filters={"unknown": "x", "platform": "youtube"})

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

    payload = service.search(query="timeout issue", top_k=3, mode="semantic", filters={"platform": "youtube"})

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

    payload = service.search(query="timeout", top_k=5, mode="hybrid", filters={"platform": "youtube"})

    assert len(payload["items"]) == 2
    assert payload["items"][0]["job_id"] == "job-1"
    assert payload["items"][0]["score"] == 1.2
    assert payload["items"][1]["job_id"] == "job-2"


def test_retrieval_service_search_hits_three_sources(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "digest.md").write_text("alpha found in digest", encoding="utf-8")
    (artifact_root / "transcript.txt").write_text("alpha found in transcript", encoding="utf-8")
    (artifact_root / "outline.json").write_text('{"summary":"alpha found in outline"}', encoding="utf-8")

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
