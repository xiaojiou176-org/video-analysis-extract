from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from support.mock_api import MockApiServer, MockApiState, start_mock_api_server, stop_mock_api_server
from support.runtime_utils import external_web_base_url_from_env, free_port, slugify_nodeid, wait_http_ok

PROJECT_ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = PROJECT_ROOT / "apps" / "web"
WEB_E2E_ARTIFACT_ROOT = PROJECT_ROOT / ".runtime-cache" / "web-e2e-artifacts"
WEB_E2E_VIDEO_DIR = WEB_E2E_ARTIFACT_ROOT / "videos"
WEB_E2E_TRACE_DIR = WEB_E2E_ARTIFACT_ROOT / "traces"
WEB_E2E_SCREENSHOT_DIR = WEB_E2E_ARTIFACT_ROOT / "screenshots"

for artifact_dir in (WEB_E2E_VIDEO_DIR, WEB_E2E_TRACE_DIR, WEB_E2E_SCREENSHOT_DIR):
    artifact_dir.mkdir(parents=True, exist_ok=True)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(scope="session")
def mock_api_server() -> MockApiServer:
    running = start_mock_api_server()
    try:
        yield running.api_server
    finally:
        stop_mock_api_server(running)


@pytest.fixture(scope="session")
def web_base_url(mock_api_server: MockApiServer) -> str:
    external_base_url = external_web_base_url_from_env()
    if external_base_url is not None:
        wait_http_ok(f"{external_base_url}/")
        yield external_base_url
        return

    if shutil.which("npm") is None:
        raise RuntimeError("npm is required for web E2E. Install Node.js/npm in CI before running tests.")
    if not (WEB_DIR / "node_modules").exists():
        raise RuntimeError("apps/web/node_modules is missing. Run `npm ci` in apps/web before E2E.")

    web_port = free_port()
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
        wait_http_ok(f"{base_url}/")
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
    artifact_slug = slugify_nodeid(request.node.nodeid)
    call_report = getattr(request.node, "rep_call", None)
    if call_report is not None and call_report.failed:
        page.screenshot(path=str(WEB_E2E_SCREENSHOT_DIR / f"{artifact_slug}.png"), full_page=True)
    context.tracing.stop(path=str(WEB_E2E_TRACE_DIR / f"{artifact_slug}.zip"))
    context.close()
