from __future__ import annotations

from urllib.parse import urlencode
from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import ApiCall, is_error_payload, to_optional_str


def _normalize_markdown_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if is_error_payload(payload):
        return payload

    markdown = payload.get("markdown")
    if not isinstance(markdown, str):
        text = payload.get("text")
        markdown = text if isinstance(text, str) else ""

    return {
        "markdown": markdown,
        "job_id": to_optional_str(payload.get("job_id")),
        "video_url": to_optional_str(payload.get("video_url")),
        "found": bool(markdown),
    }


def register_artifact_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.artifacts.get_markdown", description="Read digest markdown artifact text.")
    def get_artifact_markdown(
        job_id: str | None = None,
        video_url: str | None = None,
    ) -> dict[str, Any]:
        response = api_call(
            "GET",
            "/api/v1/artifacts/markdown",
            params={
                "job_id": job_id,
                "video_url": video_url,
            },
        )
        return _normalize_markdown_payload(response)

    @mcp.tool(
        name="vd.artifacts.get_asset",
        description="Get artifact asset URL and optionally inline base64 bytes.",
    )
    def get_artifact_asset(
        job_id: str,
        path: str,
        include_base64: bool = False,
    ) -> dict[str, Any]:
        response = api_call(
            "GET",
            "/api/v1/artifacts/assets",
            params={"job_id": job_id, "path": path},
            return_bytes_base64=include_base64,
        )
        if is_error_payload(response):
            return {
                **response,
                "exists": False,
                "asset_url": None,
                "mime_type": None,
                "base64": None,
                "size_bytes": None,
            }
        query = urlencode({"job_id": job_id, "path": path})
        return {
            "exists": True,
            "asset_url": f"/api/v1/artifacts/assets?{query}",
            "mime_type": to_optional_str(response.get("mime_type")) or "application/octet-stream",
            "base64": to_optional_str(response.get("base64")) if include_base64 else None,
            "size_bytes": response.get("size_bytes") if include_base64 else None,
        }
