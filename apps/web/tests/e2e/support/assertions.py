from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

from support.mock_api import MockApiState


def wait_for_call_count(
    state: MockApiState,
    key: str,
    expected: int,
    timeout_sec: float = 5.0,
    *,
    exact: bool = True,
) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        actual = state.call_count(key)
        if (actual == expected) if exact else (actual >= expected):
            return
        time.sleep(0.05)
    qualifier = "==" if exact else ">="
    raise AssertionError(
        f"Timed out waiting for `{key}` calls: expected {qualifier} {expected}, actual={state.call_count(key)}"
    )


def wait_for_http_path(state: MockApiState, path: str, timeout_sec: float = 5.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with state.lock:
            if any(item.get("path") == path for item in state.calls["http"]):
                return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for HTTP path call: {path}")


def wait_for_http_query_fragment(
    state: MockApiState,
    path: str,
    query_fragment: str,
    timeout_sec: float = 5.0,
) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with state.lock:
            if any(item.get("path") == path and query_fragment in item.get("query", "") for item in state.calls["http"]):
                return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for HTTP query fragment: {path}?...{query_fragment}")


def wait_for_http_call(
    state: MockApiState,
    *,
    method: str | None = None,
    path: str | None = None,
    status: int | None = None,
    query_fragment: str | None = None,
    payload_contains: dict[str, Any] | None = None,
    payload_check: Callable[[dict[str, Any] | None], bool] | None = None,
    timeout_sec: float = 5.0,
) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    method_upper = method.upper() if method else None

    while time.time() < deadline:
        with state.lock:
            calls = list(state.calls["http"])
        for call in calls:
            if method_upper and call.get("method") != method_upper:
                continue
            if path and call.get("path") != path:
                continue
            if status is not None and call.get("status") != status:
                continue
            if query_fragment and query_fragment not in call.get("query", ""):
                continue
            payload = call.get("payload")
            if payload_contains:
                if not isinstance(payload, dict):
                    continue
                if not all(payload.get(k) == v for k, v in payload_contains.items()):
                    continue
            if payload_check and not payload_check(payload if isinstance(payload, dict) else None):
                continue
            return dict(call)
        time.sleep(0.05)

    raise AssertionError(
        "Timed out waiting for HTTP call "
        f"(method={method!r}, path={path!r}, status={status!r}, query_fragment={query_fragment!r})"
    )
