#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="e2e_live_smoke"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_env_file "$ROOT_DIR/.env.local" "$SCRIPT_NAME"

VD_API_BASE_URL="${VD_API_BASE_URL:-http://127.0.0.1:8000}"
LIVE_SMOKE_TIMEOUT_SECONDS="${LIVE_SMOKE_TIMEOUT_SECONDS:-60}"
LIVE_SMOKE_REQUIRE_API="${LIVE_SMOKE_REQUIRE_API:-0}"
YOUTUBE_SMOKE_URL="${YOUTUBE_SMOKE_URL:-https://www.youtube.com/watch?v=dQw4w9WgXcQ}"
BILIBILI_SMOKE_URL="${BILIBILI_SMOKE_URL:-https://www.bilibili.com/video/BV1xx411c7mD}"

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

is_truthy() {
  local value
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

api_post() {
  local path="$1"
  local payload="$2"
  local tmp_body
  tmp_body="$(mktemp)"
  local status
  status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -X POST "${VD_API_BASE_URL}${path}" \
      --data "$payload"
  )"
  local body
  body="$(cat "$tmp_body")"
  rm -f "$tmp_body"
  printf '%s\n%s' "$status" "$body"
}

api_get() {
  local path="$1"
  local tmp_body
  tmp_body="$(mktemp)"
  local status
  status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      "${VD_API_BASE_URL}${path}"
  )"
  local body
  body="$(cat "$tmp_body")"
  rm -f "$tmp_body"
  printf '%s\n%s' "$status" "$body"
}

check_prerequisites() {
  require_cmd curl
  require_cmd python3

  local missing=()
  [[ -z "${GEMINI_API_KEY:-}" ]] && missing+=("GEMINI_API_KEY")
  [[ -z "${RESEND_API_KEY:-}" ]] && missing+=("RESEND_API_KEY")
  [[ -z "${RESEND_FROM_EMAIL:-}" ]] && missing+=("RESEND_FROM_EMAIL")
  [[ -z "${YOUTUBE_API_KEY:-}" ]] && missing+=("YOUTUBE_API_KEY")

  if [[ "${#missing[@]}" -gt 0 ]]; then
    log "SKIP: missing secrets: ${missing[*]}"
    exit 0
  fi

  local status body response
  response="$(api_get "/healthz")"
  status="${response%%$'\n'*}"
  body="${response#*$'\n'}"
  if [[ "$status" != "200" ]]; then
    if is_truthy "$LIVE_SMOKE_REQUIRE_API"; then
      fail "API health check failed: status=${status} body=${body}"
    fi
    log "SKIP: API is unavailable at ${VD_API_BASE_URL} (status=${status})"
    exit 0
  fi
}

process_video() {
  local platform="$1"
  local url="$2"
  local mode="$3"
  local label="$4"

  local payload
  payload="$(
    PLATFORM="$platform" URL="$url" MODE="$mode" python3 - <<'PY'
import json
import os
print(json.dumps({
  "video": {"platform": os.environ["PLATFORM"], "url": os.environ["URL"]},
  "mode": os.environ["MODE"],
  "overrides": {},
  "force": True,
}))
PY
  )"
  local status body response
  response="$(api_post "/api/v1/videos/process" "$payload")"
  status="${response%%$'\n'*}"
  body="${response#*$'\n'}"
  if [[ "$status" != "202" ]]; then
    fail "${label} failed: status=${status} body=${body}"
  fi
  local job_id
  job_id="$(BODY="$body" python3 - <<'PY'
import json, os
obj = json.loads(os.environ["BODY"])
print(obj.get("job_id") or "")
PY
  )"
  [[ -z "$job_id" ]] && fail "${label} missing job_id: body=${body}"
  log "${label}: queued job_id=${job_id}"
}

run_worker_workflow_once() {
  local command_name="$1"
  shift
  (
    cd "$ROOT_DIR/apps/worker"
    if command -v uv >/dev/null 2>&1; then
      PYTHONPATH="$ROOT_DIR/apps/worker:$ROOT_DIR:${PYTHONPATH:-}" \
        uv run python -m worker.main "$command_name" --run-once "$@" >/tmp/"$SCRIPT_NAME"."$command_name".json
    else
      PYTHONPATH="$ROOT_DIR/apps/worker:$ROOT_DIR:${PYTHONPATH:-}" \
        python3 -m worker.main "$command_name" --run-once "$@" >/tmp/"$SCRIPT_NAME"."$command_name".json
    fi
  ) || fail "worker command failed: ${command_name}"
}

main() {
  check_prerequisites

  log "Scenario: YouTube full"
  process_video "youtube" "$YOUTUBE_SMOKE_URL" "full" "youtube_full"

  log "Scenario: Bilibili full"
  process_video "bilibili" "$BILIBILI_SMOKE_URL" "full" "bilibili_full"

  log "Scenario: Gemini degrade(text_only fallback path)"
  process_video "youtube" "$YOUTUBE_SMOKE_URL" "text_only" "gemini_degrade"

  log "Scenario: video_digest retry recovery"
  run_worker_workflow_once "start-notification-retry-workflow" --retry-batch-limit 20

  log "Scenario: daily_digest dedupe"
  run_worker_workflow_once "start-daily-workflow"
  run_worker_workflow_once "start-daily-workflow"

  log "Scenario: provider canary"
  run_worker_workflow_once "start-provider-canary-workflow" --timeout-seconds "$LIVE_SMOKE_TIMEOUT_SECONDS"

  log "LIVE SMOKE DONE"
}

main "$@"
