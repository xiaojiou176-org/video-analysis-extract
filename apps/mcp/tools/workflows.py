from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import ApiCall, is_error_payload, to_optional_dict, to_optional_str


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
        response = api_call(
            "POST",
            "/api/v1/workflows/run",
            json_body={
                "workflow": workflow,
                "run_once": run_once,
                "wait_for_result": wait_for_result,
                "workflow_id": workflow_id,
                "payload": payload or {},
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
