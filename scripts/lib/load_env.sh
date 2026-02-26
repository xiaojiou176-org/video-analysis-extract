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

load_env_files() {
  local caller="${1:-env_loader}"
  shift || true
  local env_path
  for env_path in "$@"; do
    load_env_file "$env_path" "$caller"
  done
}

normalize_env_profile() {
  local profile="${1:-local}"
  if [[ -z "$profile" ]]; then
    printf 'local\n'
    return 0
  fi
  if [[ "$profile" =~ ^[A-Za-z0-9._-]+$ ]]; then
    printf '%s\n' "$profile"
    return 0
  fi
  printf 'local\n'
}

get_repo_env_files() {
  local root_dir="${1:-}"
  local profile="${2:-${ENV_PROFILE:-local}}"
  profile="$(normalize_env_profile "$profile")"

  if [[ -z "$root_dir" ]]; then
    return 0
  fi

  local core_file="$root_dir/env/core.env"
  local core_example_file="$root_dir/env/core.env.example"
  local profile_file="$root_dir/env/profiles/${profile}.env"
  local repo_env_file="$root_dir/.env"

  if [[ -f "$core_file" ]]; then
    printf '%s\n' "$core_file"
  elif [[ -f "$core_example_file" ]]; then
    printf '%s\n' "$core_example_file"
  fi

  if [[ -f "$profile_file" ]]; then
    printf '%s\n' "$profile_file"
  fi

  if [[ -f "$repo_env_file" ]]; then
    printf '%s\n' "$repo_env_file"
  fi
}

load_repo_env() {
  local root_dir="${1:-}"
  local caller="${2:-env_loader}"
  local requested_profile="${3:-${ENV_PROFILE:-local}}"
  local profile
  profile="$(normalize_env_profile "$requested_profile")"

  if [[ -z "$root_dir" ]]; then
    printf '[%s] root_dir is empty, skipping repo env load.\n' "$caller" >&2
    return 0
  fi

  local shell_snapshot
  shell_snapshot="$(mktemp)"
  export -p > "$shell_snapshot"

  local -a env_files=()
  local env_file
  while IFS= read -r env_file; do
    [[ -z "$env_file" ]] && continue
    env_files+=("$env_file")
  done < <(get_repo_env_files "$root_dir" "$profile")

  if (( ${#env_files[@]} > 0 )); then
    load_env_files "$caller" "${env_files[@]}"
  else
    printf '[%s] No env files found under %s (profile=%s), using current shell env only.\n' "$caller" "$root_dir" "$profile" >&2
  fi

  # shell environment has the highest priority.
  # shellcheck disable=SC1090
  source "$shell_snapshot"
  rm -f "$shell_snapshot"

  export ENV_PROFILE="$profile"
}
