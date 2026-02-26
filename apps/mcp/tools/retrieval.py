from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import (
    ApiCall,
    is_error_payload,
    to_int,
    to_optional_dict,
    to_optional_str,
)


def _normalize_retrieval_item(item: Any) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    return {
        "job_id": to_optional_str(source.get("job_id")),
        "video_id": to_optional_str(source.get("video_id")),
        "platform": to_optional_str(source.get("platform")),
        "video_uid": to_optional_str(source.get("video_uid")),
        "source_url": to_optional_str(source.get("source_url")),
        "title": to_optional_str(source.get("title")),
        "kind": to_optional_str(source.get("kind")),
        "mode": to_optional_str(source.get("mode")),
        "source": to_optional_str(source.get("source")),
        "snippet": to_optional_str(source.get("snippet")),
        "score": float(source.get("score"))
        if isinstance(source.get("score"), (int, float))
        else 0.0,
    }


def register_retrieval_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(
        name="vd.retrieval.search",
        description="Search retrieval index over generated artifacts (digest/transcript/outline/comments).",
    )
    def retrieval_search(
        query: str,
        top_k: int = 10,
        mode: Literal["keyword", "semantic", "hybrid"] = "keyword",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = api_call(
            "POST",
            "/api/v1/retrieval/search",
            json_body={
                "query": query,
                "top_k": top_k,
                "mode": mode,
                "filters": filters or {},
            },
        )
        if is_error_payload(response):
            return response

        items = response.get("items")
        return {
            "query": to_optional_str(response.get("query")) or query,
            "top_k": to_int(response.get("top_k"), default=top_k),
            "filters": to_optional_dict(response.get("filters")) or (filters or {}),
            "items": [
                _normalize_retrieval_item(item)
                for item in (items if isinstance(items, list) else [])
            ],
        }
