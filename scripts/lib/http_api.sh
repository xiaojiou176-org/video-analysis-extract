#!/usr/bin/env bash

http_api_log() {
  if declare -F log >/dev/null 2>&1; then
    log "$*"
    return 0
  fi
  printf '[http_api] %s\n' "$*" >&2
}

http_api_fail() {
  if declare -F fail >/dev/null 2>&1; then
    fail "$*"
    return 1
  fi
  printf '[http_api] ERROR: %s\n' "$*" >&2
  exit 1
}

resolve_http_api_base_url() {
  local cli_value="${1:-}"
  local root_dir="${2:-${ROOT_DIR:-}}"
  local default_value="http://127.0.0.1:9000"

  if [[ -n "$cli_value" ]]; then
    printf '%s\n' "$cli_value"
    return 0
  fi

  if declare -F resolve_runtime_route_value >/dev/null 2>&1 && [[ -n "$root_dir" ]]; then
    resolve_runtime_route_value "$root_dir" "VD_API_BASE_URL" "" "$default_value"
    return 0
  fi

  if [[ -n "${VD_API_BASE_URL:-}" ]]; then
    printf '%s\n' "$VD_API_BASE_URL"
    return 0
  fi

  printf '%s\n' "$default_value"
}

apply_http_api_base_url() {
  local cli_value="${1:-}"
  local root_dir="${2:-${ROOT_DIR:-}}"
  export VD_API_BASE_URL
  VD_API_BASE_URL="$(resolve_http_api_base_url "$cli_value" "$root_dir")"
  export HTTP_API_BASE_URL_OVERRIDE="$VD_API_BASE_URL"
}

http_api_auth_args() {
  local -a args=()
  if [[ -n "${VD_API_KEY:-}" ]]; then
    args+=(-H "X-API-Key: ${VD_API_KEY}")
  fi
  if [[ -n "${WEB_ACTION_SESSION_TOKEN:-}" ]]; then
    args+=(-H "X-Web-Session: ${WEB_ACTION_SESSION_TOKEN}")
  fi
  printf '%s\0' "${args[@]}"
}

safe_body_preview() {
  BODY="${1:-}" python3 - <<'PY'
import os
import re

text = os.environ.get("BODY", "")
rules = [
    (r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer ***REDACTED***"),
    (r"(sk-[A-Za-z0-9]{20,})", "sk-***REDACTED***"),
    (r"(ghp_[A-Za-z0-9]{20,})", "ghp_***REDACTED***"),
    (r"(AKIA[0-9A-Z]{16})", "AKIA***REDACTED***"),
    (
        r"([?&](?:api[_-]?key|apikey|key|token|secret|password|auth(?:orization)?)=)[^&\\s]+",
        r"\1***REDACTED***",
    ),
]
for pattern, replacement in rules:
    text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
limit = 400
if len(text) > limit:
    text = text[:limit] + "...[truncated]"
print(text)
PY
}

api_get() {
  local path="$1"
  local tmp_body
  tmp_body="$(mktemp)"

  local base_url status
  base_url="$(resolve_http_api_base_url "${HTTP_API_BASE_URL_OVERRIDE:-${VD_API_BASE_URL:-}}" "${ROOT_DIR:-}")"
  local -a auth_args=()
  local auth_part
  while IFS= read -r -d '' auth_part; do
    auth_args+=("$auth_part")
  done < <(http_api_auth_args)
  if ! status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      "${auth_args[@]}" \
      "${base_url}${path}"
  )"; then
    rm -f "$tmp_body"
    http_api_fail "GET ${path} failed (network error)"
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

  local base_url status
  base_url="$(resolve_http_api_base_url "${HTTP_API_BASE_URL_OVERRIDE:-${VD_API_BASE_URL:-}}" "${ROOT_DIR:-}")"
  local -a auth_args=()
  local auth_part
  while IFS= read -r -d '' auth_part; do
    auth_args+=("$auth_part")
  done < <(http_api_auth_args)
  if ! status="$(
    curl -sS -o "$tmp_body" -w '%{http_code}' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      "${auth_args[@]}" \
      -X POST "${base_url}${path}" \
      --data "$payload"
  )"; then
    rm -f "$tmp_body"
    http_api_fail "POST ${path} failed (network error)"
  fi

  HTTP_STATUS="$status"
  HTTP_BODY="$(cat "$tmp_body")"
  rm -f "$tmp_body"
}

check_api_health() {
  api_get "/healthz"
  if [[ "$HTTP_STATUS" -lt 200 || "$HTTP_STATUS" -ge 300 ]]; then
    http_api_fail "API health check failed: status=${HTTP_STATUS}, body=$(safe_body_preview "$HTTP_BODY")"
  fi
  http_api_log "API reachable: $(resolve_http_api_base_url "${HTTP_API_BASE_URL_OVERRIDE:-${VD_API_BASE_URL:-}}" "${ROOT_DIR:-}")"
}
