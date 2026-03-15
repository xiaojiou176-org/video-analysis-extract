#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="ci_api_real_smoke"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# shellcheck source=./scripts/runtime/logging.sh
source "$ROOT_DIR/scripts/runtime/logging.sh"
vd_log_init "tests" "$SCRIPT_NAME" "$ROOT_DIR/.runtime-cache/logs/tests/ci-api-real-smoke.jsonl"

TEMPORAL_CLI_VERSION="${TEMPORAL_CLI_VERSION:-1.5.1}"
TEMPORAL_CLI_SHA256_LINUX_AMD64="${TEMPORAL_CLI_SHA256_LINUX_AMD64:-ddc95e08b0b076efd4ea9733a3f488eb7d2be875f8834e616cd2a37358b4852d}"
TEMPORAL_CLI_SHA256_LINUX_ARM64="${TEMPORAL_CLI_SHA256_LINUX_ARM64:-bd1b0db9f18b051026de8bf6cc1505f2510f14bbb7a8b9a4a91fff46c77454f5}"

TEMPORAL_PID=""
TEMPORAL_TMPDIR=""

log() {
  vd_log info ci_api_real_smoke "$*"
}

fail() {
  vd_log error ci_api_real_smoke_error "$*"
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

port_is_listening() {
  local port="$1"
  python3 - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    result = sock.connect_ex(("127.0.0.1", port))
raise SystemExit(0 if result == 0 else 1)
PY
}

wait_for_tcp() {
  local port="$1"
  local label="$2"
  local attempts="${3:-60}"
  for _ in $(seq 1 "$attempts"); do
    if port_is_listening "$port"; then
      log "${label} ready on 127.0.0.1:${port}"
      return 0
    fi
    sleep 1
  done
  fail "${label} failed to become ready on 127.0.0.1:${port}"
}

install_temporal_cli() {
  if command -v temporal >/dev/null 2>&1; then
    return 0
  fi
  require_command curl
  require_command tar
  require_command sha256sum
  require_command install

  local arch expected_sha temporal_arch archive archive_path url
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64)
      temporal_arch="amd64"
      expected_sha="$TEMPORAL_CLI_SHA256_LINUX_AMD64"
      ;;
    aarch64|arm64)
      temporal_arch="arm64"
      expected_sha="$TEMPORAL_CLI_SHA256_LINUX_ARM64"
      ;;
    *)
      fail "unsupported architecture for Temporal CLI: ${arch}"
      ;;
  esac
  [[ -n "$expected_sha" ]] || fail "missing Temporal CLI sha256 for architecture ${temporal_arch}"

  TEMPORAL_TMPDIR="$(mktemp -d "/tmp/temporal-cli-api-real-smoke-XXXXXX")"
  archive="temporal_cli_${TEMPORAL_CLI_VERSION}_linux_${temporal_arch}.tar.gz"
  archive_path="${TEMPORAL_TMPDIR}/${archive}"
  url="https://github.com/temporalio/cli/releases/download/v${TEMPORAL_CLI_VERSION}/${archive}"
  curl --retry 5 --retry-all-errors --retry-delay 2 --connect-timeout 15 -fL "$url" -o "$archive_path"
  echo "${expected_sha}  ${archive_path}" | sha256sum -c -
  tar -tzf "$archive_path" temporal >/dev/null
  tar -xzf "$archive_path" -C "$TEMPORAL_TMPDIR" temporal
  install -m 0755 "$TEMPORAL_TMPDIR/temporal" /usr/local/bin/temporal
}

maybe_bootstrap_local_temporal() {
  local resolved_target host port normalized_target
  resolved_target="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
  if [[ "$resolved_target" != *:* ]]; then
    log "skipping Temporal dev bootstrap for non host:port target ${resolved_target}"
    return 0
  fi

  host="${resolved_target%:*}"
  port="${resolved_target##*:}"
  normalized_target="127.0.0.1:${port}"
  case "$host" in
    127.0.0.1|localhost|host.docker.internal)
      ;;
    *)
      log "skipping Temporal dev bootstrap for non-local target ${resolved_target}"
      return 0
      ;;
  esac

  if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    fail "TEMPORAL_TARGET_HOST port must be numeric, got ${resolved_target}"
  fi

  if port_is_listening "$port"; then
    log "reusing existing Temporal listener at ${resolved_target}"
    export TEMPORAL_TARGET_HOST="$normalized_target"
    return 0
  fi

  install_temporal_cli
  mkdir -p .runtime-cache/logs/tests
  log "starting local Temporal dev server at ${resolved_target} for api-real-smoke"
  temporal server start-dev --ip 127.0.0.1 --port "$port" > ".runtime-cache/logs/tests/api-real-smoke-temporal.log" 2>&1 &
  TEMPORAL_PID="$!"
  wait_for_tcp "$port" "api-real-smoke temporal" 60
  export TEMPORAL_TARGET_HOST="$normalized_target"
}

cleanup() {
  if [[ -n "$TEMPORAL_PID" ]] && kill -0 "$TEMPORAL_PID" >/dev/null 2>&1; then
    kill "$TEMPORAL_PID" >/dev/null 2>&1 || true
    wait "$TEMPORAL_PID" 2>/dev/null || true
  fi
  if [[ -n "$TEMPORAL_TMPDIR" && -d "$TEMPORAL_TMPDIR" ]]; then
    rm -rf "$TEMPORAL_TMPDIR"
  fi
}
trap cleanup EXIT

mkdir -p .runtime-cache
default_api_real_smoke_database_url="${API_REAL_SMOKE_DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres}"
if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL}" == "sqlite+pysqlite:///:memory:" ]]; then
  export DATABASE_URL="$default_api_real_smoke_database_url"
fi
export API_INTEGRATION_SMOKE_STRICT="${API_INTEGRATION_SMOKE_STRICT:-1}"
export TEMPORAL_TARGET_HOST="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"

uv sync --frozen --extra dev --extra e2e
maybe_bootstrap_local_temporal
./scripts/ci/api_real_smoke_local.sh --profile ci "$@"
