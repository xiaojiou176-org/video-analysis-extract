from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = PROJECT_ROOT / "apps" / "web"
WEB_E2E_ARTIFACT_ROOT = PROJECT_ROOT / ".runtime-cache" / "web-e2e-artifacts"
WEB_E2E_VIDEO_DIR = WEB_E2E_ARTIFACT_ROOT / "videos"
WEB_E2E_TRACE_DIR = WEB_E2E_ARTIFACT_ROOT / "traces"
WEB_E2E_SCREENSHOT_DIR = WEB_E2E_ARTIFACT_ROOT / "screenshots"
PING_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sYfA8kAAAAASUVORK5CYII="
)

for artifact_dir in (WEB_E2E_VIDEO_DIR, WEB_E2E_TRACE_DIR, WEB_E2E_SCREENSHOT_DIR):
    artifact_dir.mkdir(parents=True, exist_ok=True)


def _slugify_nodeid(nodeid: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", nodeid).strip("-")
    return value or "unknown-test"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _wait_http_ok(url: str, timeout_sec: float = 90.0) -> None:
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


def _external_web_base_url_from_env() -> str | None:
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


@dataclass
class MockApiState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    subscriptions: list[dict[str, Any]] = field(default_factory=list)
    notification_config: dict[str, Any] = field(default_factory=dict)
    calls: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    job_id: str = "job-e2e-001"
    health_status: int = int(HTTPStatus.OK)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        with self.lock:
            now = _utc_now()
            self.subscriptions = []
            self.notification_config = {
                "enabled": True,
                "to_email": "ops@example.com",
                "daily_digest_enabled": False,
                "daily_digest_hour_utc": None,
                "failure_alert_enabled": True,
                "created_at": now,
                "updated_at": now,
            }
            self.calls = {
                "http": [],
                "poll_ingest": [],
                "process_video": [],
                "upsert_subscription": [],
                "delete_subscription": [],
                "update_notification_config": [],
                "send_notification_test": [],
                "get_job": [],
                "get_artifact_markdown": [],
            }
            self.health_status = int(HTTPStatus.OK)

    def record(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.calls[key].append(payload)

    def call_count(self, key: str) -> int:
        with self.lock:
            return len(self.calls[key])

    def last_call(self, key: str) -> dict[str, Any]:
        with self.lock:
            return dict(self.calls[key][-1])

    def current_job(self) -> dict[str, Any]:
        now = _utc_now()
        return {
            "id": self.job_id,
            "video_id": "video-db-001",
            "kind": "video_digest_v1",
            "status": "succeeded",
            "idempotency_key": "idem-e2e",
            "error_message": None,
            "artifact_digest_md": "artifacts/digest.md",
            "artifact_root": "artifacts/job-e2e-001",
            "created_at": now,
            "updated_at": now,
            "step_summary": [
                {
                    "name": "fetch_transcript",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": now,
                    "finished_at": now,
                    "error": None,
                },
                {
                    "name": "generate_markdown",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": now,
                    "finished_at": now,
                    "error": None,
                },
            ],
            "steps": [],
            "degradations": [],
            "pipeline_final_status": "succeeded",
            "artifacts_index": {
                "digest_markdown": "artifacts/digest.md",
                "shots_zip": "artifacts/screenshots.zip",
            },
            "mode": "text_only",
        }

    def artifact_payload(self) -> dict[str, Any]:
        return {
            "markdown": "# Digest Summary\n\n- Key finding A\n- Key finding B\n",
            "meta": {
                "frame_files": ["screenshots/frame_0001.png", "screenshots/frame_0002.webp"],
                "job": {"id": self.job_id},
            },
        }


@dataclass(frozen=True)
class MockApiServer:
    base_url: str
    state: MockApiState


def _mock_handler(state: MockApiState) -> type[BaseHTTPRequestHandler]:
    class MockHandler(BaseHTTPRequestHandler):
        server_version = "MockVDAPI/1.0"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
            raw = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_binary(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_no_content(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _read_json(self) -> dict[str, Any]:
            raw_size = self.headers.get("Content-Length", "0")
            size = int(raw_size) if raw_size.isdigit() else 0
            if size <= 0:
                return {}
            raw = self.rfile.read(size).decode("utf-8")
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {}

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            state.record("http", {"method": "GET", "path": path, "query": parsed.query})

            if path == "/api/v1/subscriptions":
                with state.lock:
                    self._send_json(HTTPStatus.OK, state.subscriptions)
                return

            if path == "/healthz":
                status = HTTPStatus(state.health_status)
                self._send_json(status, {"status": "ok" if status == HTTPStatus.OK else "degraded"})
                return

            if path == "/api/v1/videos":
                now = _utc_now()
                videos = [
                    {
                        "id": "video-db-001",
                        "platform": "youtube",
                        "video_uid": "yt-e2e-001",
                        "source_url": "https://youtube.com/watch?v=e2e001",
                        "title": "E2E Demo",
                        "published_at": now,
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "status": "running",
                        "last_job_id": state.job_id,
                    }
                ]
                self._send_json(HTTPStatus.OK, videos)
                return

            if path.startswith("/api/v1/jobs/"):
                requested_job_id = path.rsplit("/", 1)[-1]
                state.record("get_job", {"job_id": requested_job_id})
                if requested_job_id != state.job_id:
                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "job not found"})
                    return
                self._send_json(HTTPStatus.OK, state.current_job())
                return

            if path == "/api/v1/artifacts/markdown":
                state.record(
                    "get_artifact_markdown",
                    {
                        "job_id": query.get("job_id", [""])[0],
                        "video_url": query.get("video_url", [""])[0],
                        "include_meta": query.get("include_meta", [""])[0],
                    },
                )
                include_meta = query.get("include_meta", ["false"])[0].lower() == "true"
                payload = state.artifact_payload()
                if include_meta:
                    self._send_json(HTTPStatus.OK, payload)
                    return
                self._send_text(HTTPStatus.OK, payload["markdown"], "text/markdown; charset=utf-8")
                return

            if path == "/api/v1/artifacts/assets":
                path_param = query.get("path", [""])[0].lower()
                if path_param.endswith(".webp"):
                    self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/webp")
                    return
                if path_param.endswith(".jpg") or path_param.endswith(".jpeg"):
                    self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/jpeg")
                    return
                self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/png")
                return

            if path == "/api/v1/notifications/config":
                with state.lock:
                    self._send_json(HTTPStatus.OK, state.notification_config)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled GET path: {path}"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            state.record("http", {"method": "POST", "path": path, "query": parsed.query})
            payload = self._read_json()

            if path == "/api/v1/ingest/poll":
                state.record("poll_ingest", payload)
                self._send_json(HTTPStatus.OK, {"enqueued": 2, "candidates": []})
                return

            if path == "/api/v1/videos/process":
                state.record("process_video", payload)
                response = {
                    "job_id": state.job_id,
                    "video_db_id": "video-db-001",
                    "video_uid": "yt-e2e-001",
                    "status": "queued",
                    "idempotency_key": "idem-e2e",
                    "mode": payload.get("mode", "full"),
                    "overrides": payload.get("overrides", {}),
                    "force": bool(payload.get("force", False)),
                    "reused": False,
                    "workflow_id": "wf-e2e-001",
                }
                self._send_json(HTTPStatus.OK, response)
                return

            if path == "/api/v1/subscriptions":
                state.record("upsert_subscription", payload)
                now = _utc_now()
                with state.lock:
                    new_id = f"sub-{len(state.subscriptions) + 1:03d}"
                    subscription = {
                        "id": new_id,
                        "platform": payload.get("platform", "youtube"),
                        "source_type": payload.get("source_type", "url"),
                        "source_value": payload.get("source_value", ""),
                        "rsshub_route": payload.get("rsshub_route") or "",
                        "enabled": bool(payload.get("enabled", False)),
                        "created_at": now,
                        "updated_at": now,
                    }
                    state.subscriptions.append(subscription)
                self._send_json(HTTPStatus.OK, {"subscription": subscription, "created": True})
                return

            if path == "/api/v1/notifications/test":
                state.record("send_notification_test", payload)
                now = _utc_now()
                to_email = payload.get("to_email") or "ops@example.com"
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "delivery_id": "delivery-e2e-001",
                        "status": "sent",
                        "provider_message_id": "provider-001",
                        "error_message": None,
                        "recipient_email": to_email,
                        "subject": payload.get("subject") or "Video Digestor test notification",
                        "sent_at": now,
                        "created_at": now,
                    },
                )
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled POST path: {path}"})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            state.record("http", {"method": "PUT", "path": path, "query": parsed.query})
            payload = self._read_json()

            if path == "/api/v1/notifications/config":
                state.record("update_notification_config", payload)
                now = _utc_now()
                with state.lock:
                    state.notification_config = {
                        "enabled": bool(payload.get("enabled", False)),
                        "to_email": payload.get("to_email"),
                        "daily_digest_enabled": bool(payload.get("daily_digest_enabled", False)),
                        "daily_digest_hour_utc": payload.get("daily_digest_hour_utc"),
                        "failure_alert_enabled": bool(payload.get("failure_alert_enabled", False)),
                        "created_at": state.notification_config.get("created_at", now),
                        "updated_at": now,
                    }
                    response = dict(state.notification_config)
                self._send_json(HTTPStatus.OK, response)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled PUT path: {path}"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            state.record("http", {"method": "DELETE", "path": path, "query": parsed.query})
            if path.startswith("/api/v1/subscriptions/"):
                subscription_id = path.rsplit("/", 1)[-1]
                state.record("delete_subscription", {"id": subscription_id})
                with state.lock:
                    state.subscriptions = [item for item in state.subscriptions if item["id"] != subscription_id]
                self._send_no_content()
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled DELETE path: {path}"})

    return MockHandler


@pytest.fixture(scope="session")
def mock_api_server() -> MockApiServer:
    port = _free_port()
    state = MockApiState()
    server = ThreadingHTTPServer(("127.0.0.1", port), _mock_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    _wait_http_ok(f"{base_url}/api/v1/subscriptions")
    try:
        yield MockApiServer(base_url=base_url, state=state)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def web_base_url(mock_api_server: MockApiServer) -> str:
    external_base_url = _external_web_base_url_from_env()
    if external_base_url is not None:
        _wait_http_ok(f"{external_base_url}/")
        yield external_base_url
        return

    if shutil.which("npm") is None:
        raise RuntimeError("npm is required for web E2E. Install Node.js/npm in CI before running tests.")
    if not (WEB_DIR / "node_modules").exists():
        raise RuntimeError("apps/web/node_modules is missing. Run `npm ci` in apps/web before E2E.")

    web_port = _free_port()
    base_url = f"http://127.0.0.1:{web_port}"
    env = os.environ.copy()
    env["NEXT_PUBLIC_API_BASE_URL"] = mock_api_server.base_url
    env["VD_API_BASE_URL"] = mock_api_server.base_url
    env["PORT"] = str(web_port)
    env["HOSTNAME"] = "127.0.0.1"
    env["CI"] = "1"

    output_lines: list[str] = []
    process = subprocess.Popen(
        ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", str(web_port)],
        cwd=WEB_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _capture_output() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            output_lines.append(line.rstrip())

    output_thread = threading.Thread(target=_capture_output, daemon=True)
    output_thread.start()

    try:
        _wait_http_ok(f"{base_url}/")
    except Exception as exc:
        process.terminate()
        process.wait(timeout=10)
        tail = "\n".join(output_lines[-60:])
        raise RuntimeError(f"Next.js web server failed to start.\n--- server output ---\n{tail}") from exc

    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        output_thread.join(timeout=2)


@pytest.fixture
def mock_api_state(mock_api_server: MockApiServer) -> MockApiState:
    mock_api_server.state.reset()
    return mock_api_server.state


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, web_base_url: str, request: pytest.FixtureRequest) -> Page:
    context = browser.new_context(
        base_url=web_base_url,
        record_video_dir=str(WEB_E2E_VIDEO_DIR),
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    page.set_default_timeout(20_000)
    yield page
    artifact_slug = _slugify_nodeid(request.node.nodeid)
    call_report = getattr(request.node, "rep_call", None)
    if call_report is not None and call_report.failed:
        page.screenshot(path=str(WEB_E2E_SCREENSHOT_DIR / f"{artifact_slug}.png"), full_page=True)
    context.tracing.stop(path=str(WEB_E2E_TRACE_DIR / f"{artifact_slug}.zip"))
    context.close()


def _wait_for_call_count(state: MockApiState, key: str, expected: int, timeout_sec: float = 5.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if state.call_count(key) >= expected:
            return
        time.sleep(0.05)
    raise AssertionError(
        f"Timed out waiting for `{key}` calls: expected >= {expected}, actual={state.call_count(key)}"
    )


def _wait_for_http_path(state: MockApiState, path: str, timeout_sec: float = 5.0) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with state.lock:
            if any(item.get("path") == path for item in state.calls["http"]):
                return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for HTTP path call: {path}")


def _wait_for_http_query_fragment(
    state: MockApiState,
    path: str,
    query_fragment: str,
    timeout_sec: float = 5.0,
) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with state.lock:
            if any(
                item.get("path") == path and query_fragment in item.get("query", "")
                for item in state.calls["http"]
            ):
                return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for HTTP query fragment: {path}?...{query_fragment}")


def _seed_subscription(state: MockApiState, subscription_id: str, source_value: str) -> None:
    now = _utc_now()
    with state.lock:
        state.subscriptions = [
            {
                "id": subscription_id,
                "platform": "youtube",
                "source_type": "url",
                "source_value": source_value,
                "rsshub_route": "/youtube/channel/seeded",
                "enabled": True,
                "created_at": now,
                "updated_at": now,
            }
        ]


def test_external_web_base_url_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    assert _external_web_base_url_from_env() is None

    monkeypatch.setenv("WEB_BASE_URL", "  http://127.0.0.1:3300/  ")
    assert _external_web_base_url_from_env() == "http://127.0.0.1:3300"

    monkeypatch.setenv("WEB_BASE_URL", "not-a-url")
    with pytest.raises(RuntimeError, match="absolute http\\(s\\) URL"):
        _external_web_base_url_from_env()


def test_dashboard_trigger_ingest_poll_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Poll ingest")).to_be_visible()
    expect(page.get_by_text("API health: Healthy")).to_be_visible()
    page.get_by_role("button", name="Trigger ingest poll").click()

    _wait_for_call_count(mock_api_state, "poll_ingest", 1)
    payload = mock_api_state.last_call("poll_ingest")
    assert payload.get("max_new_videos") == 50
    assert page.url.startswith("http://127.0.0.1:")


def test_dashboard_health_chip_degraded_state(page: Page, mock_api_state: MockApiState) -> None:
    mock_api_state.health_status = int(HTTPStatus.SERVICE_UNAVAILABLE)
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_text("API health: Degraded")).to_be_visible()


def test_dashboard_start_processing_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/", wait_until="domcontentloaded")
    start_button = page.get_by_role("button", name="Start processing")
    expect(start_button).to_be_disabled()
    page.get_by_label("Video URL").fill("https://www.youtube.com/watch?v=e2e001")
    expect(start_button).to_be_enabled()
    page.get_by_label("Mode").select_option("text_only")
    page.get_by_role("checkbox", name="Force run").check()
    start_button.click()

    _wait_for_call_count(mock_api_state, "process_video", 1)
    process_payload = mock_api_state.last_call("process_video")
    assert process_payload["video"]["url"] == "https://www.youtube.com/watch?v=e2e001"
    assert process_payload["mode"] == "text_only"
    assert process_payload["force"] is True
    assert page.url.startswith("http://127.0.0.1:")


def test_subscriptions_save_subscription_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/subscriptions", wait_until="domcontentloaded")
    page.get_by_label("Source value").fill("https://youtube.com/@vd-e2e")
    page.get_by_label("RSSHub route (optional)").fill("/youtube/channel/vd-e2e")
    page.get_by_role("button", name="Save subscription").click()

    _wait_for_call_count(mock_api_state, "upsert_subscription", 1)
    upsert_payload = mock_api_state.last_call("upsert_subscription")
    assert upsert_payload["source_value"] == "https://youtube.com/@vd-e2e"
    assert upsert_payload["rsshub_route"] == "/youtube/channel/vd-e2e"
    assert upsert_payload["enabled"] is True
    created_row = page.locator("tbody tr", has_text="https://youtube.com/@vd-e2e")
    expect(created_row).to_be_visible()


def test_subscriptions_delete_button(page: Page, mock_api_state: MockApiState) -> None:
    seeded_source = "https://youtube.com/@vd-delete"
    seeded_id = "sub-seeded-001"
    _seed_subscription(mock_api_state, seeded_id, seeded_source)

    page.goto("/subscriptions", wait_until="domcontentloaded")
    row = page.locator("tbody tr", has_text=seeded_source)
    expect(row).to_be_visible()
    row.get_by_role("button", name="Delete").click()

    _wait_for_call_count(mock_api_state, "delete_subscription", 1)
    delete_payload = mock_api_state.last_call("delete_subscription")
    assert delete_payload["id"] == seeded_id
    expect(page.locator("tbody tr", has_text=seeded_source)).to_have_count(0)


def test_settings_save_config_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    digest_hour = page.get_by_label("Daily digest hour (UTC)")
    expect(digest_hour).to_be_disabled()
    page.get_by_label("Recipient email").fill("ops-e2e@example.com")
    page.get_by_label("Enable daily digest").check()
    expect(digest_hour).to_be_enabled()
    page.get_by_label("Daily digest hour (UTC)").fill("7")
    page.get_by_role("button", name="Save config").click()

    _wait_for_call_count(mock_api_state, "update_notification_config", 1)
    update_payload = mock_api_state.last_call("update_notification_config")
    assert update_payload["to_email"] == "ops-e2e@example.com"
    assert update_payload["daily_digest_enabled"] is True
    assert update_payload["daily_digest_hour_utc"] == 7
    assert page.url.startswith("http://127.0.0.1:")


def test_settings_send_test_email_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    page.get_by_label("Override recipient (optional)").fill("qa-e2e@example.com")
    page.get_by_label("Subject (optional)").fill("E2E notification check")
    page.get_by_label("Body (optional)").fill("this is an automated e2e notification test")
    page.get_by_role("button", name="Send test email").click()

    _wait_for_call_count(mock_api_state, "send_notification_test", 1)
    notify_payload = mock_api_state.last_call("send_notification_test")
    assert notify_payload["to_email"] == "qa-e2e@example.com"
    assert notify_payload["subject"] == "E2E notification check"
    assert notify_payload["body"] == "this is an automated e2e notification test"


def test_jobs_to_artifacts_query_navigation(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/jobs", wait_until="domcontentloaded")
    page.get_by_label("Job ID").fill(mock_api_state.job_id)
    page.get_by_role("button", name="Fetch job").click()

    expect(page).to_have_url(re.compile(r"/jobs\?job_id=job-e2e-001"))
    expect(page.get_by_role("heading", name="Job lookup")).to_be_visible()

    page.goto("/artifacts", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Artifact lookup")).to_be_visible()
    page.get_by_label("Job ID").fill(mock_api_state.job_id)
    page.get_by_role("button", name="Load artifacts").click()

    _wait_for_call_count(mock_api_state, "get_artifact_markdown", 1)
    _wait_for_http_path(mock_api_state, "/api/v1/artifacts/assets")
    _wait_for_http_query_fragment(mock_api_state, "/api/v1/artifacts/assets", "path=screenshots%2Fframe_0001.png")
    _wait_for_http_query_fragment(mock_api_state, "/api/v1/artifacts/assets", "path=screenshots%2Fframe_0002.webp")
    artifact_payload = mock_api_state.last_call("get_artifact_markdown")
    assert artifact_payload["job_id"] == mock_api_state.job_id
    assert artifact_payload["include_meta"] == "true"

    expect(page).to_have_url(re.compile(r"/artifacts\?job_id=job-e2e-001"))
    expect(page.get_by_role("heading", name="Artifact lookup")).to_be_visible()
    expect(page.get_by_role("heading", name="Embedded screenshots")).to_be_visible()
    expect(page.get_by_role("heading", name="Screenshot index (fallback)")).to_be_visible()
    screenshot_index = page.locator(
        "section",
        has=page.get_by_role("heading", name="Screenshot index (fallback)"),
    )
    expect(screenshot_index.locator("code", has_text="screenshots/frame_0001.png")).to_be_visible()
    expect(screenshot_index.locator("code", has_text="screenshots/frame_0002.webp")).to_be_visible()
    expect(page.get_by_role("heading", name="Markdown preview")).to_be_visible()
    expect(page.get_by_text("Key finding A")).to_be_visible()


def test_artifacts_lookup_form_requires_single_field(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    submit = page.get_by_role("button", name="Load artifacts")

    expect(submit).to_be_disabled()
    page.get_by_label("Job ID").fill("job-e2e-001")
    expect(submit).to_be_enabled()
    page.get_by_label("Video URL").fill("https://www.youtube.com/watch?v=e2e001")
    expect(submit).to_be_disabled()
