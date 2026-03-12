#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="smoke_computer_use_local"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_BASE_URL="http://127.0.0.1:9000"
RETRIES="2"
HEARTBEAT_SECONDS="30"
ALLOW_UNSUPPORTED_SKIP="0"
heartbeat_pid=""
TMP_FILES=()

if [[ -z "${VD_API_KEY:-}" && -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  export VD_API_KEY="video-digestor-local-dev-token"
fi

log() {
  printf '[smoke_computer_use_local] %s\n' "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

start_heartbeat() {
  (
    while true; do
      log "heartbeat: computer-use request still running..."
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

run_teardown() {
  stop_heartbeat
  local file_path
  if (( ${#TMP_FILES[@]} > 0 )); then
    for file_path in "${TMP_FILES[@]}"; do
      [[ -f "$file_path" ]] && rm -f "$file_path"
    done
  fi
}
trap run_teardown EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    --retries)
      RETRIES="$2"
      shift 2
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="$2"
      shift 2
      ;;
    --allow-unsupported-skip)
      ALLOW_UNSUPPORTED_SKIP="$2"
      shift 2
      ;;
    *)
      log "unknown arg: $1"
      exit 2
      ;;
  esac
done

[[ "$RETRIES" =~ ^[0-9]+$ ]] || fail "--retries must be a positive integer"
(( RETRIES > 0 )) || fail "--retries must be > 0"
(( RETRIES <= 2 )) || fail "--retries must be <= 2 for live smoke policy"
[[ "$HEARTBEAT_SECONDS" =~ ^[0-9]+$ ]] || fail "--heartbeat-seconds must be a positive integer"
(( HEARTBEAT_SECONDS > 0 )) || fail "--heartbeat-seconds must be > 0"
[[ "$ALLOW_UNSUPPORTED_SKIP" =~ ^[01]$ ]] || fail "--allow-unsupported-skip must be 0 or 1"

payload="$(
  python3 - <<'PY'
import base64
import json
import struct
import zlib

def generate_png_base64(width: int = 64, height: int = 64) -> str:
    signature = b"\x89PNG\r\n\x1a\n"
    row = b"\x00" + (b"\x66\xaa\xff" * width)  # filter byte + RGB pixels
    raw = row * height
    compressed = zlib.compress(raw, level=9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", compressed)
    iend = chunk(b"IEND", b"")
    png = signature + ihdr + idat + iend
    return base64.b64encode(png).decode("ascii")

print(json.dumps({
    "instruction": "Open settings and click submit button",
    "screenshot_base64": generate_png_base64(),
    "safety": {
        "confirm_before_execute": True,
        "blocked_actions": ["submit"],
        "max_actions": 5
    }
}))
PY
)"

tmp_body="$(mktemp)"
TMP_FILES+=("$tmp_body")
curl_cmd=(curl -sS -o "$tmp_body" -w '%{http_code}')
if [[ -n "${VD_API_KEY:-}" ]]; then
  curl_cmd+=(-H "X-API-Key: ${VD_API_KEY}")
  curl_cmd+=(-H "Authorization: Bearer ${VD_API_KEY}")
fi
curl_cmd+=(
  --retry "$((RETRIES - 1))" --retry-delay 1 --retry-all-errors
  -H 'Accept: application/json'
  -H 'Content-Type: application/json'
  -X POST "${API_BASE_URL}/api/v1/computer-use/run"
  --data "$payload"
)
start_heartbeat
curl_exit=0
status="$("${curl_cmd[@]}")" || curl_exit=$?
stop_heartbeat
body="$(cat "$tmp_body")"

if [[ "$curl_exit" -ne 0 ]]; then
  log "curl request failed: exit=${curl_exit} body=${body}"
  exit 1
fi

if [[ "$status" != "200" ]]; then
  if [[ "$status" == "400" ]] && [[ "$body" == *"Computer Use is not enabled"* || "$body" == *"computer_use_provider_error:400 INVALID_ARGUMENT"* ]]; then
    if [[ "$ALLOW_UNSUPPORTED_SKIP" == "1" ]]; then
      log "result=skipped reason=provider_account_not_enabled_for_computer_use"
      exit 0
    fi
    log "status=${status} body=${body}"
    fail "provider account does not have computer use capability; pass --allow-unsupported-skip=1 to treat this as skip"
  fi
  log "status=${status} body=${body}"
  exit 1
fi

BODY="$body" python3 - <<'PY'
import json, os, sys
obj = json.loads(os.environ["BODY"])
required = ["actions", "require_confirmation", "blocked_actions", "final_text", "thought_metadata"]
missing = [k for k in required if k not in obj]
if missing:
    print(f"missing fields: {missing}", file=sys.stderr)
    sys.exit(1)
if not isinstance(obj["actions"], list) or not obj["actions"]:
    print("actions empty", file=sys.stderr)
    sys.exit(1)
if "provider" not in (obj.get("thought_metadata") or {}):
    print("thought_metadata.provider missing", file=sys.stderr)
    sys.exit(1)
print("[smoke_computer_use_local] result=passed")
PY
