from __future__ import annotations

import json
import os
import base64
from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .tools.artifacts import register_artifact_tools
from .tools.computer_use import register_computer_use_tools
from .tools.health import register_health_tools
from .tools.ingest import register_ingest_tools
from .tools.jobs import register_job_tools
from .tools.notifications import register_notification_tools
from .tools.retrieval import register_retrieval_tools
from .tools.subscriptions import register_subscription_tools
from .tools.ui_audit import register_ui_audit_tools
from .tools.workflows import register_workflow_tools


class ApiError(RuntimeError):
    """Raised when the backing API returns an error response."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": _normalize_error_details(self.details),
        }


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    timeout_sec: float
    api_key: str | None

    @classmethod
    def from_env(cls) -> "ApiConfig":
        return cls(
            base_url=os.getenv("VD_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            timeout_sec=float(os.getenv("VD_API_TIMEOUT_SEC", "20")),
            api_key=os.getenv("VD_API_KEY"),
        )


class ApiClient:
    def __init__(self, config: ApiConfig) -> None:
        self._config = config

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        return_bytes_base64: bool = False,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        url = f"{self._config.base_url}{path}"
        try:
            with httpx.Client(timeout=self._config.timeout_sec) as http_client:
                response = http_client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise ApiError(
                "UPSTREAM_TIMEOUT",
                "Upstream API request timed out.",
                {"method": method, "path": path, "error": str(exc)},
            ) from exc
        except httpx.HTTPError as exc:
            raise ApiError(
                "UPSTREAM_NETWORK_ERROR",
                "Failed to reach upstream API.",
                {"method": method, "path": path, "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            error_body = _read_response_body(response)
            raise ApiError(
                "UPSTREAM_HTTP_ERROR",
                _extract_error_message(
                    error_body,
                    fallback=f"{method} {path} failed with status {response.status_code}.",
                ),
                {
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "body_preview": _stringify_value(error_body)[:400],
                },
            )

        if not response.content:
            return {"ok": True}

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            if return_bytes_base64:
                return {
                    "base64": base64.b64encode(response.content).decode("ascii"),
                    "mime_type": content_type or "application/octet-stream",
                    "size_bytes": len(response.content),
                }
            return {"text": response.text}

        try:
            data = response.json()
        except ValueError:
            return {"text": response.text}

        if isinstance(data, dict):
            return data
        return {"items": data}


def _drop_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _read_response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return response.text
    return response.text


def _extract_error_message(error_body: Any, fallback: str) -> str:
    if isinstance(error_body, dict):
        for key in ("message", "detail", "error", "title"):
            value = error_body.get(key)
            if isinstance(value, str) and value.strip():
                return value
        detail = error_body.get("detail")
        if isinstance(detail, list) and detail:
            return _stringify_value(detail[0]) or fallback
    if isinstance(error_body, str) and error_body.strip():
        return error_body.strip()
    return fallback


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _normalize_error_details(details: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    method = details.get("method")
    if isinstance(method, str) and method:
        normalized["method"] = method

    path = details.get("path")
    if isinstance(path, str) and path:
        normalized["path"] = path

    status_code = details.get("status_code")
    if isinstance(status_code, int):
        normalized["status_code"] = status_code

    error = details.get("error")
    if error is not None:
        normalized["error"] = _stringify_value(error)

    body_preview = details.get("body_preview")
    if body_preview is not None:
        normalized["body_preview"] = _stringify_value(body_preview)

    return normalized


def create_server() -> FastMCP:
    config = ApiConfig.from_env()
    api_client = ApiClient(config)
    mcp = FastMCP("video-data-phase3")

    def api_call(
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        return_bytes_base64: bool = False,
    ) -> dict[str, Any]:
        normalized_params = _drop_none_values(params or {}) or None
        normalized_body = _drop_none_values(json_body or {}) or None
        try:
            return api_client.request(
                method=method,
                path=path,
                params=normalized_params,
                json_body=normalized_body,
                return_bytes_base64=return_bytes_base64,
            )
        except ApiError as exc:
            return exc.to_payload()
        except Exception as exc:  # pragma: no cover - defensive boundary
            return {
                "code": "MCP_INTERNAL_ERROR",
                "message": "Unexpected MCP server error.",
                "details": _normalize_error_details(
                    {
                        "method": method,
                        "path": path,
                        "error": str(exc),
                    }
                ),
            }

    register_subscription_tools(mcp, api_call)
    register_ingest_tools(mcp, api_call)
    register_job_tools(mcp, api_call)
    register_artifact_tools(mcp, api_call)
    register_notification_tools(mcp, api_call)
    register_health_tools(mcp, api_call)
    register_workflow_tools(mcp, api_call)
    register_retrieval_tools(mcp, api_call)
    register_computer_use_tools(mcp, api_call)
    register_ui_audit_tools(mcp, api_call)
    return mcp


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
