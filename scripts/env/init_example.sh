#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="init_env_example"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

OUTPUT_PATH="$ROOT_DIR/.env.generated.example"
INIT_ENV_FORCE=0
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
    fail "output exists: $OUTPUT_PATH (use --force to overwrite)"
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
[${SCRIPT_NAME}]   1) cp "$OUTPUT_PATH" "$ROOT_DIR/.env"
[${SCRIPT_NAME}]   2) edit "$ROOT_DIR/.env" and fill RESEND_* values
[${SCRIPT_NAME}]   3) source "$ROOT_DIR/.env"
[${SCRIPT_NAME}]   4) if needed, export temporary overrides in current shell
[${SCRIPT_NAME}]   5) run scripts/runtime/run_daily_digest.sh or scripts/runtime/run_failure_alerts.sh
EOF
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output)
        if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
          fail "--output requires a non-empty path"
        fi
        OUTPUT_PATH="$2"
        shift 2
        ;;
      --force)
        INIT_ENV_FORCE=1
        shift
        ;;
      -h|--help)
        cat <<EOF
Usage: ./scripts/env/init_example.sh [--output <path>] [--force]

Options:
  --output <path>  Output file path (default: $ROOT_DIR/.env.generated.example)
  --force          Overwrite existing output file
  -h, --help       Show this help
EOF
        exit 0
        ;;
      *)
        fail "unknown argument: $1"
        ;;
    esac
  done

  write_example_env
  print_next_steps
}

main "$@"
