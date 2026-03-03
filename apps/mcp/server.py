from __future__ import annotations

import base64
import json
import os
import re
import time
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
            "message": _redact_sensitive_text(self.message),
            "details": _normalize_error_details(self.details),
        }


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    timeout_sec: float
    api_key: str | None
    max_base64_bytes: int = 2 * 1024 * 1024
    retry_attempts: int = 1
    retry_backoff_sec: float = 0.2

    @classmethod
    def from_env(cls) -> ApiConfig:
        def _env_float(name: str, default: float) -> float:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                return float(raw.strip())
            except (TypeError, ValueError):
                return default

        def _env_positive_int(
            name: str,
            default: int,
            *,
            min_value: int = 1,
            max_value: int | None = None,
        ) -> int:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                value = int(raw.strip())
            except (TypeError, ValueError):
                return default
            bounded = value if value >= min_value else min_value
            if max_value is not None and bounded > max_value:
                return max_value
            return bounded

        def _env_bounded_float(
            name: str,
            default: float,
            *,
            min_value: float,
            max_value: float,
        ) -> float:
            raw = os.getenv(name)
            if raw is None:
                return default
            try:
                value = float(raw.strip())
            except (TypeError, ValueError):
                return default
            if value < min_value:
                return min_value
            if value > max_value:
                return max_value
            return value

        return cls(
            base_url=os.getenv("VD_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            timeout_sec=_env_float("VD_API_TIMEOUT_SEC", 20.0),
            api_key=os.getenv("VD_API_KEY"),
            max_base64_bytes=_env_positive_int("VD_MCP_MAX_BASE64_BYTES", 2 * 1024 * 1024),
            retry_attempts=_env_positive_int(
                "VD_API_RETRY_ATTEMPTS",
                1,
                min_value=1,
                max_value=5,
            ),
            retry_backoff_sec=_env_bounded_float(
                "VD_API_RETRY_BACKOFF_SEC",
                0.2,
                min_value=0.0,
                max_value=5.0,
            ),
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
        normalized_path = _normalize_upstream_path(path)
        normalized_method = str(method or "").upper()
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        url = f"{self._config.base_url}{normalized_path}"
        attempts = max(self._config.retry_attempts, 1)
        is_retryable_method = normalized_method in {"GET", "HEAD", "OPTIONS"}
        last_exception: httpx.HTTPError | None = None
        response: httpx.Response | None = None
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=self._config.timeout_sec) as http_client:
                    response = http_client.request(
                        method=normalized_method,
                        url=url,
                        params=params,
                        json=json_body,
                        headers=headers,
                    )
                if response.status_code >= 400:
                    error_body = _read_response_body(response)
                    should_retry = (
                        is_retryable_method
                        and attempt < attempts
                        and response.status_code in {429, 502, 503, 504}
                    )
                    if should_retry:
                        _sleep_with_backoff(self._config.retry_backoff_sec, attempt)
                        continue
                    raise ApiError(
                        "UPSTREAM_HTTP_ERROR",
                        _extract_error_message(
                            error_body,
                            fallback=f"{normalized_method} {normalized_path} failed with status {response.status_code}.",
                        ),
                        {
                            "method": normalized_method,
                            "path": normalized_path,
                            "status_code": response.status_code,
                            "body_preview": _safe_body_preview(error_body),
                            "attempts": attempt,
                        },
                    )
                break
            except httpx.TimeoutException as exc:
                last_exception = exc
                if is_retryable_method and attempt < attempts:
                    _sleep_with_backoff(self._config.retry_backoff_sec, attempt)
                    continue
                raise ApiError(
                    "UPSTREAM_TIMEOUT",
                    "Upstream API request timed out.",
                    {
                        "method": normalized_method,
                        "path": normalized_path,
                        "error": str(exc),
                        "attempts": attempt,
                    },
                ) from exc
            except httpx.HTTPError as exc:
                last_exception = exc
                if is_retryable_method and attempt < attempts:
                    _sleep_with_backoff(self._config.retry_backoff_sec, attempt)
                    continue
                raise ApiError(
                    "UPSTREAM_NETWORK_ERROR",
                    "Failed to reach upstream API.",
                    {
                        "method": normalized_method,
                        "path": normalized_path,
                        "error": str(exc),
                        "attempts": attempt,
                    },
                ) from exc

        if response is None:
            raise ApiError(
                "UPSTREAM_NETWORK_ERROR",
                "Failed to reach upstream API.",
                {
                    "method": normalized_method,
                    "path": normalized_path,
                    "error": str(last_exception) if last_exception else "unknown error",
                    "attempts": attempts,
                },
            )

        if not response.content:
            return {"ok": True}

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            if return_bytes_base64:
                size_bytes = len(response.content)
                if size_bytes > self._config.max_base64_bytes:
                    raise ApiError(
                        "PAYLOAD_TOO_LARGE",
                        "Binary payload exceeds base64 return limit.",
                        {
                            "method": method,
                            "path": normalized_path,
                            "size_bytes": size_bytes,
                            "max_size_bytes": self._config.max_base64_bytes,
                        },
                    )
                return {
                    "base64": base64.b64encode(response.content).decode("ascii"),
                    "mime_type": content_type or "application/octet-stream",
                    "size_bytes": size_bytes,
                }
            return {"text": response.text}

        try:
            data = response.json()
        except ValueError:
            return {"text": response.text}

        if isinstance(data, dict):
            return data
        return {"items": data}


def _sleep_with_backoff(base_delay_sec: float, attempt: int) -> None:
    delay = max(base_delay_sec, 0.0) * attempt
    if delay > 0:
        time.sleep(delay)


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
        normalized["error"] = _redact_sensitive_text(_stringify_value(error))

    body_preview = details.get("body_preview")
    if body_preview is not None:
        normalized["body_preview"] = _redact_sensitive_text(_stringify_value(body_preview))

    size_bytes = details.get("size_bytes")
    if isinstance(size_bytes, int):
        normalized["size_bytes"] = size_bytes

    max_size_bytes = details.get("max_size_bytes")
    if isinstance(max_size_bytes, int):
        normalized["max_size_bytes"] = max_size_bytes
    attempts = details.get("attempts")
    if isinstance(attempts, int) and attempts > 0:
        normalized["attempts"] = attempts

    return normalized


_PATH_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\b(authorization\s*:\s*bearer\s+)[^\s,;]+"),
    re.compile(
        r"(?i)\b((?:api[_-]?key|apikey|key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|oauth[_-]?token|jwt|secret|client[_-]?secret|password|passwd|session(?:id)?|auth(?:orization)?|signature)\s*[=:]\s*)[^\s,;]+"
    ),
    re.compile(
        r'(?i)(["\'](?:api[_-]?key|apikey|key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|oauth[_-]?token|jwt|secret|client[_-]?secret|password|passwd|session(?:id)?|auth(?:orization)?|signature)["\']\s*:\s*["\'])[^"\']+'
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
]


def _normalize_upstream_path(path: str) -> str:
    text = str(path or "").strip()
    if not text:
        raise ApiError(
            "INVALID_UPSTREAM_PATH",
            "Upstream request path must be a non-empty relative path starting with '/'.",
            {"path": path},
        )
    if not text.startswith("/") or text.startswith("//") or _PATH_SCHEME_PATTERN.match(text):
        raise ApiError(
            "INVALID_UPSTREAM_PATH",
            "Upstream request path must be a relative API path.",
            {"path": path},
        )
    if any(char in text for char in ("\r", "\n", "\x00")):
        raise ApiError(
            "INVALID_UPSTREAM_PATH",
            "Upstream request path contains invalid control characters.",
            {"path": path},
        )
    if "?" in text or "#" in text:
        raise ApiError(
            "INVALID_UPSTREAM_PATH",
            "Upstream request path must not include query strings or fragments.",
            {"path": path},
        )
    segments = [segment for segment in text.split("/") if segment not in ("", ".")]
    if any(segment == ".." for segment in segments):
        raise ApiError(
            "INVALID_UPSTREAM_PATH",
            "Upstream request path must not contain traversal segments.",
            {"path": path},
        )
    return text


def _safe_body_preview(error_body: Any, max_chars: int = 400) -> str:
    preview = _stringify_value(error_body)[:max_chars]
    return _redact_sensitive_text(preview)


def _redact_sensitive_text(value: str) -> str:
    text = value
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(
            lambda m: f"{m.group(1)}[REDACTED]" if m.groups() else "[REDACTED]", text
        )
    return text


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
