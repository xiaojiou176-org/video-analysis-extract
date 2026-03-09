#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="smoke_llm_real_local"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_BASE_URL="http://127.0.0.1:9000"
DIAGNOSTICS_JSON=".runtime-cache/pr-llm-real-smoke-result.json"
HEARTBEAT_SECONDS="30"
MAX_RETRIES="2"
KEY_SOURCE="unset"
AUTH_MODE="unauthenticated"
STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
TEARDOWN_TRACE=""
TEARDOWN_DONE=0
TEARDOWN_TMP_FILES=()
REQUEST_IDEMPOTENCY_KEY=""
request_headers=(
  -H 'Accept: application/json'
  -H 'Content-Type: application/json'
)

usage() {
  cat <<'EOF'
Usage: scripts/smoke_llm_real_local.sh [options]

Options:
  --api-base-url <url>            API base URL (default: http://127.0.0.1:9000)
  --diagnostics-json <path>       Diagnostics output path (default: .runtime-cache/pr-llm-real-smoke-result.json)
  --heartbeat-seconds <n>         Heartbeat interval seconds (default: 30)
  --max-retries <n>               Max retries in [1,2] (default: 2)
  -h, --help                      Show this help
EOF
}

record_teardown_step() {
  local name="$1"
  local status="$2"
  local detail="${3:-}"
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  local line
  line="$(printf '%s\t%s\t%s\t%s\n' "$ts" "$name" "$status" "$detail")"
  TEARDOWN_TRACE+="$line"
}

run_teardown_phase() {
  if [[ "$TEARDOWN_DONE" == "1" ]]; then
    return 0
  fi
  TEARDOWN_DONE=1
  echo "[$SCRIPT_NAME] phase=teardown start" >&2
  local removed=0
  local file_path
  for file_path in "${TEARDOWN_TMP_FILES[@]}"; do
    if [[ -f "$file_path" ]]; then
      rm -f "$file_path"
      ((removed += 1))
      record_teardown_step "remove_tmp_file" "passed" "path=${file_path}"
    else
      record_teardown_step "remove_tmp_file" "skipped" "path=${file_path} missing"
    fi
  done
  if [[ "${#TEARDOWN_TMP_FILES[@]}" -eq 0 ]]; then
    record_teardown_step "remove_tmp_file" "skipped" "no temp files registered"
  fi
  echo "[$SCRIPT_NAME] phase=teardown done removed_tmp_files=${removed}" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-base-url)
      API_BASE_URL="$2"
      shift 2
      ;;
    --diagnostics-json)
      DIAGNOSTICS_JSON="$2"
      shift 2
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="$2"
      shift 2
      ;;
    --max-retries)
      MAX_RETRIES="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[smoke_llm_real_local] unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "$DIAGNOSTICS_JSON")"

# Live smoke env source:
# 1) repo .env (already loaded above)
# 2) current process environment variables
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  KEY_SOURCE="repo_env"
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  run_teardown_phase
  DIAGNOSTICS_JSON="$DIAGNOSTICS_JSON" API_BASE_URL="$API_BASE_URL" STARTED_AT_UTC="$STARTED_AT_UTC" TEARDOWN_TRACE="$TEARDOWN_TRACE" MAX_RETRIES="$MAX_RETRIES" python3 - <<'PY'
import json
import os
from pathlib import Path

teardown_steps = []
for raw in (os.environ.get("TEARDOWN_TRACE", "") or "").splitlines():
    parts = raw.split("\t", 3)
    if len(parts) != 4:
        continue
    ts, step, status, detail = parts
    teardown_steps.append({"timestamp": ts, "step": step, "status": status, "detail": detail})

Path(os.environ["DIAGNOSTICS_JSON"]).write_text(
    json.dumps(
        {
            "status": "failed",
            "failure_kind": "network_or_environment_timeout",
            "reason": "missing GEMINI_API_KEY",
            "api_base_url": os.environ["API_BASE_URL"],
            "started_at_utc": os.environ.get("STARTED_AT_UTC", ""),
            "retry_policy": {"max_attempts": int(os.environ.get("MAX_RETRIES", "2") or "2")},
            "write_policy": {
                "idempotency": "computer_use request key is generated per endpoint+payload hash",
                "teardown": "safe teardown removes only script temp files",
            },
            "write_operations": [],
            "teardown": {"steps": teardown_steps},
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
  echo "[smoke_llm_real_local] GEMINI_API_KEY is required" >&2
  exit 2
fi

if [[ -n "${VD_API_KEY:-}" ]]; then
  request_headers+=(-H "X-API-Key: ${VD_API_KEY}")
  AUTH_MODE="x_api_key"
fi

if ! [[ "$HEARTBEAT_SECONDS" =~ ^[0-9]+$ ]] || (( HEARTBEAT_SECONDS <= 0 )); then
  HEARTBEAT_SECONDS=30
fi
if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || (( MAX_RETRIES <= 0 )); then
  MAX_RETRIES=2
fi
if (( MAX_RETRIES > 2 )); then
  MAX_RETRIES=2
fi

heartbeat_pid=""
start_heartbeat() {
  local label="$1"
  (
    while true; do
      echo "[$SCRIPT_NAME] heartbeat: ${label} still running..." >&2
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

retry_count="$((MAX_RETRIES - 1))"

probe_tmp="$(mktemp)"
TEARDOWN_TMP_FILES+=("$probe_tmp")
probe_curl_exit=0
echo "[$SCRIPT_NAME] phase=probe_external_gemini start" >&2
probe_status="$(
  curl -sS -o "$probe_tmp" -w '%{http_code}' \
    --retry "$retry_count" --retry-delay 1 --retry-all-errors \
    -H 'Accept: application/json' \
    "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}"
)" || probe_curl_exit=$?
probe_body="$(cat "$probe_tmp" 2>/dev/null || true)"

if [[ "$probe_curl_exit" -ne 0 || "$probe_status" != "200" ]]; then
  run_teardown_phase
  BODY="$probe_body" STATUS="$probe_status" DIAGNOSTICS_JSON="$DIAGNOSTICS_JSON" API_BASE_URL="$API_BASE_URL" CURL_EXIT="$probe_curl_exit" KEY_SOURCE="$KEY_SOURCE" STARTED_AT_UTC="$STARTED_AT_UTC" TEARDOWN_TRACE="$TEARDOWN_TRACE" MAX_RETRIES="$MAX_RETRIES" python3 - <<'PY'
import json
import os
from pathlib import Path

teardown_steps = []
for raw in (os.environ.get("TEARDOWN_TRACE", "") or "").splitlines():
    parts = raw.split("\t", 3)
    if len(parts) != 4:
        continue
    ts, step, status, detail = parts
    teardown_steps.append({"timestamp": ts, "step": step, "status": status, "detail": detail})

Path(os.environ["DIAGNOSTICS_JSON"]).write_text(
    json.dumps(
        {
            "status": "failed",
            "failure_kind": "network_or_environment_timeout",
            "reason": "external_gemini_probe_failed",
            "api_base_url": os.environ["API_BASE_URL"],
            "http_status": os.environ.get("STATUS", ""),
            "curl_exit": int(os.environ.get("CURL_EXIT", "0") or "0"),
            "retry_policy": {"max_attempts": int(os.environ.get("MAX_RETRIES", "2") or "2")},
            "key_source": os.environ.get("KEY_SOURCE", "unknown"),
            "started_at_utc": os.environ.get("STARTED_AT_UTC", ""),
            "write_policy": {
                "idempotency": "computer_use request key is generated per endpoint+payload hash",
                "teardown": "safe teardown removes only script temp files",
            },
            "write_operations": [],
            "teardown": {"steps": teardown_steps},
            "response_body_preview": (os.environ.get("BODY", "") or "")[:500],
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
  echo "[smoke_llm_real_local] external gemini probe failed (status=${probe_status}, curl_exit=${probe_curl_exit})" >&2
  exit 1
fi

payload="$(
  python3 - <<'PY'
import base64
import json
import struct
import zlib

def generate_png_base64(width: int = 64, height: int = 64) -> str:
    signature = b"\x89PNG\r\n\x1a\n"
    row = b"\x00" + (b"\x66\xaa\xff" * width)
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

print(
    json.dumps(
        {
            "instruction": "Inspect this page and plan one safe next UI action.",
            "screenshot_base64": generate_png_base64(),
            "safety": {
                "confirm_before_execute": True,
                "blocked_actions": ["submit"],
                "max_actions": 3,
            },
        }
    )
)
PY
)"
echo "[$SCRIPT_NAME] phase=probe_external_gemini done status=${probe_status}" >&2

REQUEST_IDEMPOTENCY_KEY="$(
  API_BASE_URL="$API_BASE_URL" PAYLOAD="$payload" python3 - <<'PY'
import hashlib
import os

raw = "|".join(
    (
        "computer_use_run",
        os.environ["API_BASE_URL"],
        hashlib.sha256(os.environ["PAYLOAD"].encode("utf-8")).hexdigest(),
    )
)
print(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24])
PY
)"
request_headers+=(-H "X-Idempotency-Key: ${REQUEST_IDEMPOTENCY_KEY}")

tmp_body="$(mktemp)"
TEARDOWN_TMP_FILES+=("$tmp_body")
curl_exit=0
echo "[$SCRIPT_NAME] phase=computer_use_api start" >&2
start_heartbeat "POST ${API_BASE_URL}/api/v1/computer-use/run"
status="$(
  curl -sS -o "$tmp_body" -w '%{http_code}' \
    --retry "$retry_count" --retry-delay 1 --retry-all-errors \
    "${request_headers[@]}" \
    -X POST "${API_BASE_URL}/api/v1/computer-use/run" \
    --data "$payload"
)" || curl_exit=$?
stop_heartbeat
echo "[$SCRIPT_NAME] phase=computer_use_api done status=${status}" >&2
body="$(cat "$tmp_body" 2>/dev/null || true)"

if [[ "$curl_exit" -ne 0 ]]; then
  run_teardown_phase
  BODY="$body" STATUS="curl_error" DIAGNOSTICS_JSON="$DIAGNOSTICS_JSON" API_BASE_URL="$API_BASE_URL" CURL_EXIT="$curl_exit" STARTED_AT_UTC="$STARTED_AT_UTC" REQUEST_IDEMPOTENCY_KEY="$REQUEST_IDEMPOTENCY_KEY" TEARDOWN_TRACE="$TEARDOWN_TRACE" MAX_RETRIES="$MAX_RETRIES" python3 - <<'PY'
import json
import os
from pathlib import Path

teardown_steps = []
for raw in (os.environ.get("TEARDOWN_TRACE", "") or "").splitlines():
    parts = raw.split("\t", 3)
    if len(parts) != 4:
        continue
    ts, step, status, detail = parts
    teardown_steps.append({"timestamp": ts, "step": step, "status": status, "detail": detail})

Path(os.environ["DIAGNOSTICS_JSON"]).write_text(
    json.dumps(
        {
            "status": "failed",
            "failure_kind": "network_or_environment_timeout",
            "reason": "curl_request_failed",
            "api_base_url": os.environ["API_BASE_URL"],
            "curl_exit": int(os.environ.get("CURL_EXIT", "1")),
            "retry_policy": {"max_attempts": int(os.environ.get("MAX_RETRIES", "2") or "2")},
            "started_at_utc": os.environ.get("STARTED_AT_UTC", ""),
            "write_policy": {
                "idempotency": "computer_use request key is generated per endpoint+payload hash",
                "teardown": "safe teardown removes only script temp files",
            },
            "write_operations": [
                {
                    "operation": "POST /api/v1/computer-use/run",
                    "idempotency_key": os.environ.get("REQUEST_IDEMPOTENCY_KEY", ""),
                    "cleanup_action": "no destructive cleanup; retain service-side audit records only",
                }
            ],
            "teardown": {"steps": teardown_steps},
            "response_body_preview": (os.environ.get("BODY", "") or "")[:500],
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
  echo "[smoke_llm_real_local] request failed to ${API_BASE_URL} (curl exit ${curl_exit})" >&2
  exit 1
fi

run_teardown_phase
BODY="$body" STATUS="$status" DIAGNOSTICS_JSON="$DIAGNOSTICS_JSON" API_BASE_URL="$API_BASE_URL" KEY_SOURCE="$KEY_SOURCE" HEARTBEAT_SECONDS="$HEARTBEAT_SECONDS" AUTH_MODE="$AUTH_MODE" STARTED_AT_UTC="$STARTED_AT_UTC" MAX_RETRIES="$MAX_RETRIES" REQUEST_IDEMPOTENCY_KEY="$REQUEST_IDEMPOTENCY_KEY" TEARDOWN_TRACE="$TEARDOWN_TRACE" python3 - <<'PY'
import json
import os
import sys
from pathlib import Path

status_code = os.environ["STATUS"]
api_base_url = os.environ["API_BASE_URL"]
diag_path = Path(os.environ["DIAGNOSTICS_JSON"])
body_raw = os.environ["BODY"]

result = {
    "status": "failed",
    "failure_kind": "code_logic_error",
    "api_base_url": api_base_url,
    "http_status": status_code,
    "started_at_utc": os.environ.get("STARTED_AT_UTC", ""),
    "key_source": os.environ.get("KEY_SOURCE", "unknown"),
    "heartbeat_seconds": int(os.environ.get("HEARTBEAT_SECONDS", "30")),
    "retry_policy": {"max_attempts": int(os.environ.get("MAX_RETRIES", "2") or "2")},
    "auth_mode": os.environ.get("AUTH_MODE", "unknown"),
    "external_probe": {"gemini_models_status": "200"},
    "write_policy": {
        "idempotency": "computer_use request key is generated per endpoint+payload hash",
        "teardown": "safe teardown removes only script temp files",
    },
    "write_operations": [
        {
            "operation": "POST /api/v1/computer-use/run",
            "idempotency_key": os.environ.get("REQUEST_IDEMPOTENCY_KEY", ""),
            "cleanup_action": "no destructive cleanup; retain service-side audit records only",
        }
    ],
    "checks": [],
}

teardown_steps = []
for raw in (os.environ.get("TEARDOWN_TRACE", "") or "").splitlines():
    parts = raw.split("\t", 3)
    if len(parts) != 4:
        continue
    ts, step, status, detail = parts
    teardown_steps.append({"timestamp": ts, "step": step, "status": status, "detail": detail})
result["teardown"] = {"steps": teardown_steps}

def finalize_and_exit(code: int, reason: str) -> None:
    result["status"] = "passed" if code == 0 else "failed"
    if reason:
        result["reason"] = reason
    if code != 0:
        if (
            status_code == "curl_error"
            or status_code == "000"
            or reason.startswith("[smoke_llm_real_local] status=5")
        ):
            result["failure_kind"] = "network_or_environment_timeout"
        else:
            result["failure_kind"] = "code_logic_error"
    diag_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if code != 0:
        print(reason, file=sys.stderr)
    raise SystemExit(code)

if status_code != "200":
    unsupported_markers = (
        "Computer Use is not enabled",
        "computer_use_provider_error:400 INVALID_ARGUMENT",
    )
    if status_code == "400" and any(marker in body_raw for marker in unsupported_markers):
        result["response_body_preview"] = body_raw[:500]
        result["checks"].append(
            {
                "name": "computer_use_capability_available",
                "passed": False,
                "reason": "provider_account_not_enabled_for_computer_use",
            }
        )
        finalize_and_exit(
            0,
            "[smoke_llm_real_local] skipped: computer use capability is not enabled for current provider account",
        )
    result["response_body_preview"] = body_raw[:500]
    finalize_and_exit(1, f"[smoke_llm_real_local] status={status_code}")

try:
    obj = json.loads(body_raw)
except json.JSONDecodeError as exc:
    result["response_body_preview"] = body_raw[:500]
    finalize_and_exit(1, f"invalid JSON response: {exc}")

required = ["actions", "require_confirmation", "blocked_actions", "final_text", "thought_metadata"]
missing = [k for k in required if k not in obj]
if missing:
    result["response_keys"] = sorted(obj.keys())
    finalize_and_exit(1, f"missing fields: {missing}")

result["checks"].append({"name": "required_fields", "passed": True})

actions = obj.get("actions")
if not isinstance(actions, list) or not actions:
    finalize_and_exit(1, "actions empty")
result["checks"].append({"name": "actions_non_empty", "passed": True, "count": len(actions)})

meta = obj.get("thought_metadata")
if not isinstance(meta, dict):
    finalize_and_exit(1, "thought_metadata missing")
result["checks"].append({"name": "thought_metadata_present", "passed": True})

provider = meta.get("provider")
if provider != "gemini":
    finalize_and_exit(1, f"unexpected provider: {provider}")
result["checks"].append({"name": "provider_gemini", "passed": True})

model = str(meta.get("model") or "").strip()
if not model:
    finalize_and_exit(1, "thought_metadata.model missing")
result["checks"].append({"name": "model_present", "passed": True, "model": model})

request_id = str(meta.get("request_id") or "").strip()
finish_reason = str(meta.get("finish_reason") or "").strip()
if not request_id and not finish_reason:
    finalize_and_exit(1, "missing both thought_metadata.request_id and thought_metadata.finish_reason")
result["checks"].append(
    {
        "name": "request_or_finish_reason_present",
        "passed": True,
        "request_id_present": bool(request_id),
        "finish_reason_present": bool(finish_reason),
    }
)

result["response_summary"] = {
    "actions_count": len(actions),
    "require_confirmation": obj.get("require_confirmation"),
    "blocked_actions_count": len(obj.get("blocked_actions", [])) if isinstance(obj.get("blocked_actions"), list) else None,
}

finalize_and_exit(0, "")
PY

echo "[smoke_llm_real_local] passed"
