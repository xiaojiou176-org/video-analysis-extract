#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="smoke_full_stack"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_BASE="${VD_API_BASE_URL:-http://127.0.0.1:${API_PORT:-8000}}"
WEB_BASE="${WEB_BASE_URL:-http://127.0.0.1:${WEB_PORT:-3001}}"
REQUIRE_READER="${FULL_STACK_REQUIRE_READER:-1}"
MINIFLUX_BASE="${MINIFLUX_BASE_URL:-}"
NEXTFLUX_PORT="${NEXTFLUX_PORT:-3000}"
OFFLINE_FALLBACK="${OFFLINE_FALLBACK:-1}"
READER_ENV_FILE="${READER_ENV_FILE:-$ROOT_DIR/.env.reader-stack}"
FALLBACK_MARKER_FILE="$ROOT_DIR/.runtime-cache/full-stack/offline-fallback.flag"
HEARTBEAT_SECONDS="${FULL_STACK_SMOKE_HEARTBEAT_SECONDS:-30}"
LIVE_DIAGNOSTICS_JSON="${LIVE_SMOKE_DIAGNOSTICS_JSON:-.runtime-cache/e2e-live-smoke-result.json}"
heartbeat_pid=""
AI_FEED_SYNC_TMP_OUTPUT=""

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
fail() { log "ERROR: $*"; exit 1; }

is_truthy() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

check_http_200() {
  local url="$1"
  local code attempt
  for attempt in $(seq 1 40); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" || true)"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    sleep 1
  done
  fail "http check failed: ${url} -> ${code}"
}

start_heartbeat() {
  local label="$1"
  (
    while true; do
      log "heartbeat: ${label} still running..."
      sleep "$HEARTBEAT_SECONDS"
    done
  ) &
  heartbeat_pid="$!"
}

stop_heartbeat() {
  if [[ -n "$heartbeat_pid" ]] && kill -0 "$heartbeat_pid" >/dev/null 2>&1; then
    kill "$heartbeat_pid" >/dev/null 2>&1 || true
    wait "$heartbeat_pid" 2>/dev/null || true
  fi
  heartbeat_pid=""
}

cleanup_temp_files() {
  if [[ -n "$AI_FEED_SYNC_TMP_OUTPUT" ]] && [[ -f "$AI_FEED_SYNC_TMP_OUTPUT" ]]; then
    rm -f "$AI_FEED_SYNC_TMP_OUTPUT"
  fi
}

cleanup() {
  stop_heartbeat
  cleanup_temp_files
}
trap cleanup EXIT

log "phase=short_tests status=start"
log "Checking API health"
check_http_200 "${API_BASE}/healthz"

log "Checking feed API"
check_http_200 "${API_BASE}/api/v1/feed/digests?limit=1"

log "Checking web UI"
check_http_200 "${WEB_BASE}"
log "phase=short_tests status=passed"

log "phase=long_tests status=start"
log "Running built-in e2e live smoke"
start_heartbeat "e2e_live_smoke"
if ! (cd "$ROOT_DIR" && LIVE_SMOKE_DIAGNOSTICS_JSON="$LIVE_DIAGNOSTICS_JSON" ./scripts/e2e_live_smoke.sh); then
  stop_heartbeat
  live_diag_path="$ROOT_DIR/$LIVE_DIAGNOSTICS_JSON"
  if [[ -f "$live_diag_path" ]]; then
    diag_summary="$(
      DIAG_PATH="$live_diag_path" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["DIAG_PATH"])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("failure_kind=unknown reason=diagnostics_parse_failed")
    raise SystemExit(0)
print(
    "failure_kind={kind} reason={reason}".format(
        kind=payload.get("failure_kind", "unknown"),
        reason=payload.get("reason", ""),
    )
)
PY
    )"
    log "e2e_live_smoke failed: ${diag_summary} diagnostics_path=${live_diag_path}"
  else
    log "e2e_live_smoke failed: diagnostics missing at ${live_diag_path}"
  fi
  fail "live smoke failed"
fi
stop_heartbeat
log "e2e_live_smoke diagnostics_path=$ROOT_DIR/$LIVE_DIAGNOSTICS_JSON"

if is_truthy "$REQUIRE_READER"; then
  if [[ -z "$MINIFLUX_BASE" && -f "$READER_ENV_FILE" ]]; then
    load_env_file "$READER_ENV_FILE" "$SCRIPT_NAME"
    MINIFLUX_BASE="${MINIFLUX_BASE_URL:-}"
    NEXTFLUX_PORT="${NEXTFLUX_PORT:-3000}"
  fi
  if [[ -f "$FALLBACK_MARKER_FILE" ]] && is_truthy "$OFFLINE_FALLBACK"; then
    log "Reader checks skipped due offline fallback marker: $FALLBACK_MARKER_FILE"
    log "Marker details: $(tr '\n' ' ' < "$FALLBACK_MARKER_FILE")"
    log "Smoke checks passed (reader stack degraded)"
    exit 0
  fi
  if [[ -z "$MINIFLUX_BASE" ]]; then
    fail "FULL_STACK_REQUIRE_READER=1 but MINIFLUX_BASE_URL is empty"
  fi
  log "Checking Miniflux"
  check_http_200 "$MINIFLUX_BASE"
  nextflux_base="http://127.0.0.1:${NEXTFLUX_PORT}"
  log "Checking Nextflux"
  check_http_200 "$nextflux_base"

  log "Running AI feed -> Miniflux sync"
  AI_FEED_SYNC_TMP_OUTPUT="$(mktemp)"
  start_heartbeat "run_ai_feed_sync"
  (cd "$ROOT_DIR" && ./scripts/run_ai_feed_sync.sh >"$AI_FEED_SYNC_TMP_OUTPUT")
  stop_heartbeat
  log "AI feed sync result: $(cat "$AI_FEED_SYNC_TMP_OUTPUT")"
  cleanup_temp_files
  AI_FEED_SYNC_TMP_OUTPUT=""
fi

log "phase=long_tests status=passed"
log "Smoke checks passed"
