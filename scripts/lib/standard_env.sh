#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
eval "$(python3 "$ROOT_DIR/scripts/ci_contract.py" shell-exports)"
STANDARD_ENV_IMAGE="${VD_STANDARD_ENV_IMAGE:-$STRICT_CI_STANDARD_IMAGE_REF}"
STANDARD_ENV_DOCKERFILE="${VD_STANDARD_ENV_DOCKERFILE:-$ROOT_DIR/$STRICT_CI_STANDARD_IMAGE_DOCKERFILE}"
STANDARD_ENV_WORKDIR="${VD_STANDARD_ENV_WORKDIR:-$STRICT_CI_STANDARD_IMAGE_WORKDIR}"
STANDARD_ENV_HOST_GATEWAY="${VD_STANDARD_ENV_HOST_GATEWAY:-host.docker.internal}"

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
  "$ROOT_DIR/scripts/build_ci_standard_image.sh" --load --tag local-debug
  STANDARD_ENV_IMAGE="${STRICT_CI_STANDARD_IMAGE_REPOSITORY}:local-debug"
}

run_in_standard_env() {
  local command=("$@")
  local runtime_database_url runtime_temporal_target_host

  runtime_database_url="$(resolve_standard_env_runtime_value DATABASE_URL "${DATABASE_URL:-}")"
  runtime_temporal_target_host="$(resolve_standard_env_runtime_value TEMPORAL_TARGET_HOST "${TEMPORAL_TARGET_HOST:-}")"

  docker pull "$STANDARD_ENV_IMAGE" >/dev/null 2>&1 || true

  docker run --rm --init \
    --network host \
    -v "$ROOT_DIR:$STANDARD_ENV_WORKDIR" \
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
