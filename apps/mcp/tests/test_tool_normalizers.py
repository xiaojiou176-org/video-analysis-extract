from __future__ import annotations

from typing import Any, Callable

from apps.mcp.tools._common import (
    is_error_payload,
    to_int,
    to_optional_bool,
    to_optional_dict,
    to_optional_int,
    to_optional_str,
)
from apps.mcp.tools.artifacts import _normalize_markdown_payload
from apps.mcp.tools.health import register_health_tools
from apps.mcp.tools.jobs import _normalize_job_payload, register_job_tools
from apps.mcp.tools.notifications import (
    _normalize_send_test_payload,
    _normalize_set_config_payload,
)


def test_common_normalizers_handle_basic_types() -> None:
    assert is_error_payload({"code": "E", "message": "bad", "details": {"x": 1}}) is True
    assert is_error_payload({"code": "E", "message": "bad"}) is False
    assert to_optional_str("abc") == "abc"
    assert to_optional_str(1) is None
    assert to_int("7", default=0) == 7
    assert to_int("x", default=3) == 3
    assert to_optional_dict({"x": 1}) == {"x": 1}
    assert to_optional_dict("x") is None
    assert to_optional_bool(True) is True
    assert to_optional_bool(1) is None
    assert to_optional_int(5) == 5
    assert to_optional_int("5") is None


def test_artifact_normalizer_marks_payload_found_when_markdown_present() -> None:
    payload = _normalize_markdown_payload(
        {
            "markdown": "# digest",
            "job_id": "job-1",
            "video_url": "https://example.com/video",
        }
    )

    assert payload["found"] is True
    assert payload["markdown"] == "# digest"
    assert payload["job_id"] == "job-1"


def test_job_normalizer_keeps_extended_pipeline_fields() -> None:
    normalized = _normalize_job_payload(
        {
            "id": "job-1",
            "status": "running",
            "mode": "text_only",
            "pipeline_final_status": "degraded",
            "llm_required": True,
            "llm_gate_passed": False,
            "hard_fail_reason": "llm_gate_blocked",
            "artifacts_index": {
                "digest_markdown": "/tmp/artifacts/digest.md",
                "step_json": "/tmp/artifacts/steps.json",
            },
            "step_summary": [
                {
                    "name": "fetch_metadata",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": "2026-02-21T10:00:00Z",
                    "finished_at": "2026-02-21T10:00:03Z",
                }
            ],
            "steps": [
                {
                    "name": "llm_digest",
                    "status": "failed",
                    "attempt": 2,
                    "started_at": "2026-02-21T10:01:00Z",
                    "finished_at": "2026-02-21T10:01:02Z",
                    "error": {"detail": "upstream timeout"},
                    "error_kind": "timeout",
                    "retry_meta": {"max_attempts": 2},
                    "result": {"fallback_used": True},
                    "cache_key": "llm_digest:v1",
                }
            ],
            "degradations": [
                {
                    "step": "llm_digest",
                    "status": "failed",
                    "reason": "fallback_to_local_template",
                    "error": {"detail": "upstream timeout"},
                    "error_kind": "timeout",
                    "retry_meta": {"attempt": 2},
                    "cache_meta": {"hit": False},
                }
            ],
            "notification_retry": {
                "delivery_id": "00000000-0000-0000-0000-000000000123",
                "status": "failed",
                "attempt_count": 3,
                "next_retry_at": "2026-02-22T01:00:00Z",
                "last_error_kind": "transient",
            },
        }
    )

    assert normalized["id"] == "job-1"
    assert normalized["status"] == "running"
    assert normalized["mode"] == "text_only"
    assert normalized["pipeline_final_status"] == "degraded"
    assert normalized["llm_required"] is True
    assert normalized["llm_gate_passed"] is False
    assert normalized["hard_fail_reason"] == "llm_gate_blocked"
    assert normalized["artifacts_index"]["digest_markdown"] == "/tmp/artifacts/digest.md"
    assert normalized["step_summary"][0]["name"] == "fetch_metadata"
    assert normalized["step_summary"][0]["attempt"] == 1
    assert normalized["steps"][0]["name"] == "llm_digest"
    assert normalized["steps"][0]["error_kind"] == "timeout"
    assert normalized["steps"][0]["retry_meta"] == {"max_attempts": 2}
    assert normalized["degradations"][0]["reason"] == "fallback_to_local_template"
    assert normalized["degradations"][0]["cache_meta"] == {"hit": False}
    assert normalized["notification_retry"]["status"] == "failed"
    assert normalized["notification_retry"]["attempt_count"] == 3


def test_notification_normalizers_return_expected_core_fields() -> None:
    send_test = _normalize_send_test_payload(
        {
            "delivery_id": "delivery-1",
            "status": "sent",
            "provider_message_id": "provider-1",
            "recipient_email": "demo@example.com",
            "subject": "hello",
            "created_at": "2026-02-21T10:00:00Z",
        }
    )
    set_config = _normalize_set_config_payload(
        {
            "enabled": True,
            "to_email": "demo@example.com",
            "daily_digest_enabled": False,
            "daily_digest_hour_utc": 8,
            "failure_alert_enabled": True,
            "updated_at": "2026-02-21T10:00:00Z",
        }
    )

    assert send_test["delivery_id"] == "delivery-1"
    assert send_test["status"] == "sent"
    assert send_test["recipient_email"] == "demo@example.com"
    assert set_config["enabled"] is True
    assert set_config["daily_digest_hour_utc"] == 8
    assert set_config["updated_at"] == "2026-02-21T10:00:00Z"


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def tool(self, *, name: str, description: str):
        def _decorator(func: Callable[..., dict[str, Any]]):
            self.tools[name] = func
            return func

        return _decorator


def test_videos_process_normalizes_missing_overrides_to_empty_object() -> None:
    mcp = _FakeMCP()
    calls: list[dict[str, Any]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {"ok": True}

    register_job_tools(mcp, fake_api_call)
    response = mcp.tools["vd.videos.process"](
        video={
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        }
    )

    assert response["ok"] is True
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/v1/videos/process"
    assert calls[0]["kwargs"]["json_body"]["overrides"] == {}


def test_health_providers_tool_normalizes_payload() -> None:
    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "GET"
        assert path == "/api/v1/health/providers"
        assert kwargs["params"]["window_hours"] == 24
        return {
            "window_hours": 24,
            "providers": [
                {
                    "provider": "rsshub",
                    "ok": 2,
                    "warn": 1,
                    "fail": 0,
                    "last_status": "ok",
                    "last_checked_at": "2026-02-21T10:00:00Z",
                    "last_error_kind": None,
                    "last_message": "ok",
                }
            ],
        }

    register_health_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.health.providers"](window_hours=24)

    assert payload["window_hours"] == 24
    assert payload["providers"][0]["provider"] == "rsshub"
    assert payload["providers"][0]["ok"] == 2
