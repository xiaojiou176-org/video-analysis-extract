#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="e2e_live_smoke"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Keep parent-shell overrides for API routing knobs before loading repo .env files.
SHELL_VD_API_BASE_URL="${VD_API_BASE_URL-}"
SHELL_VD_API_BASE_URL_SET="${VD_API_BASE_URL+x}"
SHELL_LIVE_SMOKE_API_BASE_URL="${LIVE_SMOKE_API_BASE_URL-}"
SHELL_LIVE_SMOKE_API_BASE_URL_SET="${LIVE_SMOKE_API_BASE_URL+x}"
SHELL_LIVE_SMOKE_API_PORT="${LIVE_SMOKE_API_PORT-}"
SHELL_LIVE_SMOKE_API_PORT_SET="${LIVE_SMOKE_API_PORT+x}"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

if [[ -n "$SHELL_VD_API_BASE_URL_SET" ]]; then
  VD_API_BASE_URL="$SHELL_VD_API_BASE_URL"
fi
if [[ -n "$SHELL_LIVE_SMOKE_API_BASE_URL_SET" ]]; then
  LIVE_SMOKE_API_BASE_URL="$SHELL_LIVE_SMOKE_API_BASE_URL"
fi
if [[ -n "$SHELL_LIVE_SMOKE_API_PORT_SET" ]]; then
  LIVE_SMOKE_API_PORT="$SHELL_LIVE_SMOKE_API_PORT"
fi

LIVE_SMOKE_API_PORT="${LIVE_SMOKE_API_PORT:-${API_PORT:-8000}}"
LIVE_SMOKE_API_BASE_URL="${LIVE_SMOKE_API_BASE_URL:-${VD_API_BASE_URL:-}}"
if [[ -z "$LIVE_SMOKE_API_BASE_URL" ]]; then
  LIVE_SMOKE_API_BASE_URL="http://127.0.0.1:${LIVE_SMOKE_API_PORT}"
fi
VD_API_BASE_URL="$LIVE_SMOKE_API_BASE_URL"

LIVE_SMOKE_TIMEOUT_SECONDS="${LIVE_SMOKE_TIMEOUT_SECONDS:-180}"
LIVE_SMOKE_REQUIRE_API="${LIVE_SMOKE_REQUIRE_API:-1}"
LIVE_SMOKE_POLL_INTERVAL_SECONDS="${LIVE_SMOKE_POLL_INTERVAL_SECONDS:-3}"
LIVE_SMOKE_HEALTH_PATH="${LIVE_SMOKE_HEALTH_PATH:-/healthz}"
LIVE_SMOKE_COMPUTER_USE_STRICT="${LIVE_SMOKE_COMPUTER_USE_STRICT:-1}"
LIVE_SMOKE_COMPUTER_USE_SKIP="${LIVE_SMOKE_COMPUTER_USE_SKIP:-0}"
LIVE_SMOKE_COMPUTER_USE_SKIP_REASON="${LIVE_SMOKE_COMPUTER_USE_SKIP_REASON:-}"
LIVE_SMOKE_COMPUTER_USE_CMD="${LIVE_SMOKE_COMPUTER_USE_CMD:-}"
LIVE_SMOKE_REQUIRE_SECRETS="${LIVE_SMOKE_REQUIRE_SECRETS:-0}"
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

require_enum() {
  local name="$1"
  local value="$2"
  shift 2
  local allowed=("$@")
  local candidate
  for candidate in "${allowed[@]}"; do
    if [[ "$value" == "$candidate" ]]; then
      return 0
    fi
  done
  fail "invalid ${name}=${value}; allowed: ${allowed[*]}"
}

trim_whitespace() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

resolve_local_script_path() {
  local raw_path="$1"
  local candidate
  candidate="$(trim_whitespace "$raw_path")"
  [[ -n "$candidate" ]] || fail "script path is empty"

  if [[ "${candidate:0:1}" != "/" ]]; then
    candidate="$ROOT_DIR/$candidate"
  fi

  local resolved
  resolved="$(
    SCRIPT_PATH="$candidate" python3 - <<'PY'
import os
import pathlib

path = pathlib.Path(os.environ["SCRIPT_PATH"]).expanduser()
print(path.resolve())
PY
  )"

  case "$resolved" in
    "$ROOT_DIR/scripts/"*) ;;
    *)
      fail "script path must be under $ROOT_DIR/scripts: $resolved"
      ;;
  esac
  [[ -f "$resolved" ]] || fail "script file not found: $resolved"
  [[ -x "$resolved" ]] || fail "script file is not executable: $resolved"
  printf '%s' "$resolved"
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

  if ! [[ "$LIVE_SMOKE_API_PORT" =~ ^[0-9]+$ ]] || (( LIVE_SMOKE_API_PORT < 1 || LIVE_SMOKE_API_PORT > 65535 )); then
    fail "invalid LIVE_SMOKE_API_PORT=${LIVE_SMOKE_API_PORT}; expected integer in [1,65535]"
  fi
  if [[ -z "$LIVE_SMOKE_HEALTH_PATH" || "${LIVE_SMOKE_HEALTH_PATH:0:1}" != "/" ]]; then
    fail "invalid LIVE_SMOKE_HEALTH_PATH=${LIVE_SMOKE_HEALTH_PATH}; expected absolute path (e.g. /healthz)"
  fi

  local computer_use_strict
  computer_use_strict="$(printf '%s' "$LIVE_SMOKE_COMPUTER_USE_STRICT" | tr '[:upper:]' '[:lower:]')"
  require_enum "LIVE_SMOKE_COMPUTER_USE_STRICT" "$computer_use_strict" 0 1 true false yes no on off

  local computer_use_skip
  computer_use_skip="$(printf '%s' "$LIVE_SMOKE_COMPUTER_USE_SKIP" | tr '[:upper:]' '[:lower:]')"
  require_enum "LIVE_SMOKE_COMPUTER_USE_SKIP" "$computer_use_skip" 0 1 true false yes no on off

  log "API target: base=${VD_API_BASE_URL} port=${LIVE_SMOKE_API_PORT}"
  if [[ -z "$(trim_whitespace "$LIVE_SMOKE_COMPUTER_USE_CMD")" ]]; then
    LIVE_SMOKE_COMPUTER_USE_CMD="$ROOT_DIR/scripts/smoke_computer_use_local.sh"
  fi
  LIVE_SMOKE_COMPUTER_USE_CMD="$(resolve_local_script_path "$LIVE_SMOKE_COMPUTER_USE_CMD")"

  local missing=()
  [[ -z "${GEMINI_API_KEY:-}" ]] && missing+=("GEMINI_API_KEY")
  [[ -z "${RESEND_API_KEY:-}" ]] && missing+=("RESEND_API_KEY")
  [[ -z "${RESEND_FROM_EMAIL:-}" ]] && missing+=("RESEND_FROM_EMAIL")
  [[ -z "${YOUTUBE_API_KEY:-}" ]] && missing+=("YOUTUBE_API_KEY")

  if [[ "${#missing[@]}" -gt 0 ]]; then
    if is_truthy "$LIVE_SMOKE_REQUIRE_SECRETS"; then
      fail "missing required secrets: ${missing[*]}"
    fi
    log "SKIP: missing secrets: ${missing[*]}"
    exit 0
  fi

  local llm_input_mode
  llm_input_mode="$(printf '%s' "${PIPELINE_LLM_INPUT_MODE:-auto}" | tr '[:upper:]' '[:lower:]')"
  require_enum "PIPELINE_LLM_INPUT_MODE" "$llm_input_mode" auto text video_text frames_text

  local thinking_level
  thinking_level="$(printf '%s' "${GEMINI_THINKING_LEVEL:-high}" | tr '[:upper:]' '[:lower:]')"
  require_enum "GEMINI_THINKING_LEVEL" "$thinking_level" minimal low medium high
  log "LLM strategy: provider=gemini model=${GEMINI_MODEL:-gemini-3.1-pro-preview} fast_model=${GEMINI_FAST_MODEL:-gemini-3-flash-preview} thinking=${thinking_level} input_mode=${llm_input_mode} cache=${GEMINI_CONTEXT_CACHE_ENABLED:-true}"

  local status body response
  response="$(api_get "$LIVE_SMOKE_HEALTH_PATH")"
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

run_computer_use_smoke() {
  local strict_value skip_value skip_reason cmd
  strict_value="$(printf '%s' "$LIVE_SMOKE_COMPUTER_USE_STRICT" | tr '[:upper:]' '[:lower:]')"
  skip_value="$(printf '%s' "$LIVE_SMOKE_COMPUTER_USE_SKIP" | tr '[:upper:]' '[:lower:]')"
  skip_reason="$(trim_whitespace "$LIVE_SMOKE_COMPUTER_USE_SKIP_REASON")"
  cmd="$(trim_whitespace "$LIVE_SMOKE_COMPUTER_USE_CMD")"

  if is_truthy "$skip_value"; then
    [[ -n "$skip_reason" ]] || fail "LIVE_SMOKE_COMPUTER_USE_SKIP=1 requires LIVE_SMOKE_COMPUTER_USE_SKIP_REASON"
    log "Scenario: computer_use smoke skipped; reason=${skip_reason}"
    return 0
  fi

  if [[ -z "$cmd" ]]; then
    local message="computer_use smoke command is empty; set LIVE_SMOKE_COMPUTER_USE_CMD to a script path or skip with LIVE_SMOKE_COMPUTER_USE_SKIP=1 and reason"
    if is_truthy "$strict_value"; then
      fail "$message"
    fi
    log "Scenario: computer_use smoke non-strict skip; reason=${message}"
    return 0
  fi

  log "Scenario: computer_use smoke"
  if "$cmd" --api-base-url "$VD_API_BASE_URL"; then
    log "computer_use smoke passed"
    return 0
  fi

  if is_truthy "$strict_value"; then
    fail "computer_use smoke failed: cmd=${cmd}"
  fi
  log "Scenario: computer_use smoke non-strict skip; reason=command failed cmd=${cmd}"
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
  printf '%s\n' "$job_id"
}

wait_for_terminal_status() {
  local job_id="$1"
  local label="$2"
  local deadline=$((SECONDS + LIVE_SMOKE_TIMEOUT_SECONDS))
  local status=""
  local pipeline_final_status=""
  local effective_final_status=""
  local error_message=""

  while (( SECONDS < deadline )); do
    local response http_status body parsed
    response="$(api_get "/api/v1/jobs/${job_id}")"
    http_status="${response%%$'\n'*}"
    body="${response#*$'\n'}"
    [[ "$http_status" == "200" ]] || fail "${label}: query failed for job_id=${job_id}, status=${http_status}, body=${body}"

    parsed="$(
      BODY="$body" python3 - <<'PY'
import json
import os

obj = json.loads(os.environ["BODY"])
status = str(obj.get("status") or "")
pipeline_final_status = str(obj.get("pipeline_final_status") or "")
error_message = str(obj.get("error_message") or "")
print("\t".join((status, pipeline_final_status, error_message)))
PY
    )"
    status="${parsed%%$'\t'*}"
    parsed="${parsed#*$'\t'}"
    pipeline_final_status="${parsed%%$'\t'*}"
    error_message="${parsed#*$'\t'}"
    effective_final_status="$status"
    if [[ -n "$pipeline_final_status" ]]; then
      effective_final_status="$pipeline_final_status"
    fi

    if [[ "$status" != "queued" && "$status" != "running" ]]; then
      if [[ "$effective_final_status" == "failed" ]]; then
        fail "${label}: terminal status failed for job_id=${job_id}, status=${status}, pipeline_final_status=${pipeline_final_status:-null}, error=${error_message:-null}"
      fi
      log "${label}: terminal status reached for job_id=${job_id}, status=${status}, pipeline_final_status=${pipeline_final_status:-null}"
      return 0
    fi

    sleep "$LIVE_SMOKE_POLL_INTERVAL_SECONDS"
  done

  fail "${label}: timeout waiting terminal status for job_id=${job_id}, last_status=${status:-unknown}, last_pipeline_final_status=${pipeline_final_status:-null}"
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
  local youtube_job_id
  youtube_job_id="$(process_video "youtube" "$YOUTUBE_SMOKE_URL" "full" "youtube_full")"
  wait_for_terminal_status "$youtube_job_id" "video_process:youtube_full"

  log "Scenario: Bilibili full"
  local bilibili_job_id
  bilibili_job_id="$(process_video "bilibili" "$BILIBILI_SMOKE_URL" "full" "bilibili_full")"
  wait_for_terminal_status "$bilibili_job_id" "video_process:bilibili_full"

  log "Scenario: Gemini degrade(text_only fallback path)"
  local degrade_job_id
  degrade_job_id="$(process_video "youtube" "$YOUTUBE_SMOKE_URL" "text_only" "gemini_degrade")"
  wait_for_terminal_status "$degrade_job_id" "video_process:gemini_degrade"

  log "Scenario: video_digest retry recovery"
  run_worker_workflow_once "start-notification-retry-workflow" --retry-batch-limit 20

  log "Scenario: daily_digest dedupe"
  run_worker_workflow_once "start-daily-workflow"
  run_worker_workflow_once "start-daily-workflow"

  log "Scenario: provider canary"
  run_worker_workflow_once "start-provider-canary-workflow" --timeout-seconds "$LIVE_SMOKE_TIMEOUT_SECONDS"

  run_computer_use_smoke

  log "LIVE SMOKE DONE"
}

main "$@"
