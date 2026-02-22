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
from apps.mcp.tools.artifacts import _normalize_markdown_payload, register_artifact_tools
from apps.mcp.tools.computer_use import register_computer_use_tools
from apps.mcp.tools.health import register_health_tools
from apps.mcp.tools.jobs import _normalize_job_payload, register_job_tools
from apps.mcp.tools.notifications import (
    _normalize_send_test_payload,
    _normalize_set_config_payload,
    register_notification_tools,
)
from apps.mcp.tools.retrieval import register_retrieval_tools
from apps.mcp.tools.workflows import register_workflow_tools


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
            "hard_fail_reason": "llm_provider_unavailable",
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
                    "result": {"degraded": True, "provider": "gemini"},
                    "thought_metadata": {"provider": "gemini", "thought_tokens": 32},
                    "cache_key": "llm_digest:v1",
                }
            ],
            "degradations": [
                {
                    "step": "llm_digest",
                    "status": "failed",
                    "reason": "llm_provider_unavailable",
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
    assert normalized["hard_fail_reason"] == "llm_provider_unavailable"
    assert normalized["artifacts_index"]["digest_markdown"] == "/tmp/artifacts/digest.md"
    assert normalized["step_summary"][0]["name"] == "fetch_metadata"
    assert normalized["step_summary"][0]["attempt"] == 1
    assert normalized["steps"][0]["name"] == "llm_digest"
    assert normalized["steps"][0]["error_kind"] == "timeout"
    assert normalized["steps"][0]["retry_meta"] == {"max_attempts": 2}
    assert normalized["steps"][0]["thought_metadata"] == {"provider": "gemini", "thought_tokens": 32}
    assert normalized["degradations"][0]["reason"] == "llm_provider_unavailable"
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


def test_artifacts_get_asset_tool_exposes_asset_url_and_base64() -> None:
    mcp = _FakeMCP()
    calls: list[dict[str, Any]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "mime_type": "image/jpeg",
            "base64": "dGVzdA==",
            "size_bytes": 4,
        }

    register_artifact_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.artifacts.get_asset"](
        job_id="00000000-0000-0000-0000-000000000001",
        path="frames/frame_001.jpg",
        include_base64=True,
    )

    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == "/api/v1/artifacts/assets"
    assert calls[0]["kwargs"]["params"] == {
        "job_id": "00000000-0000-0000-0000-000000000001",
        "path": "frames/frame_001.jpg",
    }
    assert calls[0]["kwargs"]["return_bytes_base64"] is True
    assert payload["exists"] is True
    assert payload["asset_url"] == (
        "/api/v1/artifacts/assets?job_id=00000000-0000-0000-0000-000000000001&path=frames%2Fframe_001.jpg"
    )
    assert payload["mime_type"] == "image/jpeg"
    assert payload["base64"] == "dGVzdA=="
    assert payload["size_bytes"] == 4


def test_retrieval_search_tool_normalizes_payload() -> None:
    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "POST"
        assert path == "/api/v1/retrieval/search"
        assert kwargs["json_body"]["query"] == "timeout"
        assert kwargs["json_body"]["top_k"] == 3
        return {
            "query": "timeout",
            "top_k": 3,
            "filters": {"platform": "youtube"},
            "items": [
                {
                    "job_id": "job-1",
                    "video_id": "video-1",
                    "platform": "youtube",
                    "video_uid": "abc123",
                    "source_url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Demo",
                    "kind": "video_digest_v1",
                    "mode": "full",
                    "source": "digest",
                    "snippet": "provider timeout",
                    "score": 2.2,
                }
            ],
        }

    register_retrieval_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.retrieval.search"](
        query="timeout",
        top_k=3,
        filters={"platform": "youtube"},
    )

    assert payload["query"] == "timeout"
    assert payload["top_k"] == 3
    assert payload["filters"] == {"platform": "youtube"}
    assert payload["items"][0]["source"] == "digest"
    assert payload["items"][0]["score"] == 2.2


def test_notifications_get_config_tool_normalizes_payload() -> None:
    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "GET"
        assert path == "/api/v1/notifications/config"
        assert kwargs == {}
        return {
            "enabled": True,
            "to_email": "ops@example.com",
            "daily_digest_enabled": True,
            "daily_digest_hour_utc": 8,
            "failure_alert_enabled": False,
            "created_at": "2026-02-22T01:00:00Z",
            "updated_at": "2026-02-22T01:10:00Z",
        }

    register_notification_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.notifications.get_config"]()

    assert payload["enabled"] is True
    assert payload["to_email"] == "ops@example.com"
    assert payload["daily_digest_enabled"] is True
    assert payload["daily_digest_hour_utc"] == 8
    assert payload["failure_alert_enabled"] is False


def test_health_system_tool_returns_status() -> None:
    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "GET"
        assert path == "/healthz"
        assert kwargs == {}
        return {"status": "ok"}

    register_health_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.health.system"]()

    assert payload["status"] == "ok"


def test_workflows_run_tool_posts_expected_body_and_normalizes_result() -> None:
    mcp = _FakeMCP()
    calls: list[dict[str, Any]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "workflow": "daily_digest",
            "workflow_name": "DailyDigestWorkflow",
            "workflow_id": "wf-123",
            "run_id": "run-456",
            "status": "started",
            "started_at": "2026-02-22T08:00:00Z",
            "result": {"ok": True},
        }

    register_workflow_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.workflows.run"](
        workflow="daily_digest",
        run_once=True,
        wait_for_result=False,
        workflow_id="wf-123",
        payload={"scope": "all"},
    )

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/v1/workflows/run"
    assert calls[0]["kwargs"]["json_body"] == {
        "workflow": "daily_digest",
        "run_once": True,
        "wait_for_result": False,
        "workflow_id": "wf-123",
        "payload": {"scope": "all"},
    }
    assert payload["workflow"] == "daily_digest"
    assert payload["workflow_name"] == "DailyDigestWorkflow"
    assert payload["workflow_id"] == "wf-123"
    assert payload["run_id"] == "run-456"
    assert payload["status"] == "started"
    assert payload["result"] == {"ok": True}


def test_computer_use_run_tool_posts_expected_body_and_normalizes_result() -> None:
    mcp = _FakeMCP()
    calls: list[dict[str, Any]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {
            "actions": [
                {
                    "step": 1,
                    "action": "click",
                    "target": "submit button",
                    "input_text": None,
                    "reasoning": "click submit button",
                }
            ],
            "require_confirmation": True,
            "blocked_actions": ["submit"],
            "final_text": "Need confirmation.",
            "thought_metadata": {"planner": "rule_based"},
        }

    register_computer_use_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.computer_use.run"](
        instruction="click submit button",
        screenshot_base64="ZmFrZQ==",
        safety={"blocked_actions": ["submit"], "confirm_before_execute": False},
    )

    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/v1/computer-use/run"
    assert calls[0]["kwargs"]["json_body"] == {
        "instruction": "click submit button",
        "screenshot_base64": "ZmFrZQ==",
        "safety": {"blocked_actions": ["submit"], "confirm_before_execute": False},
    }
    assert payload["actions"][0]["step"] == 1
    assert payload["actions"][0]["action"] == "click"
    assert payload["require_confirmation"] is True
    assert payload["blocked_actions"] == ["submit"]
    assert payload["final_text"] == "Need confirmation."
    assert payload["thought_metadata"] == {"planner": "rule_based"}
