from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def _is_error_payload(payload: dict[str, Any]) -> bool:
    return {"code", "message", "details"}.issubset(payload.keys())


def _to_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_optional_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _normalize_step(item: Any) -> dict[str, Any]:
    step = item if isinstance(item, dict) else {}
    error_value = step.get("error")
    return {
        "name": _to_optional_str(step.get("name")) or "",
        "status": _to_optional_str(step.get("status")) or "unknown",
        "attempt": _to_int(step.get("attempt"), default=0),
        "started_at": _to_optional_str(step.get("started_at")),
        "finished_at": _to_optional_str(step.get("finished_at")),
        "error": None if error_value is None else str(error_value),
    }


def _normalize_step_detail(item: Any) -> dict[str, Any]:
    step = _normalize_step(item)
    source = item if isinstance(item, dict) else {}
    step["error_kind"] = _to_optional_str(source.get("error_kind"))
    step["retry_meta"] = _to_optional_dict(source.get("retry_meta"))
    step["result"] = _to_optional_dict(source.get("result"))
    step["cache_key"] = _to_optional_str(source.get("cache_key"))
    return step


def _normalize_degradation(item: Any) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    return {
        "step": _to_optional_str(source.get("step")),
        "status": _to_optional_str(source.get("status")),
        "reason": _to_optional_str(source.get("reason")),
        "error": source.get("error"),
        "error_kind": _to_optional_str(source.get("error_kind")),
        "retry_meta": _to_optional_dict(source.get("retry_meta")),
        "cache_meta": _to_optional_dict(source.get("cache_meta")),
    }


def _normalize_artifacts_index(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, item in value.items():
        if isinstance(key, str) and isinstance(item, str):
            normalized[key] = item
    return normalized


def _normalize_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if _is_error_payload(payload):
        return payload

    job = payload.get("job")
    source = job if isinstance(job, dict) else payload
    step_summary = source.get("step_summary")
    step_summary_items = step_summary if isinstance(step_summary, list) else []
    steps = source.get("steps")
    step_items = steps if isinstance(steps, list) else []
    degradations = source.get("degradations")
    degradation_items = degradations if isinstance(degradations, list) else []

    return {
        "id": _to_optional_str(source.get("id")),
        "video_id": _to_optional_str(source.get("video_id")),
        "kind": _to_optional_str(source.get("kind")),
        "status": _to_optional_str(source.get("status")),
        "idempotency_key": _to_optional_str(source.get("idempotency_key")),
        "error_message": _to_optional_str(source.get("error_message")),
        "artifact_digest_md": _to_optional_str(source.get("artifact_digest_md")),
        "artifact_root": _to_optional_str(source.get("artifact_root")),
        "created_at": _to_optional_str(source.get("created_at")),
        "updated_at": _to_optional_str(source.get("updated_at")),
        "step_summary": [_normalize_step(item) for item in step_summary_items],
        "steps": [_normalize_step_detail(item) for item in step_items],
        "degradations": [_normalize_degradation(item) for item in degradation_items],
        "pipeline_final_status": _to_optional_str(source.get("pipeline_final_status")),
        "artifacts_index": _normalize_artifacts_index(source.get("artifacts_index")),
        "mode": _to_optional_str(source.get("mode")),
    }


def register_job_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.jobs.get", description="Get one job by id.")
    def get_job(job_id: str) -> dict[str, Any]:
        response = api_call("GET", f"/api/v1/jobs/{job_id}")
        return _normalize_job_payload(response)

    @mcp.tool(name="vd.videos.list", description="List ingested videos.")
    def list_videos(
        platform: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        return api_call(
            "GET",
            "/api/v1/videos",
            params={
                "platform": platform,
                "status": status,
                "limit": limit,
            },
        )

    @mcp.tool(name="vd.videos.process", description="Trigger ProcessJobWorkflow for one video.")
    def process_video(
        video: dict[str, Any],
        mode: str = "full",
        overrides: dict[str, Any] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        return api_call(
            "POST",
            "/api/v1/videos/process",
            json_body={
                "video": video,
                "mode": mode,
                "overrides": overrides,
                "force": force,
            },
        )
