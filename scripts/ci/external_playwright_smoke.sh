#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="external_playwright_smoke"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# shellcheck source=./scripts/runtime/logging.sh
source "$ROOT_DIR/scripts/runtime/logging.sh"
vd_log_init "tests" "$SCRIPT_NAME" "$ROOT_DIR/.runtime-cache/logs/tests/external-playwright-smoke.jsonl"

url="https://example.com"
browser="chromium"
timeout_ms="45000"
expect_text="Example Domain"
output_dir=".runtime-cache/evidence/tests/external-playwright-smoke"
retries="2"
diagnostics_json=".runtime-cache/reports/tests/external-playwright-smoke-result.json"
heartbeat_seconds="30"

log() {
  vd_log info external_playwright_smoke "$*"
}

fail() {
  vd_log error external_playwright_smoke_error "$*"
  exit 1
}

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/ci/external_playwright_smoke.sh [options]

Options:
  --url <url>               External target URL (default: https://example.com)
  --browser <name>          Browser engine: chromium|firefox|webkit (default: chromium)
  --timeout-ms <ms>         Navigation/assert timeout in ms (default: 45000)
  --expect-text <text>      Expected body text marker (default: Example Domain)
  --output-dir <path>       Artifact output directory (default: .runtime-cache/evidence/tests/external-playwright-smoke)
  --diagnostics-json <path> Structured diagnostics JSON output path
  --retries <n>             Number of attempts (default: 2)
  --heartbeat-seconds <n>   Heartbeat interval in seconds (default: 30)
  -h, --help                Show this help

Defaults are internal constants in this script. Use CLI options to override.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      url="${2:-}"
      shift 2
      ;;
    --browser)
      browser="${2:-}"
      shift 2
      ;;
    --timeout-ms)
      timeout_ms="${2:-}"
      shift 2
      ;;
    --expect-text)
      expect_text="${2:-}"
      shift 2
      ;;
    --output-dir)
      output_dir="${2:-}"
      shift 2
      ;;
    --retries)
      retries="${2:-}"
      shift 2
      ;;
    --diagnostics-json)
      diagnostics_json="${2:-}"
      shift 2
      ;;
    --heartbeat-seconds)
      heartbeat_seconds="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -n "$url" ]] || fail "--url cannot be empty"
[[ -n "$expect_text" ]] || fail "--expect-text cannot be empty"
[[ "$browser" == "chromium" || "$browser" == "firefox" || "$browser" == "webkit" ]] || fail "--browser must be one of: chromium|firefox|webkit"
[[ "$timeout_ms" =~ ^[0-9]+$ ]] || fail "--timeout-ms must be a positive integer"
[[ "$retries" =~ ^[0-9]+$ ]] || fail "--retries must be a positive integer"
[[ "$heartbeat_seconds" =~ ^[0-9]+$ ]] || fail "--heartbeat-seconds must be a positive integer"
(( timeout_ms > 0 )) || fail "--timeout-ms must be > 0"
(( retries > 0 )) || fail "--retries must be > 0"
(( retries <= 2 )) || fail "--retries must be <= 2 for live smoke policy"
(( heartbeat_seconds > 0 )) || fail "--heartbeat-seconds must be > 0"

command -v python3 >/dev/null 2>&1 || fail "python3 is required"

if [[ "${output_dir:0:1}" != "/" ]]; then
  output_dir="$ROOT_DIR/$output_dir"
fi
mkdir -p "$output_dir"
if [[ "${diagnostics_json:0:1}" != "/" ]]; then
  diagnostics_json="$ROOT_DIR/$diagnostics_json"
fi
mkdir -p "$(dirname "$diagnostics_json")"

python_cmd=(python3)
python_source="system_python3"
if ! python3 -c 'import playwright' >/dev/null 2>&1; then
  if command -v uv >/dev/null 2>&1; then
    python_cmd=(uv run --with playwright python3)
    python_source="uv_with_playwright"
  else
    fail "python3 missing playwright and uv is not available; run: uv sync --frozen --extra e2e"
  fi
fi
export EXTERNAL_SMOKE_PYTHON_SOURCE="$python_source"
export EXTERNAL_SMOKE_REPO_ROOT="$ROOT_DIR"
export EXTERNAL_SMOKE_RUN_ID="${vd_log_run_id:-external-playwright-smoke}"

log "Running external Playwright smoke: browser=$browser url=$url timeout_ms=$timeout_ms retries=$retries heartbeat_seconds=$heartbeat_seconds"
log "Python runner source: $python_source"

"${python_cmd[@]}" - \
  "$url" \
  "$browser" \
  "$timeout_ms" \
  "$expect_text" \
  "$output_dir" \
  "$retries" \
  "$diagnostics_json" \
  "$heartbeat_seconds" <<'PY'
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

root = Path(os.environ["EXTERNAL_SMOKE_REPO_ROOT"])
if str(root / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(root / "scripts" / "governance"))

from common import write_json_artifact

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class SmokeConfig:
    url: str
    browser: str
    timeout_ms: int
    expect_text: str
    output_dir: Path
    retries: int
    diagnostics_json: Path
    heartbeat_seconds: int

def _build_config() -> SmokeConfig:
    if len(sys.argv) != 9:
        raise RuntimeError("invalid invocation: expected 8 args")
    return SmokeConfig(
        url=sys.argv[1],
        browser=sys.argv[2],
        timeout_ms=int(sys.argv[3]),
        expect_text=sys.argv[4],
        output_dir=Path(sys.argv[5]),
        retries=int(sys.argv[6]),
        diagnostics_json=Path(sys.argv[7]),
        heartbeat_seconds=int(sys.argv[8]),
    )


def _attempt(config: SmokeConfig, attempt: int) -> dict[str, Any]:
    screenshot_path = config.output_dir / f"attempt-{attempt}.png"
    html_path = config.output_dir / f"attempt-{attempt}.html"
    diagnostics: dict[str, Any] = {
        "attempt": attempt,
        "url": config.url,
        "browser": config.browser,
        "timeout_ms": config.timeout_ms,
        "expect_text": config.expect_text,
        "screenshot": str(screenshot_path),
        "html": str(html_path),
    }

    stop_heartbeat = threading.Event()

    def _heartbeat() -> None:
        while not stop_heartbeat.wait(config.heartbeat_seconds):
            print(
                f"[external_playwright_smoke] heartbeat: attempt={attempt} url={config.url} browser={config.browser}",
                flush=True,
            )

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat_thread.start()

    with sync_playwright() as p:
        browser_launcher = getattr(p, config.browser)
        browser = browser_launcher.launch(headless=True)
        page = None
        try:
            context = browser.new_context(ignore_https_errors=False)
            page = context.new_page()

            console_errors: list[str] = []
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text)
                if msg.type == "error" and len(console_errors) < 20
                else None,
            )

            response = page.goto(config.url, wait_until="domcontentloaded", timeout=config.timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(config.timeout_ms, 15_000))
            except PlaywrightTimeoutError:
                # Network idle is best effort on external sites.
                pass

            title = page.title()
            current_url = page.url
            status = response.status if response is not None else None
            response_ok = bool(response and response.ok)
            body_text = page.inner_text("body", timeout=min(config.timeout_ms, 10_000))
            body_preview = body_text[:400]

            page.screenshot(path=str(screenshot_path), full_page=True)
            html_path.write_text(page.content(), encoding="utf-8")

            diagnostics.update(
                {
                    "http_status": status,
                    "response_ok": response_ok,
                    "title": title,
                    "current_url": current_url,
                    "body_preview": body_preview,
                    "console_errors": console_errors,
                }
            )

            if status is None:
                raise AssertionError("navigation returned no HTTP response")
            if status >= 400:
                raise AssertionError(f"unexpected HTTP status: {status}")
            if config.expect_text not in body_text:
                raise AssertionError(
                    f"expected marker not found in body text: {config.expect_text!r}"
                )

            diagnostics["result"] = "passed"
            return diagnostics
        except Exception as exc:  # noqa: BLE001
            diagnostics["result"] = "failed"
            diagnostics["error"] = f"{type(exc).__name__}: {exc}"
            diagnostics["traceback"] = traceback.format_exc(limit=10)
            error_name = type(exc).__name__
            if isinstance(exc, PlaywrightTimeoutError):
                diagnostics["failure_kind"] = "network_or_environment_timeout"
            elif isinstance(exc, PlaywrightError):
                diagnostics["failure_kind"] = "network_or_environment_timeout"
            elif isinstance(exc, AssertionError):
                diagnostics["failure_kind"] = "code_logic_error"
            else:
                diagnostics["failure_kind"] = "code_logic_error"
            diagnostics["error_name"] = error_name
            if page is not None:
                try:
                    page.screenshot(path=str(screenshot_path), full_page=True)
                except PlaywrightError:
                    diagnostics["screenshot_error"] = "failed to write screenshot"
                try:
                    html_path.write_text(page.content(), encoding="utf-8")
                except PlaywrightError:
                    diagnostics["html_error"] = "failed to write html snapshot"
            return diagnostics
        finally:
            browser.close()
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=1.0)


def main() -> int:
    config = _build_config()
    config.output_dir.mkdir(parents=True, exist_ok=True)

    all_attempts: list[dict[str, Any]] = []
    for attempt in range(1, config.retries + 1):
        attempt_result = _attempt(config, attempt)
        all_attempts.append(attempt_result)

        if attempt_result.get("result") == "passed":
            summary = {
                "status": "passed",
                "url": config.url,
                "browser": config.browser,
                "python_source": os.environ.get("EXTERNAL_SMOKE_PYTHON_SOURCE", "unknown"),
                "retry_policy": {"max_attempts": 2, "configured_attempts": config.retries},
                "attempt": attempt,
                "http_status": attempt_result.get("http_status"),
                "title": attempt_result.get("title"),
                "artifacts": {
                    "screenshot": attempt_result.get("screenshot"),
                    "html": attempt_result.get("html"),
                },
            }
            write_json_artifact(
                config.diagnostics_json,
                summary,
                source_entrypoint="scripts/ci/external_playwright_smoke.sh",
                verification_scope="tests:external-playwright-smoke",
                source_run_id=os.environ.get("EXTERNAL_SMOKE_RUN_ID", "external-playwright-smoke"),
                freshness_window_hours=24,
                extra={"report_kind": "external-playwright-smoke-result"},
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

    summary = {
        "status": "failed",
        "failure_kind": "network_or_environment_timeout"
        if any(a.get("failure_kind") == "network_or_environment_timeout" for a in all_attempts)
        else "code_logic_error",
        "url": config.url,
        "browser": config.browser,
        "python_source": os.environ.get("EXTERNAL_SMOKE_PYTHON_SOURCE", "unknown"),
        "expect_text": config.expect_text,
        "retries": config.retries,
        "retry_policy": {"max_attempts": 2, "configured_attempts": config.retries},
        "attempts": all_attempts,
    }
    write_json_artifact(
        config.diagnostics_json,
        summary,
        source_entrypoint="scripts/ci/external_playwright_smoke.sh",
        verification_scope="tests:external-playwright-smoke",
        source_run_id=os.environ.get("EXTERNAL_SMOKE_RUN_ID", "external-playwright-smoke"),
        freshness_window_hours=24,
        extra={"report_kind": "external-playwright-smoke-result"},
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
PY
