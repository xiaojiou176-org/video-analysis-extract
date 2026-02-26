#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="external_playwright_smoke"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

url="${EXTERNAL_SMOKE_URL:-https://example.com}"
browser="${EXTERNAL_SMOKE_BROWSER:-chromium}"
timeout_ms="${EXTERNAL_SMOKE_TIMEOUT_MS:-45000}"
expect_text="${EXTERNAL_SMOKE_EXPECT_TEXT:-Example Domain}"
output_dir="${EXTERNAL_SMOKE_OUTPUT_DIR:-.runtime-cache/external-playwright-smoke}"
retries="${EXTERNAL_SMOKE_RETRIES:-2}"
diagnostics_json="${EXTERNAL_SMOKE_DIAGNOSTICS_JSON:-.runtime-cache/external-playwright-smoke-result.json}"
heartbeat_seconds="${EXTERNAL_SMOKE_HEARTBEAT_SECONDS:-30}"

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/external_playwright_smoke.sh [options]

Options:
  --url <url>               External target URL (default: https://example.com)
  --browser <name>          Browser engine: chromium|firefox|webkit (default: chromium)
  --timeout-ms <ms>         Navigation/assert timeout in ms (default: 45000)
  --expect-text <text>      Expected body text marker (default: Example Domain)
  --output-dir <path>       Artifact output directory (default: .runtime-cache/external-playwright-smoke)
  --diagnostics-json <path> Structured diagnostics JSON output path
  --retries <n>             Number of attempts (default: 2)
  --heartbeat-seconds <n>   Heartbeat interval in seconds (default: 30)
  -h, --help                Show this help

Environment defaults (used when corresponding option is omitted):
  EXTERNAL_SMOKE_URL, EXTERNAL_SMOKE_BROWSER, EXTERNAL_SMOKE_TIMEOUT_MS,
  EXTERNAL_SMOKE_EXPECT_TEXT, EXTERNAL_SMOKE_OUTPUT_DIR, EXTERNAL_SMOKE_RETRIES
  EXTERNAL_SMOKE_DIAGNOSTICS_JSON, EXTERNAL_SMOKE_HEARTBEAT_SECONDS
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

export EXTERNAL_SMOKE_URL="$url"
export EXTERNAL_SMOKE_BROWSER="$browser"
export EXTERNAL_SMOKE_TIMEOUT_MS="$timeout_ms"
export EXTERNAL_SMOKE_EXPECT_TEXT="$expect_text"
export EXTERNAL_SMOKE_OUTPUT_DIR="$output_dir"
export EXTERNAL_SMOKE_RETRIES="$retries"
export EXTERNAL_SMOKE_DIAGNOSTICS_JSON="$diagnostics_json"
export EXTERNAL_SMOKE_HEARTBEAT_SECONDS="$heartbeat_seconds"

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

log "Running external Playwright smoke: browser=$browser url=$url timeout_ms=$timeout_ms retries=$retries heartbeat_seconds=$heartbeat_seconds"
log "Python runner source: $python_source"

"${python_cmd[@]}" - <<'PY'
from __future__ import annotations

import json
import os
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    return SmokeConfig(
        url=os.environ["EXTERNAL_SMOKE_URL"],
        browser=os.environ["EXTERNAL_SMOKE_BROWSER"],
        timeout_ms=int(os.environ["EXTERNAL_SMOKE_TIMEOUT_MS"]),
        expect_text=os.environ["EXTERNAL_SMOKE_EXPECT_TEXT"],
        output_dir=Path(os.environ["EXTERNAL_SMOKE_OUTPUT_DIR"]),
        retries=int(os.environ["EXTERNAL_SMOKE_RETRIES"]),
        diagnostics_json=Path(os.environ["EXTERNAL_SMOKE_DIAGNOSTICS_JSON"]),
        heartbeat_seconds=int(os.environ["EXTERNAL_SMOKE_HEARTBEAT_SECONDS"]),
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
            config.diagnostics_json.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
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
    config.diagnostics_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
PY
