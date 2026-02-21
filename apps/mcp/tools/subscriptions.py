from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def register_subscription_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.subscriptions.list", description="List video subscriptions.")
    def list_subscriptions(
        platform: str | None = None,
        enabled_only: bool | None = None,
    ) -> dict[str, Any]:
        return api_call(
            "GET",
            "/api/v1/subscriptions",
            params={
                "platform": platform,
                "enabled_only": enabled_only,
            },
        )

    @mcp.tool(name="vd.subscriptions.upsert", description="Create or update a subscription.")
    def upsert_subscription(
        platform: str,
        source_type: str,
        source_value: str,
        rsshub_route: str | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
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

    @mcp.tool(name="vd.subscriptions.remove", description="Remove one subscription.")
    def remove_subscription(id: str) -> dict[str, Any]:
        return api_call("DELETE", f"/api/v1/subscriptions/{id}")
