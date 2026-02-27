from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright
from support.mock_api import (
    MockApiServer,
    MockApiState,
    start_mock_api_server,
    stop_mock_api_server,
)
from support.runtime_utils import (
    external_web_base_url_from_env,
    slugify_nodeid,
    wait_http_ok,
    with_free_port_retry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
WEB_DIR = PROJECT_ROOT / "apps" / "web"
WEB_E2E_ARTIFACT_ROOT = PROJECT_ROOT / ".runtime-cache" / "web-e2e-artifacts"
WEB_E2E_VIDEO_DIR = WEB_E2E_ARTIFACT_ROOT / "videos"
WEB_E2E_TRACE_DIR = WEB_E2E_ARTIFACT_ROOT / "traces"
WEB_E2E_SCREENSHOT_DIR = WEB_E2E_ARTIFACT_ROOT / "screenshots"

for artifact_dir in (WEB_E2E_VIDEO_DIR, WEB_E2E_TRACE_DIR, WEB_E2E_SCREENSHOT_DIR):
    artifact_dir.mkdir(parents=True, exist_ok=True)


class _PortInUseStartupError(RuntimeError):
    pass


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--web-e2e-browser",
        action="store",
        default="chromium",
        help="Playwright browser for web e2e: chromium|firefox|webkit",
    )
    parser.addoption(
        "--web-e2e-trace-mode",
        action="store",
        default="off",
        help="Playwright tracing mode: off|on|retain-on-failure",
    )
    parser.addoption(
        "--web-e2e-video-mode",
        action="store",
        default="retain-on-failure",
        help="Playwright video mode: off|on|retain-on-failure",
    )
    parser.addoption(
        "--web-e2e-worker-id",
        action="store",
        default="gw0",
        help="Worker id suffix for isolated Next.js dist dir",
    )


def _read_trace_mode(config: pytest.Config) -> str:
    mode = str(config.getoption("--web-e2e-trace-mode")).strip().lower()
    allowed = {"off", "on", "retain-on-failure"}
    if mode not in allowed:
        raise RuntimeError(
            f"unsupported --web-e2e-trace-mode={mode!r}; expected one of {sorted(allowed)}"
        )
    return mode


def _read_video_mode(config: pytest.Config) -> str:
    mode = str(config.getoption("--web-e2e-video-mode")).strip().lower()
    allowed = {"off", "on", "retain-on-failure"}
    if mode not in allowed:
        raise RuntimeError(
            f"unsupported --web-e2e-video-mode={mode!r}; expected one of {sorted(allowed)}"
        )
    return mode


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
def web_base_url(mock_api_server: MockApiServer, pytestconfig: pytest.Config) -> str:
    external_base_url = external_web_base_url_from_env()
    if external_base_url is not None:
        wait_http_ok(f"{external_base_url}/")
        yield external_base_url
        return

    if shutil.which("npm") is None:
        raise RuntimeError("npm is required for web E2E. Install Node.js/npm in CI before running tests.")
    if not (WEB_DIR / "node_modules").exists():
        raise RuntimeError("apps/web/node_modules is missing. Run `npm ci` in apps/web before E2E.")

    worker_id = str(pytestconfig.getoption("--web-e2e-worker-id"))
    worker_slug = "".join(ch if ch.isalnum() else "-" for ch in worker_id.lower())

    process: subprocess.Popen[str] | None = None
    output_thread: threading.Thread | None = None
    output_lines: list[str] = []

    def _start_web_server_on_port(web_port: int) -> tuple[subprocess.Popen[str], threading.Thread, list[str]]:
        nonlocal output_lines
        output_lines = []
        base_url = f"http://127.0.0.1:{web_port}"
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_BASE_URL"] = mock_api_server.base_url
        env["NEXT_DIST_DIR"] = f".next-e2e-{worker_slug}"
        env["PORT"] = str(web_port)
        env["HOSTNAME"] = "127.0.0.1"
        env["CI"] = "1"

        local_process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", str(web_port)],
            cwd=WEB_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _capture_output() -> None:
            if local_process.stdout is None:
                return
            for line in local_process.stdout:
                output_lines.append(line.rstrip())

        local_output_thread = threading.Thread(target=_capture_output, daemon=True)
        local_output_thread.start()

        try:
            wait_http_ok(f"{base_url}/")
            return local_process, local_output_thread, output_lines
        except Exception as exc:
            local_process.terminate()
            local_process.wait(timeout=10)
            local_output_thread.join(timeout=2)
            tail = "\n".join(output_lines[-60:])
            message = f"Next.js web server failed to start on port {web_port}.\n--- server output ---\n{tail}"
            if "EADDRINUSE" in tail:
                raise _PortInUseStartupError(message) from exc
            raise RuntimeError(message) from exc

    (process, output_thread, output_lines), web_port = with_free_port_retry(
        _start_web_server_on_port,
        attempts=4,
        retry_if=lambda exc: isinstance(exc, _PortInUseStartupError),
    )
    base_url = f"http://127.0.0.1:{web_port}"

    try:
        yield base_url
    finally:
        assert process is not None
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        assert output_thread is not None
        output_thread.join(timeout=2)


@pytest.fixture
def mock_api_state(mock_api_server: MockApiServer) -> MockApiState:
    mock_api_server.state.reset()
    return mock_api_server.state


@pytest.fixture(scope="session")
def browser(pytestconfig: pytest.Config) -> Browser:
    browser_name = str(pytestconfig.getoption("--web-e2e-browser")).strip().lower()
    launchers = {"chromium", "firefox", "webkit"}
    if browser_name not in launchers:
        raise RuntimeError(
            f"unsupported --web-e2e-browser={browser_name!r}; expected one of {sorted(launchers)}"
        )
    with sync_playwright() as playwright:
        browser = getattr(playwright, browser_name).launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser, web_base_url: str, request: pytest.FixtureRequest) -> Page:
    artifact_slug = slugify_nodeid(request.node.nodeid)
    trace_mode = _read_trace_mode(request.config)
    video_mode = _read_video_mode(request.config)

    new_context_kwargs: dict[str, str] = {"base_url": web_base_url}
    video_test_dir = WEB_E2E_VIDEO_DIR / artifact_slug
    if video_mode != "off":
        video_test_dir.mkdir(parents=True, exist_ok=True)
        new_context_kwargs["record_video_dir"] = str(video_test_dir)

    context = browser.new_context(**new_context_kwargs)
    if trace_mode != "off":
        context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    page.set_default_timeout(20_000)
    yield page
    call_report = getattr(request.node, "rep_call", None)
    failed = call_report is not None and call_report.failed
    if failed:
        page.screenshot(path=str(WEB_E2E_SCREENSHOT_DIR / f"{artifact_slug}.png"), full_page=True)

    if trace_mode == "on":
        context.tracing.stop(path=str(WEB_E2E_TRACE_DIR / f"{artifact_slug}.zip"))
    elif trace_mode == "retain-on-failure":
        if failed:
            context.tracing.stop(path=str(WEB_E2E_TRACE_DIR / f"{artifact_slug}.zip"))
        else:
            context.tracing.stop()

    video_obj = page.video
    context.close()
    if video_mode == "retain-on-failure":
        kept_video_path: Path | None = None
        if video_obj is not None:
            try:
                kept_video_path = Path(video_obj.path())
            except Exception:
                kept_video_path = None

        if failed and kept_video_path is not None and kept_video_path.exists():
            target_path = WEB_E2E_VIDEO_DIR / f"{artifact_slug}{kept_video_path.suffix or '.webm'}"
            if target_path.exists():
                target_path.unlink()
            kept_video_path.replace(target_path)

        shutil.rmtree(video_test_dir, ignore_errors=True)
