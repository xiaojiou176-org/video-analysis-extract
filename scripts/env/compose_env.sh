#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="compose_env"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"
WRITE_PATH=""
PROFILE_INPUT="${ENV_PROFILE:-local}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/env/compose_env.sh [--profile <name>] [--write <path>]

Compose effective env by order:
  env/core.env (or env/core.env.example)
  env/profiles/<profile>.env
  .env
  shell overrides (highest priority)

Examples:
  bash scripts/env/compose_env.sh --profile local
  bash scripts/env/compose_env.sh --profile local --write .runtime-cache/tmp/.env.local.resolved
USAGE
}

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
die() { printf '[%s] error: %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      [[ $# -ge 2 ]] || die "missing value for $1"
      ENV_PROFILE="${2:-}"
      PROFILE_INPUT="$ENV_PROFILE"
      shift 2
      ;;
    --write)
      [[ $# -ge 2 ]] || die "missing value for --write"
      WRITE_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "error: unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
ENV_PROFILE="$(normalize_env_profile "$ENV_PROFILE")"
if [[ "$PROFILE_INPUT" != "$ENV_PROFILE" ]]; then
  log "warning: profile '$PROFILE_INPUT' normalized to '$ENV_PROFILE' (allowed chars: A-Za-z0-9._-)."
fi
log "composing env for profile=$ENV_PROFILE"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"

ENV_FILES=()
while IFS= read -r env_file; do
  [[ -z "$env_file" ]] && continue
  ENV_FILES+=("$env_file")
done < <(get_repo_env_files "$ROOT_DIR" "$ENV_PROFILE")

if (( ${#ENV_FILES[@]} == 0 )); then
  log "no env files discovered for profile=$ENV_PROFILE, nothing to compose."
  log "hint: expected one or more of env/core.env(.example), env/profiles/${ENV_PROFILE}.env, .env"
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
  log "wrote resolved env: $WRITE_PATH"
fi

cat "$TMP_OUT"
resolved_keys="$(wc -l < "$TMP_OUT" | tr -d '[:space:]')"
log "summary: profile=$ENV_PROFILE, files=${#ENV_FILES[@]}, resolved_keys=${resolved_keys:-0}"
rm -f "$TMP_OUT"
