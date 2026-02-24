from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def register_subscription_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(
        name="vd.subscriptions.manage",
        description="Manage subscriptions. action=list|upsert|remove|batch_update_category.",
    )
    def manage_subscriptions(
        action: str,
        id: str | None = None,
        platform: str | None = None,
        category: str | None = None,
        ids: list[str] | None = None,
        enabled_only: bool | None = None,
        source_type: str | None = None,
        source_value: str | None = None,
        adapter_type: str | None = None,
        source_url: str | None = None,
        rsshub_route: str | None = None,
        tags: list[str] | None = None,
        priority: int | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        normalized_action = str(action or "").strip().lower()
        if normalized_action == "list":
            return api_call(
                "GET",
                "/api/v1/subscriptions",
                params={
                    "platform": platform,
                    "category": category,
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
                    "adapter_type": adapter_type,
                    "source_url": source_url,
                    "rsshub_route": rsshub_route,
                    "category": category,
                    "tags": tags or [],
                    "priority": priority,
                    "enabled": enabled,
                },
            )
        if normalized_action == "batch_update_category":
            return api_call(
                "POST",
                "/api/v1/subscriptions/batch-update-category",
                json_body={
                    "ids": ids or [],
                    "category": category,
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
            "message": "action must be one of: list, upsert, remove, batch_update_category",
            "details": {"method": "POST", "path": "vd.subscriptions.manage"},
        }
