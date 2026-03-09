from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.mcp.tools.ingest import register_ingest_tools
from apps.mcp.tools.workflows import _normalize_workflow_payload, register_workflow_tools

UUID_1 = "11111111-1111-1111-1111-111111111111"


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {}

    def tool(self, *, name: str, description: str):
        def _decorator(func: Callable[..., dict[str, Any]]):
            self.tools[name] = func
            return func

        return _decorator


def test_ingest_poll_rejects_invalid_subscription_id() -> None:
    mcp = _FakeMCP()
    register_ingest_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    payload = mcp.tools["vd.ingest.poll"](subscription_id="sub-1")

    assert payload["code"] == "INVALID_ARGUMENT"
    assert payload["details"]["field"] == "subscription_id"
    assert payload["details"]["path"] == "/api/v1/ingest/poll"


def test_ingest_poll_rejects_invalid_max_new_videos() -> None:
    mcp = _FakeMCP()
    register_ingest_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    payload = mcp.tools["vd.ingest.poll"](max_new_videos=0)

    assert payload["code"] == "INVALID_ARGUMENT"
    assert payload["details"]["field"] == "max_new_videos"


def test_ingest_poll_posts_expected_payload_with_normalized_uuid() -> None:
    mcp = _FakeMCP()
    calls: list[dict[str, Any]] = []

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, "kwargs": kwargs})
        return {"ok": True}

    register_ingest_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.ingest.poll"](
        subscription_id=UUID_1.upper(),
        platform="youtube",
        max_new_videos=10,
    )

    assert payload["ok"] is True
    assert calls == [
        {
            "method": "POST",
            "path": "/api/v1/ingest/poll",
            "kwargs": {
                "json_body": {
                    "subscription_id": UUID_1,
                    "platform": "youtube",
                    "max_new_videos": 10,
                }
            },
        }
    ]


def test_workflows_run_rejects_invalid_workflow_id() -> None:
    mcp = _FakeMCP()
    register_workflow_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    payload = mcp.tools["vd.workflows.run"](
        workflow="daily_digest",
        workflow_id="bad workflow id",
    )

    assert payload["code"] == "INVALID_ARGUMENT"
    assert payload["details"]["field"] == "workflow_id"


def test_workflows_run_rejects_unknown_workflow_name() -> None:
    mcp = _FakeMCP()
    register_workflow_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    payload = mcp.tools["vd.workflows.run"](workflow="not-supported")

    assert payload["code"] == "INVALID_ARGUMENT"
    assert payload["details"]["field"] == "workflow"


def test_workflows_run_passes_through_error_payload_from_upstream() -> None:
    mcp = _FakeMCP()

    def fake_api_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "POST"
        assert path == "/api/v1/workflows/run"
        assert kwargs["json_body"]["workflow"] == "daily_digest"
        return {
            "code": "UPSTREAM_HTTP_ERROR",
            "message": "gateway unavailable",
            "details": {"status_code": 503},
        }

    register_workflow_tools(mcp, fake_api_call)
    payload = mcp.tools["vd.workflows.run"](workflow="daily_digest")

    assert payload["code"] == "UPSTREAM_HTTP_ERROR"
    assert payload["details"]["status_code"] == 503


def test_workflows_run_rejects_invalid_boolean_flags() -> None:
    mcp = _FakeMCP()
    calls = 0

    def fake_api_call(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"ok": True}

    register_workflow_tools(mcp, fake_api_call)

    bad_run_once = mcp.tools["vd.workflows.run"](
        workflow="daily_digest",
        run_once="true",  # type: ignore[arg-type]
    )
    bad_wait_for_result = mcp.tools["vd.workflows.run"](
        workflow="daily_digest",
        wait_for_result="false",  # type: ignore[arg-type]
    )

    assert bad_run_once["code"] == "INVALID_ARGUMENT"
    assert bad_run_once["details"]["field"] == "run_once"
    assert bad_wait_for_result["code"] == "INVALID_ARGUMENT"
    assert bad_wait_for_result["details"]["field"] == "wait_for_result"
    assert calls == 0


def test_workflows_run_rejects_invalid_payload_value_ranges() -> None:
    mcp = _FakeMCP()
    register_workflow_tools(mcp, lambda *_args, **_kwargs: {"ok": True})

    payload = mcp.tools["vd.workflows.run"](
        workflow="daily_digest",
        payload={"local_hour": 30},
    )

    assert payload["code"] == "INVALID_ARGUMENT"
    assert payload["details"]["field"] == "payload.local_hour"


def test_workflows_payload_normalizer_covers_bool_and_range_branches() -> None:
    invalid_payload, field, error = _normalize_workflow_payload(
        "poll_feeds",
        {"run_once": "yes"},
    )
    assert invalid_payload is None
    assert field == "run_once"
    assert error == "payload.run_once must be a boolean"

    poll_feeds, field, error = _normalize_workflow_payload(
        "poll_feeds",
        {"run_once": True, "max_new_videos": 25},
    )
    assert error is None and field is None
    assert poll_feeds == {"run_once": True, "max_new_videos": 25}

    notification_retry, field, error = _normalize_workflow_payload(
        "notification_retry",
        {"interval_minutes": 15, "retry_batch_limit": 9},
    )
    assert error is None and field is None
    assert notification_retry == {"interval_minutes": 15, "retry_batch_limit": 9}

    provider_canary, field, error = _normalize_workflow_payload(
        "provider_canary",
        {"interval_hours": 4, "timeout_seconds": 60},
    )
    assert error is None and field is None
    assert provider_canary == {"interval_hours": 4, "timeout_seconds": 60}
