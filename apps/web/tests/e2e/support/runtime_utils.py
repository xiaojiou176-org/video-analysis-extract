from __future__ import annotations

import os
import errno
import re
import socket
import time
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Callable, TypeVar
from urllib.parse import urlparse
from urllib.request import urlopen

T = TypeVar("T")


def slugify_nodeid(nodeid: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", nodeid).strip("-")
    return value or "unknown-test"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def is_port_in_use_error(exc: BaseException) -> bool:
    return isinstance(exc, OSError) and exc.errno == errno.EADDRINUSE


def with_free_port_retry(
    start: Callable[[int], T],
    *,
    attempts: int = 3,
    port_supplier: Callable[[], int] | None = None,
    retry_if: Callable[[Exception], bool] | None = None,
) -> tuple[T, int]:
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    provide_port = port_supplier or free_port
    should_retry = retry_if or is_port_in_use_error
    last_error: Exception | None = None

    for attempt in range(attempts):
        port = provide_port()
        try:
            return start(port), port
        except Exception as exc:
            if should_retry(exc) and attempt < attempts - 1:
                last_error = exc
                continue
            raise

    raise RuntimeError(f"Unable to start service after {attempts} attempts") from last_error


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def wait_http_ok(url: str, timeout_sec: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_error: Exception | None = None
    backoff_sec = 0.05
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < HTTPStatus.INTERNAL_SERVER_ERROR:
                    return
        except Exception as exc:  # pragma: no cover - only for startup retries
            last_error = exc
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(backoff_sec, remaining))
            backoff_sec = min(backoff_sec * 2, 0.5)
    raise RuntimeError(f"Timeout waiting for server readiness: {url}. Last error: {last_error}")


def external_web_base_url_from_env() -> str | None:
    raw_value = os.getenv("WEB_BASE_URL")
    if raw_value is None:
        return None
    candidate = raw_value.strip().rstrip("/")
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"WEB_BASE_URL must be an absolute http(s) URL, got: {raw_value!r}")
    return candidate
