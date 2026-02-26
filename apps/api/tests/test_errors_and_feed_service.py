from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.api.app.errors import ApiServiceError, ApiTimeoutError, build_error_payload
from apps.api.app.services.feed import FeedService


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _FakeDB:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[dict[str, Any]] = []

    def execute(self, stmt: Any, params: dict[str, Any]) -> _FakeResult:
        self.calls.append({"stmt": str(stmt), "params": dict(params)})
        return _FakeResult(self.rows)


def test_build_error_payload_and_service_error_roundtrip() -> None:
    payload = build_error_payload(detail="upstream failed", error_code="UPSTREAM_FAILED")
    assert payload == {"detail": "upstream failed", "error_code": "UPSTREAM_FAILED"}

    err = ApiServiceError(
        detail="broken", error_code="BROKEN", status_code=502, error_kind="gateway"
    )
    assert str(err) == "broken"
    assert err.to_payload() == {
        "detail": "broken",
        "error_code": "BROKEN",
        "error_kind": "gateway",
    }


def test_api_timeout_error_uses_timeout_defaults() -> None:
    err = ApiTimeoutError(detail="timed out", error_code="TIMEOUT")

    assert err.status_code == 504
    assert err.error_kind == "timeout"
    assert err.to_payload()["error_kind"] == "timeout"


def test_feed_service_reads_digest_and_outline_fallback(tmp_path: Path) -> None:
    service = FeedService(db=None)  # type: ignore[arg-type]

    digest_path = tmp_path / "digest.md"
    digest_path.write_text("# digest", encoding="utf-8")
    assert service._read_digest_file(str(digest_path)) == "# digest"

    broken_outline_root = tmp_path / "broken"
    broken_outline_root.mkdir(parents=True)
    (broken_outline_root / "outline.json").write_text("{invalid", encoding="utf-8")
    assert service._read_outline_fallback(str(broken_outline_root)) is None

    outline_root = tmp_path / "outline-ok"
    outline_root.mkdir(parents=True)
    (outline_root / "outline.json").write_text(
        json.dumps({"title": "Recap", "summary": "核心结论"}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert service._read_outline_fallback(str(outline_root)) == "# Recap\n\n核心结论"


def test_feed_service_list_digest_feed_applies_cursor_filters_and_has_more(
    tmp_path: Path, monkeypatch
) -> None:
    ts1 = datetime(2026, 2, 25, 10, 0, tzinfo=UTC)
    ts2 = datetime(2026, 2, 25, 9, 0, tzinfo=UTC)
    ts3 = datetime(2026, 2, 25, 8, 0, tzinfo=UTC)

    digest_1 = tmp_path / "digest-1.md"
    digest_2 = tmp_path / "digest-2.md"
    digest_3 = tmp_path / "digest-3.md"
    digest_1.write_text("# d1", encoding="utf-8")
    digest_2.write_text("# d2", encoding="utf-8")
    digest_3.write_text("# d3", encoding="utf-8")

    rows = [
        {
            "job_id": "job-3",
            "source_url": "https://example.com/v3",
            "source": "youtube",
            "title": "",
            "video_uid": "v-3",
            "published_at": ts1,
            "created_at": ts1,
            "sort_ts": ts1,
            "category": "tech",
            "subscription_source_type": "url",
            "subscription_source_value": "https://youtube.com/@demo",
            "artifact_digest_md": str(digest_1),
            "artifact_root": None,
        },
        {
            "job_id": "job-2",
            "source_url": "https://example.com/v2",
            "source": "youtube",
            "title": "Video 2",
            "video_uid": "v-2",
            "published_at": ts2,
            "created_at": ts2,
            "sort_ts": ts2,
            "category": "tech",
            "subscription_source_type": "url",
            "subscription_source_value": "https://youtube.com/@demo",
            "artifact_digest_md": str(digest_2),
            "artifact_root": None,
        },
        {
            "job_id": "job-1",
            "source_url": "https://example.com/v1",
            "source": "youtube",
            "title": "Video 1",
            "video_uid": "v-1",
            "published_at": ts3,
            "created_at": ts3,
            "sort_ts": ts3,
            "category": "tech",
            "subscription_source_type": "url",
            "subscription_source_value": "https://youtube.com/@demo",
            "artifact_digest_md": str(digest_3),
            "artifact_root": None,
        },
    ]

    fake_db = _FakeDB(rows)
    service = FeedService(db=fake_db)  # type: ignore[arg-type]
    result = service.list_digest_feed(
        source="youtube",
        category=" Tech ",
        limit=2,
        cursor="2026-02-24T09:00:00+00:00__job-0",
    )

    params = fake_db.calls[0]["params"]
    assert params["category"] == "tech"
    assert params["limit"] == 3
    assert params["cursor_ts"] == "2026-02-24T09:00:00+00:00"
    assert params["cursor_job_id"] == "job-0"

    assert result["has_more"] is True
    assert len(result["items"]) == 2
    assert result["next_cursor"] == f"{ts2.isoformat()}__job-2"
    assert result["items"][0]["title"] == "v-3"
    assert result["items"][0]["source_name"] in {"youtube", "Demo Channel"}
    assert result["items"][0]["artifact_type"] == "digest"


def test_feed_service_parse_cursor_and_title_resolution() -> None:
    service = FeedService(db=None)  # type: ignore[arg-type]

    assert service._parse_cursor(None) == (None, None)
    assert service._parse_cursor("invalid") == (None, None)
    assert service._parse_cursor("ts__") == (None, None)
    assert service._parse_cursor("ts__job-1") == ("ts", "job-1")

    assert service._resolve_title({"title": "  T  "}) == "T"
    assert service._resolve_title({"title": "", "video_uid": "vid-1"}) == "vid-1"
    assert (
        service._resolve_title({"title": "", "video_uid": "", "source_url": "https://x"})
        == "https://x"
    )
    assert service._resolve_title({"title": "", "video_uid": "", "source_url": ""}) == "Untitled"
