from __future__ import annotations

from typing import Any, Callable

ApiCall = Callable[..., dict[str, Any]]


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
