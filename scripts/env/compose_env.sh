#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="compose_env"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"
WRITE_PATH=""

usage() {
  cat <<'USAGE'
Usage: bash scripts/env/compose_env.sh [--profile <name>] [--write <path>]

Compose effective env by order:
  env/core.env (or env/core.env.example)
  env/profiles/<profile>.env
  .env
  shell overrides (highest priority)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    --write)
      WRITE_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf '[%s] unknown argument: %s\n' "$SCRIPT_NAME" "$1" >&2
      usage
      exit 1
      ;;
  esac
done

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
ENV_PROFILE="$(normalize_env_profile "$ENV_PROFILE")"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"

ENV_FILES=()
while IFS= read -r env_file; do
  [[ -z "$env_file" ]] && continue
  ENV_FILES+=("$env_file")
done < <(get_repo_env_files "$ROOT_DIR" "$ENV_PROFILE")

if (( ${#ENV_FILES[@]} == 0 )); then
  printf '[%s] no env files discovered, nothing to compose.\n' "$SCRIPT_NAME" >&2
  exit 0
fi

TMP_OUT="$(mktemp)"
sed -nE 's/^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=.*/\2/p' "${ENV_FILES[@]}" \
  | awk '!seen[$0]++' \
  | while IFS= read -r key; do
      [[ -z "$key" ]] && continue
      if [[ -n "${!key+x}" ]]; then
        printf '%s=%q\n' "$key" "${!key}" >> "$TMP_OUT"
      fi
    done

if [[ -n "$WRITE_PATH" ]]; then
  mkdir -p "$(dirname "$WRITE_PATH")"
  cp "$TMP_OUT" "$WRITE_PATH"
  printf '[%s] wrote resolved env: %s\n' "$SCRIPT_NAME" "$WRITE_PATH" >&2
fi

cat "$TMP_OUT"
rm -f "$TMP_OUT"
