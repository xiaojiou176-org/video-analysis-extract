#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="run_daily_digest"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
# shellcheck source=./scripts/lib/http_api.sh
source "$ROOT_DIR/scripts/lib/http_api.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_BASE_URL_OVERRIDE=""
digest_date="$(date -u +%F)"
digest_channel="email"
digest_dry_run="false"
digest_force="false"
digest_to_email=""
digest_fallback_enabled="1"

HTTP_STATUS=""
HTTP_BODY=""

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

json_bool() {
  if is_truthy "${1:-}"; then
    printf 'true'
  else
    printf 'false'
  fi
}

build_daily_payload() {
  local dry_run force
  dry_run="$(json_bool "$digest_dry_run")"
  force="$(json_bool "$digest_force")"

  python3 - "$digest_date" "$digest_channel" "$dry_run" "$force" <<'PY'
import json
import sys

print(
    json.dumps(
        {
            "date": sys.argv[1],
            "channel": sys.argv[2],
            "dry_run": sys.argv[3] == "true",
            "force": sys.argv[4] == "true",
        },
        ensure_ascii=False,
    )
)
PY
}

try_primary_route() {
  local payload
  payload="$(build_daily_payload)"
  api_post "/api/v1/reports/daily/send" "$payload"

  if [[ "$HTTP_STATUS" -ge 200 && "$HTTP_STATUS" -lt 300 ]]; then
    log "Primary route succeeded: /api/v1/reports/daily/send"
    log "Response: $(safe_body_preview "$HTTP_BODY")"
    return 0
  fi

  if [[ "$HTTP_STATUS" == "404" || "$HTTP_STATUS" == "405" ]]; then
    log "Primary route unavailable (status=${HTTP_STATUS}), fallback will be used."
    return 1
  fi

  fail "Primary route failed: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
}

fallback_daily_send() {
  log "Fallback step 1/3: fetching latest succeeded video."
  api_get "/api/v1/videos?status=succeeded&limit=1"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "Failed to list succeeded videos: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
  fi

  local latest_job_id
  latest_job_id="$(
    BODY="$HTTP_BODY" python3 - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ["BODY"] or "[]")
except json.JSONDecodeError:
    payload = []

job_id = ""
if isinstance(payload, list) and payload:
    first = payload[0]
    if isinstance(first, dict) and isinstance(first.get("last_job_id"), str):
        job_id = first["last_job_id"]

print(job_id)
PY
  )"

  if [[ -z "$latest_job_id" ]]; then
    log "No succeeded jobs found, nothing to send."
    exit 0
  fi

  log "Fallback step 2/3: reading artifact markdown for job ${latest_job_id}."
  api_get "/api/v1/artifacts/markdown?job_id=${latest_job_id}"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "Failed to read digest artifact: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
  fi
  local markdown
  markdown="$HTTP_BODY"

  log "Fallback step 3/3: sending digest via /api/v1/notifications/test."
  local markdown_file
  markdown_file="$(mktemp)"
  printf '%s' "$markdown" >"$markdown_file"

  local payload
  payload="$(
    python3 - "$digest_date" "$digest_to_email" "$latest_job_id" "$markdown_file" <<'PY'
import json
import sys
from pathlib import Path

digest_date = sys.argv[1]
to_email = sys.argv[2].strip() or None
job_id = sys.argv[3]
digest = Path(sys.argv[4]).read_text(encoding="utf-8")

subject = f"[Video Digestor] Daily digest {digest_date}"
body = f"job_id: {job_id}\n\ndate: {digest_date}\n\n{digest}"

payload = {
    "subject": subject,
    "body": body,
}
if to_email:
    payload["to_email"] = to_email

print(json.dumps(payload, ensure_ascii=False))
PY
  )"
  rm -f "$markdown_file"

  api_post "/api/v1/notifications/test" "$payload"
  if [[ "$HTTP_STATUS" -ge 200 && "$HTTP_STATUS" -lt 300 ]]; then
    log "Fallback send succeeded."
    log "Response: $(safe_body_preview "$HTTP_BODY")"
    return 0
  fi

  fail "Fallback send failed: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
}

main() {
  require_cmd curl
  require_cmd python3

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --api-base-url) API_BASE_URL_OVERRIDE="${2:-}"; shift 2 ;;
      --date) digest_date="${2:-}"; shift 2 ;;
      --channel) digest_channel="${2:-}"; shift 2 ;;
      --dry-run) digest_dry_run="${2:-}"; shift 2 ;;
      --force) digest_force="${2:-}"; shift 2 ;;
      --to-email) digest_to_email="${2:-}"; shift 2 ;;
      --fallback-enabled) digest_fallback_enabled="${2:-}"; shift 2 ;;
      -h|--help)
        cat <<'USAGE'
Usage: scripts/run_daily_digest.sh [options]
  --api-base-url <url>
  --date <YYYY-MM-DD>
  --channel <name>
  --dry-run <true|false>
  --force <true|false>
  --to-email <email>
  --fallback-enabled <0|1|true|false>
USAGE
        exit 0
        ;;
      *) fail "unknown argument: $1" ;;
    esac
  done

  cd "$ROOT_DIR"
  apply_http_api_base_url "$API_BASE_URL_OVERRIDE" "$ROOT_DIR"
  check_api_health

  if try_primary_route; then
    return 0
  fi

  if ! is_truthy "$digest_fallback_enabled"; then
    fail "Fallback disabled (--fallback-enabled=${digest_fallback_enabled})."
  fi

  fallback_daily_send
}

main "$@"
