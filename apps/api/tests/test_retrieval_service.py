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

    payload = service.search(query="timeout", top_k=1, filters={"platform": "youtube"})

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

    payload = service.search(query="quick", top_k=5, filters={"unknown": "x", "platform": "youtube"})

    assert payload["filters"] == {"platform": "youtube"}
