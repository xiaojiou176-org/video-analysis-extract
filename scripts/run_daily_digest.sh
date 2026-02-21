#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="run_daily_digest"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_env_file "$ROOT_DIR/.env.local" "$SCRIPT_NAME"

VD_API_BASE_URL="${VD_API_BASE_URL:-http://127.0.0.1:8000}"
DIGEST_DATE="${DIGEST_DATE:-$(date -u +%F)}"
DIGEST_CHANNEL="${DIGEST_CHANNEL:-email}"
DIGEST_DRY_RUN="${DIGEST_DRY_RUN:-false}"
DIGEST_FORCE="${DIGEST_FORCE:-false}"
DIGEST_TO_EMAIL="${DIGEST_TO_EMAIL:-}"
DIGEST_FALLBACK_ENABLED="${DIGEST_FALLBACK_ENABLED:-1}"

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

api_get() {
  local path="$1"
  local tmp_body
  tmp_body="$(mktemp)"

  local status
  if ! status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      "${VD_API_BASE_URL}${path}"
  )"; then
    rm -f "$tmp_body"
    fail "GET ${path} failed (network error)"
  fi

  HTTP_STATUS="$status"
  HTTP_BODY="$(cat "$tmp_body")"
  rm -f "$tmp_body"
}

api_post() {
  local path="$1"
  local payload="$2"
  local tmp_body
  tmp_body="$(mktemp)"

  local status
  if ! status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -X POST "${VD_API_BASE_URL}${path}" \
      --data "$payload"
  )"; then
    rm -f "$tmp_body"
    fail "POST ${path} failed (network error)"
  fi

  HTTP_STATUS="$status"
  HTTP_BODY="$(cat "$tmp_body")"
  rm -f "$tmp_body"
}

check_api_health() {
  api_get "/healthz"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "API health check failed: status=${HTTP_STATUS}, body=${HTTP_BODY}"
  fi
  log "API reachable: ${VD_API_BASE_URL}"
}

build_daily_payload() {
  local dry_run force
  dry_run="$(json_bool "$DIGEST_DRY_RUN")"
  force="$(json_bool "$DIGEST_FORCE")"

  DIGEST_DATE="$DIGEST_DATE" DIGEST_CHANNEL="$DIGEST_CHANNEL" DRY_RUN="$dry_run" FORCE="$force" \
    python3 - <<'PY'
import json
import os

print(
    json.dumps(
        {
            "date": os.environ["DIGEST_DATE"],
            "channel": os.environ["DIGEST_CHANNEL"],
            "dry_run": os.environ["DRY_RUN"] == "true",
            "force": os.environ["FORCE"] == "true",
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
    log "Response: ${HTTP_BODY}"
    return 0
  fi

  if [[ "$HTTP_STATUS" == "404" || "$HTTP_STATUS" == "405" ]]; then
    log "Primary route unavailable (status=${HTTP_STATUS}), fallback will be used."
    return 1
  fi

  fail "Primary route failed: status=${HTTP_STATUS}, body=${HTTP_BODY}"
}

fallback_daily_send() {
  log "Fallback step 1/3: fetching latest succeeded video."
  api_get "/api/v1/videos?status=succeeded&limit=1"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "Failed to list succeeded videos: status=${HTTP_STATUS}, body=${HTTP_BODY}"
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
    fail "Failed to read digest artifact: status=${HTTP_STATUS}, body=${HTTP_BODY}"
  fi
  local markdown
  markdown="$HTTP_BODY"

  log "Fallback step 3/3: sending digest via /api/v1/notifications/test."
  local markdown_file
  markdown_file="$(mktemp)"
  printf '%s' "$markdown" >"$markdown_file"

  local payload
  payload="$(
    DIGEST_DATE="$DIGEST_DATE" DIGEST_TO_EMAIL="$DIGEST_TO_EMAIL" JOB_ID="$latest_job_id" \
      DIGEST_MARKDOWN_FILE="$markdown_file" python3 - <<'PY'
import json
import os
from pathlib import Path

digest = Path(os.environ["DIGEST_MARKDOWN_FILE"]).read_text(encoding="utf-8")
digest_date = os.environ["DIGEST_DATE"]
job_id = os.environ["JOB_ID"]
to_email = os.environ.get("DIGEST_TO_EMAIL", "").strip() or None

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
    log "Response: ${HTTP_BODY}"
    return 0
  fi

  fail "Fallback send failed: status=${HTTP_STATUS}, body=${HTTP_BODY}"
}

main() {
  require_cmd curl
  require_cmd python3

  cd "$ROOT_DIR"
  check_api_health

  if try_primary_route; then
    return 0
  fi

  if ! is_truthy "$DIGEST_FALLBACK_ENABLED"; then
    fail "Fallback disabled (DIGEST_FALLBACK_ENABLED=${DIGEST_FALLBACK_ENABLED})."
  fi

  fallback_daily_send
}

main "$@"
