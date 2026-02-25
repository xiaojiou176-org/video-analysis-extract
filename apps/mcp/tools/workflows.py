from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import (
    ApiCall,
    invalid_argument,
    is_error_payload,
    parse_workflow_id,
    to_optional_dict,
    to_optional_str,
    validate_object_keys,
)

_WORKFLOW_PAYLOAD_ALLOWLIST: dict[str, set[str]] = {
    "poll_feeds": {"run_once", "subscription_id", "platform", "max_new_videos"},
    "daily_digest": {"run_once", "timezone_name", "timezone_offset_minutes", "local_hour"},
    "notification_retry": {"run_once", "interval_minutes", "retry_batch_limit"},
    "cleanup": {
        "run_once",
        "interval_hours",
        "workspace_dir",
        "older_than_hours",
        "cache_dir",
        "cache_older_than_hours",
        "cache_max_size_mb",
    },
    "provider_canary": {"run_once", "interval_hours", "timeout_seconds"},
}


def register_workflow_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(
        name="vd.workflows.run",
        description="Start operational Temporal workflows via API gateway.",
    )
    def run_workflow(
        workflow: str,
        run_once: bool = True,
        wait_for_result: bool = False,
        workflow_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_workflow = str(workflow or "").strip()
        allowed_payload_keys = _WORKFLOW_PAYLOAD_ALLOWLIST.get(normalized_workflow)
        if allowed_payload_keys is None:
            return invalid_argument(
                "workflow must be one of: poll_feeds, daily_digest, notification_retry, cleanup, provider_canary",
                method="POST",
                path="/api/v1/workflows/run",
                field="workflow",
                value=workflow,
            )
        normalized_workflow_id: str | None = None
        if workflow_id is not None:
            normalized_workflow_id = parse_workflow_id(workflow_id)
            if normalized_workflow_id is None:
                return invalid_argument(
                    "workflow_id must match ^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$",
                    method="POST",
                    path="/api/v1/workflows/run",
                    field="workflow_id",
                    value=workflow_id,
                )
        normalized_payload, payload_error = validate_object_keys(
            payload or {},
            allowed_keys=allowed_payload_keys,
        )
        if payload_error is not None or normalized_payload is None:
            return invalid_argument(
                f"payload {payload_error or 'is invalid'}",
                method="POST",
                path="/api/v1/workflows/run",
                field="payload",
            )
        response = api_call(
            "POST",
            "/api/v1/workflows/run",
            json_body={
                "workflow": normalized_workflow,
                "run_once": run_once,
                "wait_for_result": wait_for_result,
                "workflow_id": normalized_workflow_id,
                "payload": normalized_payload,
            },
        )
        if is_error_payload(response):
            return response
        return {
            "workflow": to_optional_str(response.get("workflow")),
            "workflow_name": to_optional_str(response.get("workflow_name")),
            "workflow_id": to_optional_str(response.get("workflow_id")),
            "run_id": to_optional_str(response.get("run_id")),
            "status": to_optional_str(response.get("status")),
            "started_at": to_optional_str(response.get("started_at")),
            "result": to_optional_dict(response.get("result")),
        }
