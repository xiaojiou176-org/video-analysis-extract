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

log "Running built-in e2e live smoke"
(cd "$ROOT_DIR" && ./scripts/e2e_live_smoke.sh)

log "Checking feed API"
check_http_200 "${API_BASE}/api/v1/feed/digests?limit=1"

log "Checking web UI"
check_http_200 "${WEB_BASE}"

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
  (cd "$ROOT_DIR" && ./scripts/run_ai_feed_sync.sh >/tmp/ai-feed-sync.out)
  log "AI feed sync result: $(cat /tmp/ai-feed-sync.out)"
fi

log "Smoke checks passed"
