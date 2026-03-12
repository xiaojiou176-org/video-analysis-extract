#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="ci_web_e2e"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROWSER="${1:-chromium}"
DATABASE_URL="${DATABASE_URL:-}"
WEB_E2E_DB_NAME="video_analysis_web_e2e"
WEB_E2E_DB_PORT="${WEB_E2E_DB_PORT:-5432}"
TEMPORAL_CLI_VERSION="${TEMPORAL_CLI_VERSION:-1.5.1}"
TEMPORAL_CLI_SHA256_LINUX_AMD64="${TEMPORAL_CLI_SHA256_LINUX_AMD64:-ddc95e08b0b076efd4ea9733a3f488eb7d2be875f8834e616cd2a37358b4852d}"
TEMPORAL_CLI_SHA256_LINUX_ARM64="${TEMPORAL_CLI_SHA256_LINUX_ARM64:-bd1b0db9f18b051026de8bf6cc1505f2510f14bbb7a8b9a4a91fff46c77454f5}"

API_PID=""
WORKER_PID=""
TEMPORAL_PID=""
TEMPORAL_TMPDIR=""
WEB_E2E_API_PORT=""
WEB_E2E_TEMPORAL_PORT=""
WEB_E2E_SQLITE_STATE_PATH=""
WEB_E2E_SQLITE_PATH=""
WEB_E2E_WORKSPACE_DIR=""
WEB_E2E_ARTIFACT_ROOT=""

usage() {
  cat <<'EOF'
Usage: ./scripts/ci_web_e2e.sh [chromium|firefox|webkit]
EOF
}

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

ensure_node_toolchain() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    return 0
  fi
  fail "node/npm are unavailable inside standard env"
}

port_is_listening() {
  local port="$1"
  python3 - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    result = sock.connect_ex(("127.0.0.1", port))
raise SystemExit(0 if result == 0 else 1)
PY
}

choose_available_port() {
  python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

wait_for_tcp() {
  local port="$1"
  local label="$2"
  local attempts="${3:-60}"
  for _ in $(seq 1 "$attempts"); do
    if port_is_listening "$port"; then
      log "${label} ready on 127.0.0.1:${port}"
      return 0
    fi
    sleep 1
  done
  fail "${label} failed to become ready on 127.0.0.1:${port}"
}

wait_for_http_ok() {
  local url="$1"
  local label="$2"
  local attempts="${3:-120}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "${label} ready: ${url}"
      return 0
    fi
    sleep 1
  done
  fail "${label} health check failed: ${url}"
}

temporal_task_queue_has_worker_pollers() {
  TEMPORAL_TARGET_HOST="127.0.0.1:${WEB_E2E_TEMPORAL_PORT}" \
  TEMPORAL_NAMESPACE="default" \
  TEMPORAL_TASK_QUEUE="video-analysis-worker" \
    uv run python - <<'PY' >/dev/null 2>&1
import asyncio
import os

from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client


async def main() -> int:
    client = await Client.connect(
        os.environ["TEMPORAL_TARGET_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
    )
    task_queue = TaskQueue(name=os.environ["TEMPORAL_TASK_QUEUE"])
    for task_queue_type in (
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ):
        response = await client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(
                namespace=os.environ["TEMPORAL_NAMESPACE"],
                task_queue=task_queue,
                task_queue_type=task_queue_type,
            )
        )
        if len(response.pollers) == 0:
            return 1
    return 0


raise SystemExit(asyncio.run(main()))
PY
}

install_temporal_cli() {
  if command -v temporal >/dev/null 2>&1; then
    return 0
  fi
  require_command curl
  require_command tar
  require_command sha256sum

  local arch expected_sha temporal_arch archive archive_path url
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64)
      temporal_arch="amd64"
      expected_sha="$TEMPORAL_CLI_SHA256_LINUX_AMD64"
      ;;
    aarch64|arm64)
      temporal_arch="arm64"
      expected_sha="$TEMPORAL_CLI_SHA256_LINUX_ARM64"
      ;;
    *)
      fail "unsupported architecture for Temporal CLI: ${arch}"
      ;;
  esac
  [[ -n "$expected_sha" ]] || fail "missing Temporal CLI sha256 for architecture ${temporal_arch}"

  TEMPORAL_TMPDIR="$(mktemp -d "/tmp/temporal-cli-web-e2e-${BROWSER}-XXXXXX")"
  archive="temporal_cli_${TEMPORAL_CLI_VERSION}_linux_${temporal_arch}.tar.gz"
  archive_path="${TEMPORAL_TMPDIR}/${archive}"
  url="https://github.com/temporalio/cli/releases/download/v${TEMPORAL_CLI_VERSION}/${archive}"
  curl --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 15 -fL "$url" -o "$archive_path"
  echo "${expected_sha}  ${archive_path}" | sha256sum -c -
  tar -tzf "$archive_path" temporal >/dev/null
  tar -xzf "$archive_path" -C "$TEMPORAL_TMPDIR" temporal
  install -m 0755 "$TEMPORAL_TMPDIR/temporal" /usr/local/bin/temporal
}

allocate_runtime_resources() {
  local suffix
  suffix="${BROWSER}-$(python3 - <<'PY'
import uuid
print(uuid.uuid4().hex[:8])
PY
)"
  WEB_E2E_API_PORT="$(choose_available_port)"
  WEB_E2E_TEMPORAL_PORT="$(choose_available_port)"
  while [[ "$WEB_E2E_TEMPORAL_PORT" == "$WEB_E2E_API_PORT" ]]; do
    WEB_E2E_TEMPORAL_PORT="$(choose_available_port)"
  done
  WEB_E2E_SQLITE_STATE_PATH="/tmp/video-digestor-api-web-e2e-${suffix}.db"
  WEB_E2E_SQLITE_PATH="/tmp/video-digestor-worker-web-e2e-${suffix}.db"
  WEB_E2E_WORKSPACE_DIR="/tmp/video-digestor-worker-web-e2e-workspace-${suffix}"
  WEB_E2E_ARTIFACT_ROOT="/tmp/video-digestor-worker-web-e2e-artifacts-${suffix}"
  log "allocated web-e2e ports: api=${WEB_E2E_API_PORT}, temporal=${WEB_E2E_TEMPORAL_PORT}"
}

run_migrations() {
  require_command pg_isready
  require_command psql
  [[ -n "$DATABASE_URL" ]] || fail "DATABASE_URL is required"

  local pg_url
  pg_url="$(python3 - "$DATABASE_URL" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

value = sys.argv[1]
parsed = urlsplit(value)
if not parsed.scheme or not parsed.netloc:
    raise SystemExit(1)
pg_scheme = parsed.scheme.split('+', 1)[0]
print(urlunsplit((pg_scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment)))
PY
)" || fail "DATABASE_URL must be a valid postgres URL"

  for _ in $(seq 1 30); do
    if pg_isready -d "$pg_url" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  mapfile -t migration_files < <(find "$ROOT_DIR/infra/migrations" -maxdepth 1 -type f -name '*.sql' | sort)
  [[ "${#migration_files[@]}" -gt 0 ]] || fail "no SQL migrations found under infra/migrations"
  for migration in "${migration_files[@]}"; do
    psql "$pg_url" -v ON_ERROR_STOP=1 -f "$migration"
  done
}

start_temporal() {
  mkdir -p "$ROOT_DIR/.runtime-cache"
  temporal server start-dev --ip 127.0.0.1 --port "$WEB_E2E_TEMPORAL_PORT" > "$ROOT_DIR/.runtime-cache/web-e2e-temporal.log" 2>&1 &
  TEMPORAL_PID="$!"
  wait_for_tcp "$WEB_E2E_TEMPORAL_PORT" "temporal web-e2e" 60
}

start_api() {
  [[ -n "$DATABASE_URL" ]] || fail "DATABASE_URL is required"
  : > "$ROOT_DIR/.runtime-cache/web-e2e-api.log"
  (
    cd "$ROOT_DIR" && \
    DATABASE_URL="$DATABASE_URL" \
    VD_API_KEY="video-digestor-local-dev-token" \
    WEB_ACTION_SESSION_TOKEN="video-digestor-local-dev-token" \
    TEMPORAL_TARGET_HOST="127.0.0.1:${WEB_E2E_TEMPORAL_PORT}" \
    TEMPORAL_NAMESPACE="default" \
    TEMPORAL_TASK_QUEUE="video-analysis-worker" \
    SQLITE_STATE_PATH="$WEB_E2E_SQLITE_STATE_PATH" \
    UI_AUDIT_GEMINI_ENABLED="false" \
    NOTIFICATION_ENABLED="0" \
    ./scripts/dev_api.sh --host 127.0.0.1 --port "$WEB_E2E_API_PORT" --no-reload
  ) > "$ROOT_DIR/.runtime-cache/web-e2e-api.log" 2>&1 &
  API_PID="$!"
  wait_for_http_ok "http://127.0.0.1:${WEB_E2E_API_PORT}/healthz" "web-e2e api" 120
}

start_worker() {
  [[ -n "$DATABASE_URL" ]] || fail "DATABASE_URL is required"
  : > "$ROOT_DIR/.runtime-cache/web-e2e-worker.log"
  (
    cd "$ROOT_DIR" && \
    DATABASE_URL="$DATABASE_URL" \
    TEMPORAL_TARGET_HOST="127.0.0.1:${WEB_E2E_TEMPORAL_PORT}" \
    TEMPORAL_NAMESPACE="default" \
    TEMPORAL_TASK_QUEUE="video-analysis-worker" \
    SQLITE_PATH="$WEB_E2E_SQLITE_PATH" \
    PIPELINE_WORKSPACE_DIR="$WEB_E2E_WORKSPACE_DIR" \
    PIPELINE_ARTIFACT_ROOT="$WEB_E2E_ARTIFACT_ROOT" \
    UI_AUDIT_GEMINI_ENABLED="false" \
    NOTIFICATION_ENABLED="0" \
    ./scripts/dev_worker.sh --no-show-hints
  ) > "$ROOT_DIR/.runtime-cache/web-e2e-worker.log" 2>&1 &
  WORKER_PID="$!"
  for _ in $(seq 1 30); do
    if ! kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      tail -n 80 "$ROOT_DIR/.runtime-cache/web-e2e-worker.log" >&2 || true
      fail "web-e2e worker exited unexpectedly"
    fi
    if temporal_task_queue_has_worker_pollers; then
      log "web-e2e worker pollers detected on task queue video-analysis-worker"
      return 0
    fi
    sleep 1
  done
  tail -n 80 "$ROOT_DIR/.runtime-cache/web-e2e-worker.log" >&2 || true
  fail "web-e2e worker failed readiness probe (no task queue pollers within 30s)"
}

install_playwright_browser() {
  for attempt in $(seq 1 8); do
    if uv run --with playwright python -m playwright install --with-deps "$BROWSER"; then
      return 0
    fi
    log "playwright install attempt ${attempt}/8 failed, retrying..."
    sleep 8
  done
  fail "playwright install failed after retries"
}

run_web_e2e_pytest() {
  mkdir -p "$ROOT_DIR/.runtime-cache"
  set -o pipefail
  (
    cd "$ROOT_DIR" && \
    uv run --with pytest --with playwright \
      pytest apps/web/tests/e2e \
      --ignore=apps/web/tests/e2e/test_mobile_breakpoints.py \
      --ignore=apps/web/tests/e2e/test_perceived_latency.py \
      --ignore=apps/web/tests/e2e/test_reduced_motion.py \
      -q --junitxml=".runtime-cache/web-e2e-junit-${BROWSER}.xml" -rA \
      --web-e2e-browser "$BROWSER" \
      --web-e2e-api-base-url "http://127.0.0.1:${WEB_E2E_API_PORT}" \
      2>&1 | tee ".runtime-cache/web-e2e-${BROWSER}.log"
  )
}

check_junit_no_silent_skip() {
  BROWSER="$BROWSER" ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import os
import xml.etree.ElementTree as ET
from pathlib import Path

browser = os.environ["BROWSER"]
root_dir = Path(os.environ["ROOT_DIR"])
report = root_dir / ".runtime-cache" / f"web-e2e-junit-{browser}.xml"
if not report.is_file():
    raise SystemExit("web e2e gate failed: junit report missing")

root = ET.parse(report).getroot()
suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
skipped = sum(int(suite.attrib.get("skipped", "0")) for suite in suites)

if tests == 0:
    raise SystemExit("web e2e gate failed: collected 0 tests")
if skipped > 0:
    raise SystemExit(f"web e2e gate failed: skipped={skipped} (no silent skip allowed)")
print(f"web e2e gate passed ({browser}): tests={tests}, skipped={skipped}")
PY
}

cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi
  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi
  if [[ -n "$TEMPORAL_PID" ]] && kill -0 "$TEMPORAL_PID" >/dev/null 2>&1; then
    kill "$TEMPORAL_PID" >/dev/null 2>&1 || true
    wait "$TEMPORAL_PID" 2>/dev/null || true
  fi
  if [[ -n "$TEMPORAL_TMPDIR" && -d "$TEMPORAL_TMPDIR" ]]; then
    rm -rf "$TEMPORAL_TMPDIR"
  fi
  rm -f "$WEB_E2E_SQLITE_STATE_PATH" "$WEB_E2E_SQLITE_PATH"
  rm -rf "$WEB_E2E_WORKSPACE_DIR" "$WEB_E2E_ARTIFACT_ROOT"
}
trap cleanup EXIT

export STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY=1
source "$ROOT_DIR/scripts/bootstrap_strict_ci_runtime.sh"
unset STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY
configure_strict_ci_python_environment

if [[ "$BROWSER" == "-h" || "$BROWSER" == "--help" ]]; then
  usage
  exit 0
fi
case "$BROWSER" in
  chromium|firefox|webkit) ;;
  *) fail "browser must be one of: chromium, firefox, webkit" ;;
esac

require_command python3
require_command uv
require_command curl
require_command install

mkdir -p "$ROOT_DIR/.runtime-cache"
cd "$ROOT_DIR"
ensure_node_toolchain
require_command npm

if [[ "${STRICT_CI_BOOTSTRAP_RUNTIME_READY:-0}" != "1" ]]; then
  source "$ROOT_DIR/scripts/bootstrap_strict_ci_runtime.sh"
elif ! declare -F install_web_npm_wrapper >/dev/null || ! declare -F ensure_web_arm64_native_optional_deps >/dev/null; then
  export STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY=1
  source "$ROOT_DIR/scripts/bootstrap_strict_ci_runtime.sh"
  unset STRICT_CI_BOOTSTRAP_LOAD_HELPERS_ONLY
  install_web_npm_wrapper
fi

install_temporal_cli
allocate_runtime_resources
run_migrations
start_temporal
start_api
start_worker
install_playwright_browser
run_web_e2e_pytest
check_junit_no_silent_skip
