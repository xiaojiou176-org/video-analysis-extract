#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="validate_profile"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"
PROFILE_INPUT="${ENV_PROFILE:-local}"
WORKSPACE_HYGIENE="$ROOT_DIR/scripts/runtime/workspace_hygiene.sh"

usage() {
  cat <<'USAGE'
Usage: bash scripts/env/validate_profile.sh [--profile <name>]

Validate profile composition and write resolved snapshot:
  .runtime-cache/tmp/.env.<profile>.resolved

Examples:
  bash scripts/env/validate_profile.sh --profile local
  bash scripts/env/validate_profile.sh --profile gce
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

PROFILE_FILE="$ROOT_DIR/env/profiles/${ENV_PROFILE}.env"
if [[ ! -f "$PROFILE_FILE" ]]; then
  available_profiles="$(ls "$ROOT_DIR/env/profiles"/*.env 2>/dev/null | xargs -n1 basename 2>/dev/null | sed 's/\.env$//' | tr '\n' ' ' || true)"
  log "error: missing profile file: $PROFILE_FILE"
  log "hint: available profiles: ${available_profiles:-none}"
  log "hint: run 'bash scripts/env/validate_profile.sh --help' for usage."
  exit 1
fi

if ! bash "$WORKSPACE_HYGIENE" >/dev/null 2>&1; then
  log "error: forbidden workspace runtime residue detected"
  log "hint: run './bin/workspace-hygiene --apply' before validate-profile."
  exit 1
fi

ENV_FILES=()
while IFS= read -r env_file; do
  [[ -z "$env_file" ]] && continue
  ENV_FILES+=("$env_file")
done < <(get_repo_env_files "$ROOT_DIR" "$ENV_PROFILE")
if (( ${#ENV_FILES[@]} == 0 )); then
  log "error: no env files discovered for profile=$ENV_PROFILE"
  log "hint: expected one or more of env/core.env(.example), env/profiles/${ENV_PROFILE}.env, .env"
  exit 1
fi

RESOLVED_PATH="$ROOT_DIR/.runtime-cache/tmp/.env.${ENV_PROFILE}.resolved"
log "heartbeat: composing effective env for profile=$ENV_PROFILE"
if ! bash "$ROOT_DIR/scripts/env/compose_env.sh" --profile "$ENV_PROFILE" --write "$RESOLVED_PATH" >/dev/null; then
  log "error: compose failed for profile=$ENV_PROFILE"
  log "hint: run 'bash scripts/env/compose_env.sh --profile $ENV_PROFILE' to inspect unresolved variables."
  exit 1
fi

if [[ ! -s "$RESOLVED_PATH" ]]; then
  log "error: resolved env is empty: $RESOLVED_PATH"
  log "hint: ensure .env and profile files contain KEY=value pairs."
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  log "risk hint: .env is missing; validation passed with available files only."
fi

resolved_keys="$(wc -l < "$RESOLVED_PATH" | tr -d '[:space:]')"
log "profile=$ENV_PROFILE validated"
log "summary: files=${#ENV_FILES[@]}, resolved_keys=${resolved_keys:-0}"
log "files=${ENV_FILES[*]}"
log "resolved=$RESOLVED_PATH"
