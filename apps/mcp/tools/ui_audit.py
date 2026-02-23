from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import ApiCall, is_error_payload, to_int, to_optional_bool, to_optional_str


def _normalize_summary(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    severity_counts = source.get("severity_counts")
    normalized_counts: dict[str, int] = {}
    if isinstance(severity_counts, dict):
        for key, item in severity_counts.items():
            if isinstance(key, str):
                normalized_counts[key] = to_int(item, default=0)
    return {
        "artifact_count": to_int(source.get("artifact_count"), default=0),
        "finding_count": to_int(source.get("finding_count"), default=0),
        "severity_counts": normalized_counts,
    }


def _normalize_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if is_error_payload(payload):
        return payload

    source = payload.get("run") if isinstance(payload.get("run"), dict) else payload
    return {
        "run_id": to_optional_str(source.get("run_id")),
        "job_id": to_optional_str(source.get("job_id")),
        "artifact_root": to_optional_str(source.get("artifact_root")),
        "status": to_optional_str(source.get("status")) or "unknown",
        "created_at": to_optional_str(source.get("created_at")),
        "summary": _normalize_summary(source.get("summary")),
    }


def _normalize_finding(item: Any) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    return {
        "id": to_optional_str(source.get("id")) or "",
        "severity": to_optional_str(source.get("severity")) or "info",
        "title": to_optional_str(source.get("title")) or "",
        "message": to_optional_str(source.get("message")) or "",
        "rule": to_optional_str(source.get("rule")),
        "artifact_key": to_optional_str(source.get("artifact_key")),
    }


def _normalize_artifact(item: Any) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    return {
        "key": to_optional_str(source.get("key")) or "",
        "path": to_optional_str(source.get("path")) or "",
        "mime_type": to_optional_str(source.get("mime_type")) or "application/octet-stream",
        "size_bytes": to_int(source.get("size_bytes"), default=0),
        "category": to_optional_str(source.get("category")) or "artifact",
    }


def _normalize_autofix_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if is_error_payload(payload):
        return payload

    summary_source = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    guardrails = payload.get("guardrails") if isinstance(payload.get("guardrails"), dict) else {}
    actions = payload.get("suggested_actions")
    raw_actions = actions if isinstance(actions, list) else []
    return {
        "run_id": to_optional_str(payload.get("run_id")),
        "mode": to_optional_str(payload.get("mode")) or "dry-run",
        "autofix_applied": bool(to_optional_bool(payload.get("autofix_applied"))),
        "summary": {
            "finding_count": to_int(summary_source.get("finding_count"), default=0),
            "high_or_worse_count": to_int(summary_source.get("high_or_worse_count"), default=0),
        },
        "guardrails": guardrails,
        "suggested_actions": [str(item) for item in raw_actions],
    }


def register_ui_audit_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.ui_audit.run", description="Run UI audit from artifact directory evidence.")
    def ui_audit_run(
        job_id: str | None = None,
        artifact_root: str | None = None,
    ) -> dict[str, Any]:
        response = api_call(
            "POST",
            "/api/v1/ui-audit/run",
            json_body={
                "job_id": job_id,
                "artifact_root": artifact_root,
            },
        )
        return _normalize_run_payload(response)

    @mcp.tool(
        name="vd.ui_audit.read",
        description="Read UI audit results. action=get|list_findings|get_artifact|autofix.",
    )
    def ui_audit_read(
        action: str,
        run_id: str,
        severity: str | None = None,
        key: str | None = None,
        include_base64: bool = False,
        mode: str = "dry-run",
        max_files: int = 3,
        max_changed_lines: int = 120,
    ) -> dict[str, Any]:
        normalized_action = str(action or "").strip().lower()

        if normalized_action == "get":
            response = api_call("GET", f"/api/v1/ui-audit/{run_id}")
            return _normalize_run_payload(response)

        if normalized_action == "list_findings":
            response = api_call(
                "GET",
                f"/api/v1/ui-audit/{run_id}/findings",
                params={"severity": severity},
            )
            if is_error_payload(response):
                return response
            items = response.get("items")
            raw_items = items if isinstance(items, list) else []
            return {
                "run_id": run_id,
                "severity": severity,
                "items": [_normalize_finding(item) for item in raw_items],
            }

        if normalized_action == "get_artifact":
            if not key:
                return {
                    "code": "INVALID_ARGUMENT",
                    "message": "key is required when action=get_artifact",
                    "details": {"method": "GET", "path": "/api/v1/ui-audit/{run_id}/artifact"},
                }
            response = api_call(
                "GET",
                f"/api/v1/ui-audit/{run_id}/artifact",
                params={
                    "key": key,
                    "include_base64": include_base64,
                },
            )
            if is_error_payload(response):
                return response
            payload = _normalize_artifact(response)
            payload["exists"] = bool(response.get("exists", False))
            payload["base64"] = to_optional_str(response.get("base64")) if include_base64 else None
            return payload

        if normalized_action == "autofix":
            response = api_call(
                "POST",
                f"/api/v1/ui-audit/{run_id}/autofix",
                json_body={
                    "mode": mode,
                    "max_files": max_files,
                    "max_changed_lines": max_changed_lines,
                },
            )
            return _normalize_autofix_payload(response)

        return {
            "code": "INVALID_ARGUMENT",
            "message": "action must be one of: get, list_findings, get_artifact, autofix",
            "details": {"method": "POST", "path": "vd.ui_audit.read"},
        }
