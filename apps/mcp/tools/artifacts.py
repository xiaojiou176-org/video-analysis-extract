from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def _is_error_payload(payload: dict[str, Any]) -> bool:
    return {"code", "message", "details"}.issubset(payload.keys())


def _to_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _normalize_markdown_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if _is_error_payload(payload):
        return payload

    markdown = payload.get("markdown")
    if not isinstance(markdown, str):
        text = payload.get("text")
        markdown = text if isinstance(text, str) else ""

    return {
        "markdown": markdown,
        "job_id": _to_optional_str(payload.get("job_id")),
        "video_url": _to_optional_str(payload.get("video_url")),
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
