#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="init_env_example"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

OUTPUT_PATH="${OUTPUT_PATH:-$ROOT_DIR/.env.local.example}"
INIT_ENV_FORCE="${INIT_ENV_FORCE:-0}"
SOURCE_ENV_TEMPLATE="$ROOT_DIR/.env.example"

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

is_truthy() {
  local value
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

write_example_env() {
  if [[ -e "$OUTPUT_PATH" ]] && ! is_truthy "$INIT_ENV_FORCE"; then
    fail "output exists: $OUTPUT_PATH (set INIT_ENV_FORCE=1 to overwrite)"
  fi
  if [[ ! -f "$SOURCE_ENV_TEMPLATE" ]]; then
    fail "source env template not found: $SOURCE_ENV_TEMPLATE"
  fi

  cp "$SOURCE_ENV_TEMPLATE" "$OUTPUT_PATH"

  log "Wrote env template: $OUTPUT_PATH"
}

print_next_steps() {
  cat <<EOF
[${SCRIPT_NAME}] Next steps:
[${SCRIPT_NAME}]   1) cp "$OUTPUT_PATH" "$ROOT_DIR/.env.local"
[${SCRIPT_NAME}]   2) edit "$ROOT_DIR/.env.local" and fill RESEND_* values
[${SCRIPT_NAME}]   3) source "$ROOT_DIR/.env.local"
[${SCRIPT_NAME}]   4) run scripts/run_daily_digest.sh or scripts/run_failure_alerts.sh
EOF
}

main() {
  write_example_env
  print_next_steps
}

main "$@"
