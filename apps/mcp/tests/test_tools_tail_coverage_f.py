from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.mcp.tools._common import (
    parse_artifact_relative_path,
    parse_uuid,
    parse_workflow_id,
    validate_base64_size,
    validate_object_keys,
)
from apps.mcp.tools.artifacts import _normalize_markdown_payload, register_artifact_tools
from apps.mcp.tools.health import register_health_tools
from apps.mcp.tools.jobs import _normalize_job_payload, register_job_tools
from apps.mcp.tools.notifications import (
    _normalize_send_test_payload,
    _normalize_set_config_payload,
    register_notification_tools,
)
from apps.mcp.tools.subscriptions import register_subscription_tools
from apps.mcp.tools.ui_audit import (
    _normalize_autofix_payload,
    _normalize_run_payload,
    register_ui_audit_tools,
)

UUID_1 = "11111111-1111-1111-1111-111111111111"
UUID_2 = "22222222-2222-2222-2222-222222222222"


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def tool(self, *, name: str, description: str):
        del description

        def _decorator(func: Callable[..., dict[str, Any]]):
            self.tools[name] = func
            return func

        return _decorator


def test_common_tail_branches() -> None:
    assert parse_uuid(123) is None
    assert parse_uuid("   ") is None
    assert parse_workflow_id(1) is None
    assert parse_workflow_id("  ") is None

    assert parse_artifact_relative_path(None) is None
    assert parse_artifact_relative_path(" ") is None
    assert parse_artifact_relative_path("bad\x00path") is None
    assert parse_artifact_relative_path("C:\\temp\\a.png") is None
    assert parse_artifact_relative_path(".") is None
    assert parse_artifact_relative_path("frames%2Fa.png") == "frames/a.png"
    assert parse_artifact_relative_path("%2e%2e/secret.txt") is None
    assert parse_artifact_relative_path("%2fetc/passwd") is None
    assert parse_artifact_relative_path("%5cwindows\\system.ini") is None
    assert parse_artifact_relative_path("%252e%252e%252fsecret.txt") is None

    parsed, error = validate_object_keys("x", allowed_keys={"a"})
    assert parsed is None
    assert error == "must be an object"

    parsed2, error2 = validate_object_keys({1: "x"}, allowed_keys={"a"})
    assert parsed2 is None
    assert error2 == "contains non-string keys"

    ok, message = validate_base64_size(1)
    assert ok is False
    assert message == "must be a base64 string"

    ok2, message2 = validate_base64_size("not-base64")
    assert ok2 is False
    assert message2 == "must be valid base64"


def test_artifacts_tail_branches() -> None:
    assert (
        _normalize_markdown_payload({"code": "X", "message": "bad", "details": {}})["code"] == "X"
    )
    assert _normalize_markdown_payload({"text": "fallback text"}) == {
        "markdown": "fallback text",
        "job_id": None,
        "video_url": None,
        "found": True,
    }

    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if path == "/api/v1/artifacts/markdown":
            return {"text": "fallback md"}
        if path == "/api/v1/artifacts/assets":
            if kwargs["params"]["path"] == "missing.png":
                return {"code": "NOT_FOUND", "message": "nope", "details": "not-a-dict"}
            return {"code": "BAD", "message": "bad", "details": {"status_code": 404}}
        raise AssertionError(path)

    register_artifact_tools(mcp, fake_api_call)

    bad_markdown_job = mcp.tools["vd.artifacts.get"](kind="markdown", job_id="bad")
    assert bad_markdown_job["code"] == "INVALID_ARGUMENT"

    missing_required = mcp.tools["vd.artifacts.get"](kind="asset", job_id=None, path=None)
    assert missing_required["code"] == "INVALID_ARGUMENT"

    bad_kind = mcp.tools["vd.artifacts.get"](kind="other")
    assert bad_kind["code"] == "INVALID_ARGUMENT"

    markdown = mcp.tools["vd.artifacts.get"](kind="markdown")
    assert markdown["markdown"] == "fallback md"

    passthrough = mcp.tools["vd.artifacts.get"](kind="asset", job_id=UUID_1, path="missing.png")
    assert passthrough["code"] == "NOT_FOUND"


def test_health_tail_branches() -> None:
    mcp = _FakeMCP()

    def api_error_on_system(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        del method, kwargs
        if path == "/healthz":
            return {"code": "UPSTREAM", "message": "bad", "details": {}}
        raise AssertionError(path)

    register_health_tools(mcp, api_error_on_system)
    invalid_scope_payload = mcp.tools["vd.health.get"](scope="invalid")
    assert invalid_scope_payload["code"] == "UPSTREAM"

    def api_error_on_providers(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        del method, kwargs
        if path == "/api/v1/health/providers":
            return {"code": "UPSTREAM", "message": "bad", "details": {}}
        raise AssertionError(path)

    register_health_tools(mcp, api_error_on_providers)
    providers_error = mcp.tools["vd.health.get"](scope="providers")
    assert providers_error["code"] == "UPSTREAM"


def test_jobs_tail_branches() -> None:
    assert (
        _normalize_job_payload({"code": "UPSTREAM", "message": "bad", "details": {}})["code"]
        == "UPSTREAM"
    )

    normalized = _normalize_job_payload(
        {
            "id": "job-1",
            "degradations": ["bad-shape"],
            "artifacts_index": "not-a-dict",
            "notification_retry": {"delivery_id": "d-1", "attempt_count": "2"},
        }
    )
    assert normalized["degradations"][0]["step"] is None
    assert normalized["artifacts_index"] == {}
    assert normalized["notification_retry"]["attempt_count"] == 2

    mcp = _FakeMCP()
    calls: list[tuple[str, str]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, path))
        if path.startswith("/api/v1/jobs/"):
            return {"id": "job-1", "status": "running"}
        if path == "/api/v1/videos":
            return {"items": []}
        if path == "/api/v1/videos/process":
            return {"ok": True}
        raise AssertionError(path)

    register_job_tools(mcp, fake_api_call)

    get_ok = mcp.tools["vd.jobs.get"](job_id=UUID_1.upper())
    assert get_ok["id"] == "job-1"

    list_ok = mcp.tools["vd.videos.list"](platform="youtube")
    assert list_ok["items"] == []

    bad_video_shape = mcp.tools["vd.videos.process"](video="bad")
    assert bad_video_shape["code"] == "INVALID_ARGUMENT"

    missing_platform = mcp.tools["vd.videos.process"](video={"url": "https://example.com"})
    assert missing_platform["details"]["field"] == "video.platform"

    missing_url = mcp.tools["vd.videos.process"](video={"platform": "youtube"})
    assert missing_url["details"]["field"] == "video.url"

    bad_override_value = mcp.tools["vd.videos.process"](
        video={"platform": "youtube", "url": "https://example.com"},
        overrides={"llm": "bad"},
    )
    assert bad_override_value["details"]["field"] == "overrides"

    assert ("GET", f"/api/v1/jobs/{UUID_1}") in calls
    assert ("GET", "/api/v1/videos") in calls


def test_notifications_tail_branches() -> None:
    assert (
        _normalize_send_test_payload({"code": "X", "message": "bad", "details": {}})["code"] == "X"
    )
    assert (
        _normalize_set_config_payload({"code": "X", "message": "bad", "details": {}})["code"] == "X"
    )

    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        del method, kwargs
        if path == "/api/v1/reports/daily/send":
            return {"code": "UPSTREAM", "message": "bad", "details": {}}
        raise AssertionError(path)

    register_notification_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.notifications.manage"](action="daily_send")
    assert payload["code"] == "UPSTREAM"


def test_subscriptions_tail_branches() -> None:
    mcp = _FakeMCP()
    register_subscription_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    bad_batch = mcp.tools["vd.subscriptions.manage"](action="batch_update_category", ids=["bad"])
    assert bad_batch["code"] == "INVALID_ARGUMENT"

    missing_remove_id = mcp.tools["vd.subscriptions.manage"](action="remove")
    assert missing_remove_id["details"]["field"] == "id"

    bad_action = mcp.tools["vd.subscriptions.manage"](action="unknown")
    assert bad_action["code"] == "INVALID_ARGUMENT"


def test_ui_audit_tail_branches() -> None:
    assert _normalize_run_payload({"code": "X", "message": "bad", "details": {}})["code"] == "X"
    assert _normalize_autofix_payload({"code": "X", "message": "bad", "details": {}})["code"] == "X"

    run_mcp = _FakeMCP()
    register_ui_audit_tools(run_mcp, lambda *_args, **_kwargs: {"ok": True})
    run_invalid = run_mcp.tools["vd.ui_audit.run"](job_id="bad")
    assert run_invalid["code"] == "INVALID_ARGUMENT"

    mcp = _FakeMCP()
    run_id = UUID_2

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if path == f"/api/v1/ui-audit/{run_id}/findings":
            return {"code": "UPSTREAM", "message": "bad", "details": {}}
        if path == f"/api/v1/ui-audit/{run_id}/artifact":
            if kwargs["params"]["key"] == "bad/error.json":
                return {"code": "UPSTREAM", "message": "bad", "details": {}}
            return {
                "key": "axe.json",
                "path": "/tmp/axe.json",
                "mime_type": "application/json",
                "size_bytes": 10,
                "category": "playwright",
                "exists": True,
                "base64": "e30=",
            }
        raise AssertionError(path)

    register_ui_audit_tools(mcp, fake_api_call)

    list_error = mcp.tools["vd.ui_audit.read"](action="list_findings", run_id=run_id)
    assert list_error["code"] == "UPSTREAM"

    missing_key = mcp.tools["vd.ui_audit.read"](action="get_artifact", run_id=run_id, key=None)
    assert missing_key["code"] == "INVALID_ARGUMENT"

    bad_key = mcp.tools["vd.ui_audit.read"](action="get_artifact", run_id=run_id, key="../x")
    assert bad_key["code"] == "INVALID_ARGUMENT"

    passthrough_error = mcp.tools["vd.ui_audit.read"](
        action="get_artifact",
        run_id=run_id,
        key="bad/error.json",
        include_base64=True,
    )
    assert passthrough_error["code"] == "UPSTREAM"

    no_base64 = mcp.tools["vd.ui_audit.read"](action="get_artifact", run_id=run_id, key="axe.json")
    assert no_base64["base64"] is None

    invalid_action = mcp.tools["vd.ui_audit.read"](action="unknown", run_id=run_id)
    assert invalid_action["code"] == "INVALID_ARGUMENT"
