from __future__ import annotations

import time

from support.mock_api import MockApiState


def wait_for_call_count(state: MockApiState, key: str, expected: int, timeout_sec: float = 5.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if state.call_count(key) >= expected:
            return
        time.sleep(0.05)
    raise AssertionError(
        f"Timed out waiting for `{key}` calls: expected >= {expected}, actual={state.call_count(key)}"
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
