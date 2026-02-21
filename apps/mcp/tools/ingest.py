from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def register_ingest_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.ingest.poll", description="Trigger one ingest poll cycle.")
    def ingest_poll(
        subscription_id: str | None = None,
        platform: str | None = None,
        max_new_videos: int | None = None,
    ) -> dict[str, Any]:
        return api_call(
            "POST",
            "/api/v1/ingest/poll",
            json_body={
                "subscription_id": subscription_id,
                "platform": platform,
                "max_new_videos": max_new_videos,
            },
        )
