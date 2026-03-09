#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_NAME="run_ai_feed_sync"
ENV_PROFILE="${ENV_PROFILE:-local}"
READER_ENV_FILE="$ROOT_DIR/env/profiles/reader.env"
API_BASE_URL_OVERRIDE=""
MINIFLUX_BASE_URL_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: ./scripts/run_ai_feed_sync.sh [options]

Options:
  --profile, --env-profile <name>   Env profile passed to load_repo_env (default: local)
  --reader-env-file <path>          Reader env file used to fill missing reader vars
  --api-base-url <url>              Override VD_API_BASE_URL for this run
  --miniflux-base-url <url>         Override MINIFLUX_BASE_URL for this run
  -h, --help                        Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    --reader-env-file)
      READER_ENV_FILE="${2:-}"
      shift 2
      ;;
    --api-base-url)
      API_BASE_URL_OVERRIDE="${2:-}"
      shift 2
      ;;
    --miniflux-base-url)
      MINIFLUX_BASE_URL_OVERRIDE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[${SCRIPT_NAME}] unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"

resolve_route_value_local() {
  local key="$1"
  local cli_value="$2"
  local default_value="$3"
  if declare -F resolve_runtime_route_value >/dev/null 2>&1; then
    resolve_runtime_route_value "$ROOT_DIR" "$key" "$cli_value" "$default_value"
    return 0
  fi
  if [[ -n "$cli_value" ]]; then
    printf '%s\n' "$cli_value"
    return 0
  fi
  local current_value
  current_value="${!key:-}"
  if [[ -n "$current_value" ]]; then
    printf '%s\n' "$current_value"
    return 0
  fi
  printf '%s\n' "$default_value"
}

export VD_API_BASE_URL
VD_API_BASE_URL="$(resolve_route_value_local "VD_API_BASE_URL" "$API_BASE_URL_OVERRIDE" "http://127.0.0.1:9000")"

if [[ -f "$READER_ENV_FILE" ]]; then
  load_env_file_preserve_process_env "$READER_ENV_FILE" "$SCRIPT_NAME"
fi

if [[ -n "$MINIFLUX_BASE_URL_OVERRIDE" ]]; then
  export MINIFLUX_BASE_URL="$MINIFLUX_BASE_URL_OVERRIDE"
fi

exec python3 "$ROOT_DIR/scripts/sync_ai_feed_to_miniflux.py"
