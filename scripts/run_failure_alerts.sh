#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="run_failure_alerts"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
# shellcheck source=./scripts/lib/http_api.sh
source "$ROOT_DIR/scripts/lib/http_api.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_BASE_URL_OVERRIDE=""
failure_lookback_hours="24"
failure_limit="20"
failure_channel="email"
failure_dry_run="false"
failure_force="false"
failure_to_email=""
failure_fallback_enabled="1"

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

build_failure_payload() {
  local dry_run force
  dry_run="$(json_bool "$failure_dry_run")"
  force="$(json_bool "$failure_force")"

  python3 - "$failure_channel" "$failure_lookback_hours" "$failure_limit" "$dry_run" "$force" <<'PY'
import json
import sys

payload = {
    "channel": sys.argv[1],
    "lookback_hours": int(sys.argv[2]),
    "limit": int(sys.argv[3]),
    "dry_run": sys.argv[4] == "true",
    "force": sys.argv[5] == "true",
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
      log "Response: $(safe_body_preview "$HTTP_BODY")"
      return 0
    fi

    if [[ "$HTTP_STATUS" == "404" || "$HTTP_STATUS" == "405" ]]; then
      log "Primary route unavailable: ${path} (status=${HTTP_STATUS})"
      continue
    fi

    fail "Primary route failed: ${path}, status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
  done

  return 1
}

build_fallback_payload() {
  python3 - "$failure_lookback_hours" "$failure_to_email" <<'PY'
import json
import sys
from datetime import datetime, timedelta, timezone

raw = sys.stdin.read()
try:
    payload = json.loads(raw or "[]")
except json.JSONDecodeError:
    payload = []

if not isinstance(payload, list):
    payload = []

lookback_hours = int(sys.argv[1])
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
to_email = sys.argv[2].strip()
if to_email:
    result["to_email"] = to_email

print(json.dumps(result, ensure_ascii=False))
PY
}

fallback_failure_alerts() {
  log "Fallback step 1/2: fetching failed videos."
  api_get "/api/v1/videos?status=failed&limit=${failure_limit}"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    fail "Failed to list failed videos: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
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
      --channel) failure_channel="${2:-}"; shift 2 ;;
      --lookback-hours) failure_lookback_hours="${2:-}"; shift 2 ;;
      --limit) failure_limit="${2:-}"; shift 2 ;;
      --dry-run) failure_dry_run="${2:-}"; shift 2 ;;
      --force) failure_force="${2:-}"; shift 2 ;;
      --to-email) failure_to_email="${2:-}"; shift 2 ;;
      --fallback-enabled) failure_fallback_enabled="${2:-}"; shift 2 ;;
      -h|--help)
        cat <<'USAGE'
Usage: scripts/run_failure_alerts.sh [options]
  --api-base-url <url>
  --channel <name>
  --lookback-hours <int>
  --limit <int>
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

  if try_primary_routes; then
    return 0
  fi

  if ! is_truthy "$failure_fallback_enabled"; then
    fail "Fallback disabled (--fallback-enabled=${failure_fallback_enabled})."
  fi

  fallback_failure_alerts
}

main "$@"
