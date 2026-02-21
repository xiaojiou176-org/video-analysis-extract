#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="run_failure_alerts"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VD_API_BASE_URL="${VD_API_BASE_URL:-http://127.0.0.1:8000}"
FAILURE_LOOKBACK_HOURS="${FAILURE_LOOKBACK_HOURS:-24}"
FAILURE_LIMIT="${FAILURE_LIMIT:-20}"
FAILURE_CHANNEL="${FAILURE_CHANNEL:-email}"
FAILURE_DRY_RUN="${FAILURE_DRY_RUN:-false}"
FAILURE_FORCE="${FAILURE_FORCE:-false}"
FAILURE_TO_EMAIL="${FAILURE_TO_EMAIL:-}"
FAILURE_FALLBACK_ENABLED="${FAILURE_FALLBACK_ENABLED:-1}"

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

build_failure_payload() {
  local dry_run force
  dry_run="$(json_bool "$FAILURE_DRY_RUN")"
  force="$(json_bool "$FAILURE_FORCE")"

  FAILURE_CHANNEL="$FAILURE_CHANNEL" FAILURE_LOOKBACK_HOURS="$FAILURE_LOOKBACK_HOURS" \
    FAILURE_LIMIT="$FAILURE_LIMIT" DRY_RUN="$dry_run" FORCE="$force" \
    python3 - <<'PY'
import json
import os

payload = {
    "channel": os.environ["FAILURE_CHANNEL"],
    "lookback_hours": int(os.environ["FAILURE_LOOKBACK_HOURS"]),
    "limit": int(os.environ["FAILURE_LIMIT"]),
    "dry_run": os.environ["DRY_RUN"] == "true",
    "force": os.environ["FORCE"] == "true",
}
print(json.dumps(payload, ensure_ascii=False))
PY
}

try_primary_routes() {
  local payload
  payload="$(build_failure_payload)"

  local endpoints=(
    "/api/v1/reports/failures/send"
    "/api/v1/reports/failure/send"
    "/api/v1/reports/failure-alerts/send"
  )

  local path
  for path in "${endpoints[@]}"; do
    api_post "$path" "$payload"
    if [[ "$HTTP_STATUS" -ge 200 && "$HTTP_STATUS" -lt 300 ]]; then
      log "Primary route succeeded: ${path}"
      log "Response: ${HTTP_BODY}"
      return 0
    fi

    if [[ "$HTTP_STATUS" == "404" || "$HTTP_STATUS" == "405" ]]; then
      log "Primary route unavailable: ${path} (status=${HTTP_STATUS})"
      continue
    fi

    fail "Primary route failed: ${path}, status=${HTTP_STATUS}, body=${HTTP_BODY}"
  done

  return 1
}

build_fallback_payload() {
  FAILURE_LOOKBACK_HOURS="$FAILURE_LOOKBACK_HOURS" FAILURE_TO_EMAIL="$FAILURE_TO_EMAIL" \
    python3 - <<'PY'
import json
import os
import sys
from datetime import datetime, timedelta, timezone

raw = sys.stdin.read()
try:
    payload = json.loads(raw or "[]")
except json.JSONDecodeError:
    payload = []

if not isinstance(payload, list):
    payload = []

lookback_hours = int(os.environ.get("FAILURE_LOOKBACK_HOURS", "24"))
cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

def parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

selected = []
for item in payload:
    if not isinstance(item, dict):
        continue
    ts = parse_iso(item.get("last_seen_at"))
    if ts is not None and ts < cutoff:
        continue
    selected.append(item)

if not selected:
    print("")
    raise SystemExit(0)

lines = []
for idx, item in enumerate(selected, start=1):
    title = str(item.get("title") or "Untitled video")
    source = str(item.get("source_url") or "")
    job_id = str(item.get("last_job_id") or "")
    last_seen = str(item.get("last_seen_at") or "unknown")
    lines.append(f"{idx}. title={title}")
    lines.append(f"   source_url={source}")
    lines.append(f"   last_job_id={job_id}")
    lines.append(f"   last_seen_at={last_seen}")

subject = f"[Video Digestor] Failure alerts ({len(selected)} items)"
body = "\n".join(
    [
        f"Window: last {lookback_hours} hours",
        f"Failed videos: {len(selected)}",
        "",
        *lines,
    ]
)

result = {
    "subject": subject,
    "body": body,
}
to_email = os.environ.get("FAILURE_TO_EMAIL", "").strip()
if to_email:
    result["to_email"] = to_email

print(json.dumps(result, ensure_ascii=False))
PY
}

fallback_failure_alerts() {
  log "Fallback step 1/2: fetching failed videos."
  api_get "/api/v1/videos?status=failed&limit=${FAILURE_LIMIT}"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "Failed to list failed videos: status=${HTTP_STATUS}, body=${HTTP_BODY}"
  fi

  local payload
  payload="$(build_fallback_payload <<<"$HTTP_BODY")"
  if [[ -z "$payload" ]]; then
    log "No failed videos found in the lookback window."
    exit 0
  fi

  log "Fallback step 2/2: sending summary via /api/v1/notifications/test."
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

  if try_primary_routes; then
    return 0
  fi

  if ! is_truthy "$FAILURE_FALLBACK_ENABLED"; then
    fail "Fallback disabled (FAILURE_FALLBACK_ENABLED=${FAILURE_FALLBACK_ENABLED})."
  fi

  fallback_failure_alerts
}

main "$@"
