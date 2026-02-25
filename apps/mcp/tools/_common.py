from __future__ import annotations

import base64
import os
import re
from pathlib import PurePosixPath
from typing import Any, Callable
from urllib.parse import quote
from uuid import UUID

ApiCall = Callable[..., dict[str, Any]]

DEFAULT_MAX_BASE64_BYTES = int(os.getenv("VD_MCP_MAX_BASE64_BYTES", "2097152"))
_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


def is_error_payload(payload: dict[str, Any]) -> bool:
    return {"code", "message", "details"}.issubset(payload.keys())


def to_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_optional_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def to_optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def to_optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def invalid_argument(
    message: str,
    *,
    method: str,
    path: str,
    field: str | None = None,
    value: Any | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {"method": method, "path": path}
    if field is not None:
        details["field"] = field
    if value is not None:
        details["value"] = str(value)
    return {
        "code": "INVALID_ARGUMENT",
        "message": message,
        "details": details,
    }


def parse_uuid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return str(UUID(text))
    except ValueError:
        return None


def parse_workflow_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text if _WORKFLOW_ID_PATTERN.fullmatch(text) else None


def url_path_segment(value: str) -> str:
    return quote(value, safe="")


def parse_artifact_relative_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if "\x00" in text:
        return None
    if text.startswith(("/", "\\", "~")):
        return None
    if "://" in text:
        return None
    if _WINDOWS_DRIVE_PATTERN.match(text):
        return None

    posix_value = text.replace("\\", "/")
    path = PurePosixPath(posix_value)
    parts = [part for part in path.parts if part not in ("", ".")]
    if not parts:
        return None
    if any(part == ".." for part in parts):
        return None
    normalized = PurePosixPath(*parts).as_posix()
    return normalized if normalized else None


def validate_object_keys(value: Any, *, allowed_keys: set[str]) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict):
        return None, "must be an object"
    unknown_keys = sorted(key for key in value.keys() if isinstance(key, str) and key not in allowed_keys)
    if unknown_keys:
        return None, f"contains unsupported keys: {', '.join(unknown_keys)}"
    non_string_keys = [str(key) for key in value.keys() if not isinstance(key, str)]
    if non_string_keys:
        return None, "contains non-string keys"
    return dict(value), None


def validate_base64_size(value: Any, *, max_bytes: int = DEFAULT_MAX_BASE64_BYTES) -> tuple[bool, str | None]:
    if not isinstance(value, str):
        return False, "must be a base64 string"
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        return False, "must be valid base64"
    if len(raw) > max_bytes:
        return False, f"decoded payload exceeds {max_bytes} bytes"
    return True, None
