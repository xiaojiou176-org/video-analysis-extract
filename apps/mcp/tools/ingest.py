from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import invalid_argument, parse_uuid

ApiCall = Callable[..., dict[str, Any]]


def register_ingest_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.ingest.poll", description="Trigger one ingest poll cycle.")
    def ingest_poll(
        subscription_id: str | None = None,
        platform: str | None = None,
        max_new_videos: int | None = None,
    ) -> dict[str, Any]:
        normalized_subscription_id: str | None = None
        if subscription_id is not None:
            normalized_subscription_id = parse_uuid(subscription_id)
            if normalized_subscription_id is None:
                return invalid_argument(
                    "subscription_id must be a valid UUID",
                    method="POST",
                    path="/api/v1/ingest/poll",
                    field="subscription_id",
                    value=subscription_id,
                )
        return api_call(
            "POST",
            "/api/v1/ingest/poll",
            json_body={
                "subscription_id": normalized_subscription_id,
                "platform": platform,
                "max_new_videos": max_new_videos,
            },
        )
