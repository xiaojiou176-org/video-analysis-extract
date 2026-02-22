from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import ApiCall, is_error_payload, to_int, to_optional_str


def _normalize_provider_item(item: Any) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    return {
        "provider": to_optional_str(source.get("provider")) or "",
        "ok": to_int(source.get("ok"), default=0),
        "warn": to_int(source.get("warn"), default=0),
        "fail": to_int(source.get("fail"), default=0),
        "last_status": to_optional_str(source.get("last_status")),
        "last_checked_at": to_optional_str(source.get("last_checked_at")),
        "last_error_kind": to_optional_str(source.get("last_error_kind")),
        "last_message": to_optional_str(source.get("last_message")),
    }


def register_health_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.health.system", description="Get system liveness healthz.")
    def get_system_health() -> dict[str, Any]:
        response = api_call("GET", "/healthz")
        if is_error_payload(response):
            return response
        status = to_optional_str(response.get("status")) or "unknown"
        return {"status": status}

    @mcp.tool(name="vd.health.providers", description="Get provider health rollup.")
    def get_provider_health(window_hours: int = 24) -> dict[str, Any]:
        response = api_call(
            "GET",
            "/api/v1/health/providers",
            params={"window_hours": window_hours},
        )
        if is_error_payload(response):
            return response
        items = response.get("providers")
        providers = items if isinstance(items, list) else []
        return {
            "window_hours": to_int(response.get("window_hours"), default=24),
            "providers": [_normalize_provider_item(item) for item in providers],
        }
