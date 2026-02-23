from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def register_subscription_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(
        name="vd.subscriptions.manage",
        description="Manage subscriptions. action=list|upsert|remove.",
    )
    def manage_subscriptions(
        action: str,
        id: str | None = None,
        platform: str | None = None,
        enabled_only: bool | None = None,
        source_type: str | None = None,
        source_value: str | None = None,
        rsshub_route: str | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        normalized_action = str(action or "").strip().lower()
        if normalized_action == "list":
            return api_call(
                "GET",
                "/api/v1/subscriptions",
                params={
                    "platform": platform,
                    "enabled_only": enabled_only,
                },
            )
        if normalized_action == "upsert":
            return api_call(
                "POST",
                "/api/v1/subscriptions",
                json_body={
                    "platform": platform,
                    "source_type": source_type,
                    "source_value": source_value,
                    "rsshub_route": rsshub_route,
                    "enabled": enabled,
                },
            )
        if normalized_action == "remove":
            if not id:
                return {
                    "code": "INVALID_ARGUMENT",
                    "message": "id is required when action=remove",
                    "details": {"method": "DELETE", "path": "/api/v1/subscriptions/{id}"},
                }
            return api_call("DELETE", f"/api/v1/subscriptions/{id}")
        return {
            "code": "INVALID_ARGUMENT",
            "message": "action must be one of: list, upsert, remove",
            "details": {"method": "POST", "path": "vd.subscriptions.manage"},
        }
