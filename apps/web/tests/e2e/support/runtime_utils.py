from __future__ import annotations

import os
import re
import socket
import time
from datetime import UTC, datetime
from http import HTTPStatus
from urllib.parse import urlparse
from urllib.request import urlopen


def slugify_nodeid(nodeid: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", nodeid).strip("-")
    return value or "unknown-test"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def wait_http_ok(url: str, timeout_sec: float = 90.0) -> None:
    deadline = time.time() + timeout_sec
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < HTTPStatus.INTERNAL_SERVER_ERROR:
                    return
        except Exception as exc:  # pragma: no cover - only for startup retries
            last_error = exc
        time.sleep(0.5)
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
