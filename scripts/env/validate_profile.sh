#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="validate_profile"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/env/validate_profile.sh [--profile <name>]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
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

PROFILE_FILE="$ROOT_DIR/env/profiles/${ENV_PROFILE}.env"
if [[ ! -f "$PROFILE_FILE" ]]; then
  printf '[%s] missing profile file: %s\n' "$SCRIPT_NAME" "$PROFILE_FILE" >&2
  exit 1
fi

ENV_FILES=()
while IFS= read -r env_file; do
  [[ -z "$env_file" ]] && continue
  ENV_FILES+=("$env_file")
done < <(get_repo_env_files "$ROOT_DIR" "$ENV_PROFILE")
if (( ${#ENV_FILES[@]} == 0 )); then
  printf '[%s] no env files discovered for profile=%s\n' "$SCRIPT_NAME" "$ENV_PROFILE" >&2
  exit 1
fi

RESOLVED_PATH="$ROOT_DIR/.runtime-cache/temp/.env.${ENV_PROFILE}.resolved"
bash "$ROOT_DIR/scripts/env/compose_env.sh" --profile "$ENV_PROFILE" --write "$RESOLVED_PATH" >/dev/null

if [[ ! -s "$RESOLVED_PATH" ]]; then
  printf '[%s] resolved env is empty: %s\n' "$SCRIPT_NAME" "$RESOLVED_PATH" >&2
  exit 1
fi

printf '[%s] profile=%s validated\n' "$SCRIPT_NAME" "$ENV_PROFILE" >&2
printf '[%s] files=%s\n' "$SCRIPT_NAME" "${ENV_FILES[*]}" >&2
printf '[%s] resolved=%s\n' "$SCRIPT_NAME" "$RESOLVED_PATH" >&2
