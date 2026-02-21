#!/usr/bin/env bash
set -euo pipefail

load_env_file() {
  local env_path="${1:-}"
  local caller="${2:-env_loader}"

  if [[ -z "$env_path" ]]; then
    printf '[%s] Env file path is empty, skipping.\n' "$caller" >&2
    return 0
  fi

  if [[ -f "$env_path" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_path"
    set +a
    printf '[%s] Loaded env file: %s\n' "$caller" "$env_path" >&2
    return 0
  fi

  printf '[%s] Env file not found, continuing with current shell env: %s\n' "$caller" "$env_path" >&2
}
