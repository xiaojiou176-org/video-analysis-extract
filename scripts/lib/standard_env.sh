#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
eval "$(python3 "$ROOT_DIR/scripts/ci_contract.py" shell-exports)"
STANDARD_ENV_IMAGE="${VD_STANDARD_ENV_IMAGE:-$STRICT_CI_STANDARD_IMAGE_REF}"
STANDARD_ENV_DOCKERFILE="${VD_STANDARD_ENV_DOCKERFILE:-$ROOT_DIR/$STRICT_CI_STANDARD_IMAGE_DOCKERFILE}"
STANDARD_ENV_WORKDIR="${VD_STANDARD_ENV_WORKDIR:-$STRICT_CI_STANDARD_IMAGE_WORKDIR}"
STANDARD_ENV_HOST_GATEWAY="${VD_STANDARD_ENV_HOST_GATEWAY:-host.docker.internal}"
STANDARD_ENV_MARKER_PATH="${VD_STANDARD_ENV_MARKER_PATH:-/etc/video-analysis-extract-strict-ci-standard-env}"
STANDARD_ENV_DOCKERENV_PATH="${VD_STANDARD_ENV_DOCKERENV_PATH:-/.dockerenv}"

is_truthy_env() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

is_running_inside_standard_env() {
  if [[ "${VD_IN_STANDARD_ENV:-0}" == "1" ]]; then
    return 0
  fi

  if [[ -f "$STANDARD_ENV_MARKER_PATH" ]]; then
    return 0
  fi

  # Legacy fallback: CI container jobs in GitHub Actions may run in the strict
  # image without propagating VD_IN_STANDARD_ENV.
  if is_truthy_env "${GITHUB_ACTIONS:-}" && [[ -f "$STANDARD_ENV_DOCKERENV_PATH" ]]; then
    return 0
  fi

  return 1
}

append_standard_env_git_mounts() {
  local -n mounts_ref="$1"
  local git_file="$ROOT_DIR/.git"
  local git_dir=""
  local git_common_dir=""

  if [[ -d "$git_file" ]]; then
    return 0
  fi
  if [[ ! -f "$git_file" ]]; then
    return 0
  fi

  git_dir="$(git -C "$ROOT_DIR" rev-parse --absolute-git-dir 2>/dev/null || true)"
  git_common_dir="$(git -C "$ROOT_DIR" rev-parse --git-common-dir 2>/dev/null || true)"
  [[ -n "$git_dir" ]] || return 0

  if [[ "$git_dir" != "$ROOT_DIR/.git" ]]; then
    mounts_ref+=(-v "$git_dir:$git_dir")
  fi
  if [[ -n "$git_common_dir" ]]; then
    git_common_dir="$(cd "$ROOT_DIR" && python3 - <<'PY' "$git_common_dir"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"
    if [[ "$git_common_dir" != "$ROOT_DIR/.git" && "$git_common_dir" != "$git_dir" ]]; then
      mounts_ref+=(-v "$git_common_dir:$git_common_dir")
    fi
  fi
}

ensure_standard_env_registry_login() {
  local registry="ghcr.io"
  local username="${GHCR_USERNAME:-}"
  local token="${GHCR_TOKEN:-}"

  if [[ -z "$username" || -z "$token" ]]; then
    return 0
  fi

  printf '%s' "$token" | docker login "$registry" -u "$username" --password-stdin >/dev/null
}

standard_env_needs_host_gateway() {
  case "$(uname -s)" in
    Darwin*|MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_standard_env_runtime_value() {
  local key="${1:-}"
  local value="${2:-}"

  if [[ -z "$value" ]] || ! standard_env_needs_host_gateway; then
    printf '%s\n' "$value"
    return 0
  fi

  python3 - "$key" "$value" "$STANDARD_ENV_HOST_GATEWAY" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

key, value, replacement_host = sys.argv[1:4]
loopback_hosts = {"127.0.0.1", "localhost"}

if key == "DATABASE_URL":
    parsed = urlsplit(value)
    if parsed.hostname not in loopback_hosts:
        print(value)
        raise SystemExit(0)
    if parsed.port is None:
        port_suffix = ""
    else:
        port_suffix = f":{parsed.port}"
    auth = ""
    if parsed.username is not None:
        auth = parsed.username
        if parsed.password is not None:
            auth += f":{parsed.password}"
        auth += "@"
    rebuilt = parsed._replace(netloc=f"{auth}{replacement_host}{port_suffix}")
    print(urlunsplit(rebuilt))
    raise SystemExit(0)

if key == "TEMPORAL_TARGET_HOST":
    host, separator, remainder = value.partition(":")
    if host in loopback_hosts and separator:
        print(f"{replacement_host}:{remainder}")
        raise SystemExit(0)

print(value)
PY
}

build_standard_env_image() {
  if [[ "${VD_STANDARD_ENV_FORCE_REBUILD:-0}" != "1" ]] \
    && docker image inspect "${STRICT_CI_STANDARD_IMAGE_REPOSITORY}:local-debug" >/dev/null 2>&1; then
    STANDARD_ENV_IMAGE="${STRICT_CI_STANDARD_IMAGE_REPOSITORY}:local-debug"
    return 0
  fi

  "$ROOT_DIR/scripts/build_ci_standard_image.sh" --load --tag local-debug
  STANDARD_ENV_IMAGE="${STRICT_CI_STANDARD_IMAGE_REPOSITORY}:local-debug"
}

run_in_standard_env() {
  local command=("$@")
  local runtime_database_url runtime_temporal_target_host
  local extra_mounts=()

  runtime_database_url="$(resolve_standard_env_runtime_value DATABASE_URL "${DATABASE_URL:-}")"
  runtime_temporal_target_host="$(resolve_standard_env_runtime_value TEMPORAL_TARGET_HOST "${TEMPORAL_TARGET_HOST:-}")"

  append_standard_env_git_mounts extra_mounts
  if ! docker image inspect "$STANDARD_ENV_IMAGE" >/dev/null 2>&1; then
    ensure_standard_env_registry_login
    if ! docker pull "$STANDARD_ENV_IMAGE" >/dev/null 2>&1; then
      echo "[strict-standard-env] failed to pull required image: $STANDARD_ENV_IMAGE" >&2
      return 1
    fi
    if ! docker image inspect "$STANDARD_ENV_IMAGE" >/dev/null 2>&1; then
      echo "[strict-standard-env] required image is unavailable after pull: $STANDARD_ENV_IMAGE" >&2
      return 1
    fi
  fi

  docker run --rm --init \
    --network host \
    -v "$ROOT_DIR:$STANDARD_ENV_WORKDIR" \
    "${extra_mounts[@]}" \
    -w "$STANDARD_ENV_WORKDIR" \
    -e VD_IN_STANDARD_ENV=1 \
    -e CI="${CI:-}" \
    -e GITHUB_ACTIONS="${GITHUB_ACTIONS:-}" \
    -e PYTHONPATH="${PYTHONPATH:-}" \
    -e DATABASE_URL="$runtime_database_url" \
    -e TEMPORAL_TARGET_HOST="$runtime_temporal_target_host" \
    -e TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-}" \
    -e TEMPORAL_TASK_QUEUE="${TEMPORAL_TASK_QUEUE:-}" \
    -e PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$STRICT_CI_PLAYWRIGHT_BROWSERS_PATH}" \
    -e UV_CACHE_DIR="${UV_CACHE_DIR:-$STRICT_CI_UV_CACHE_DIR}" \
    "$STANDARD_ENV_IMAGE" \
    "${command[@]}"
}
