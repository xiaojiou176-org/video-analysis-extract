#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="smoke_full_stack"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"
LIVE_DIAGNOSTICS_JSON=".runtime-cache/e2e-live-smoke-result.json"
API_BASE="http://127.0.0.1:8000"
WEB_BASE="http://127.0.0.1:3001"
REQUIRE_READER="1"
MINIFLUX_BASE=""
NEXTFLUX_PORT="3000"
OFFLINE_FALLBACK="1"
READER_ENV_FILE="$ROOT_DIR/env/profiles/reader.env"
HEARTBEAT_SECONDS="30"
LIVE_SMOKE_API_BASE_URL="http://127.0.0.1:8000"
LIVE_SMOKE_REQUIRE_API="1"
LIVE_SMOKE_REQUIRE_SECRETS="0"
LIVE_SMOKE_COMPUTER_USE_STRICT="1"
LIVE_SMOKE_COMPUTER_USE_SKIP="0"
LIVE_SMOKE_COMPUTER_USE_SKIP_REASON=""
YOUTUBE_SMOKE_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"

usage() {
  cat <<'EOF'
Usage: scripts/smoke_full_stack.sh [options]

Options:
  --profile, --env-profile <name>     Env profile passed to load_repo_env (default: local)
  --api-base-url <url>                API base URL (default: http://127.0.0.1:8000)
  --web-base-url <url>                Web base URL (default: http://127.0.0.1:3001)
  --require-reader <0|1>              Require reader checks (default: 1)
  --offline-fallback <0|1>            Allow offline fallback marker skip (default: 1)
  --reader-env-file <path>            Reader env file for Miniflux/Nextflux values
  --heartbeat-seconds <n>             Smoke heartbeat interval (default: 30)
  --live-smoke-api-base-url <url>     e2e live smoke API base URL
  --live-smoke-require-api <0|1>      e2e live smoke require API health gate (default: 1)
  --live-smoke-require-secrets <0|1>  e2e live smoke require secrets (default: 0)
  --live-smoke-computer-use-strict <0|1>
                                       e2e live smoke computer-use strict mode (default: 1)
  --live-smoke-computer-use-skip <0|1>
                                       e2e live smoke skip computer-use phase (default: 0)
  --live-smoke-computer-use-skip-reason <text>
                                       e2e live smoke skip reason when skip=1
  --youtube-smoke-url <url>           e2e live smoke YouTube URL
  --live-diagnostics-json <path>      e2e live smoke diagnostics output path
  -h, --help                          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    --api-base-url)
      API_BASE="${2:-}"
      shift 2
      ;;
    --web-base-url)
      WEB_BASE="${2:-}"
      shift 2
      ;;
    --require-reader)
      REQUIRE_READER="${2:-}"
      shift 2
      ;;
    --offline-fallback)
      OFFLINE_FALLBACK="${2:-}"
      shift 2
      ;;
    --reader-env-file)
      READER_ENV_FILE="${2:-}"
      shift 2
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="${2:-}"
      shift 2
      ;;
    --live-smoke-api-base-url)
      LIVE_SMOKE_API_BASE_URL="${2:-}"
      shift 2
      ;;
    --live-smoke-require-api)
      LIVE_SMOKE_REQUIRE_API="${2:-}"
      shift 2
      ;;
    --live-smoke-require-secrets)
      LIVE_SMOKE_REQUIRE_SECRETS="${2:-}"
      shift 2
      ;;
    --live-smoke-computer-use-strict)
      LIVE_SMOKE_COMPUTER_USE_STRICT="${2:-}"
      shift 2
      ;;
    --live-smoke-computer-use-skip)
      LIVE_SMOKE_COMPUTER_USE_SKIP="${2:-}"
      shift 2
      ;;
    --live-smoke-computer-use-skip-reason)
      LIVE_SMOKE_COMPUTER_USE_SKIP_REASON="${2:-}"
      shift 2
      ;;
    --youtube-smoke-url)
      YOUTUBE_SMOKE_URL="${2:-}"
      shift 2
      ;;
    --live-diagnostics-json)
      LIVE_DIAGNOSTICS_JSON="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      echo "[$SCRIPT_NAME] unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"

FALLBACK_MARKER_FILE="$ROOT_DIR/.runtime-cache/full-stack/offline-fallback.flag"
MINIFLUX_BASE="${MINIFLUX_BASE_URL:-$MINIFLUX_BASE}"
NEXTFLUX_PORT="${NEXTFLUX_PORT:-$NEXTFLUX_PORT}"
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
if ! (cd "$ROOT_DIR" && ./scripts/e2e_live_smoke.sh \
  --profile "$ENV_PROFILE" \
  --api-base-url "$LIVE_SMOKE_API_BASE_URL" \
  --require-api "$LIVE_SMOKE_REQUIRE_API" \
  --require-secrets "$LIVE_SMOKE_REQUIRE_SECRETS" \
  --computer-use-strict "$LIVE_SMOKE_COMPUTER_USE_STRICT" \
  --computer-use-skip "$LIVE_SMOKE_COMPUTER_USE_SKIP" \
  --computer-use-skip-reason "$LIVE_SMOKE_COMPUTER_USE_SKIP_REASON" \
  --youtube-url "$YOUTUBE_SMOKE_URL" \
  --diagnostics-json "$LIVE_DIAGNOSTICS_JSON"); then
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
    fail "--require-reader=1 but MINIFLUX_BASE_URL is empty"
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
