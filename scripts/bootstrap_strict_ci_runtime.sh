#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p .runtime-cache
export TEMPORAL_TARGET_HOST="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
export TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-default}"
export TEMPORAL_TASK_QUEUE="${TEMPORAL_TASK_QUEUE:-video-analysis-worker}"
export SQLITE_STATE_PATH="${SQLITE_STATE_PATH:-/tmp/video-digestor-strict-api.db}"
export SQLITE_PATH="${SQLITE_PATH:-/tmp/video-digestor-strict-worker.db}"
uv sync --frozen --extra dev --extra e2e

platform_id="$(uname -s)-$(uname -m)"
web_hash_file=".runtime-cache/strict-ci-web-${platform_id}.sha256"
web_hash="$(
  {
    sha256sum apps/web/package-lock.json
    sha256sum apps/web/package.json
    printf '%s\n' "$platform_id"
  } | sha256sum | awk '{print $1}'
)"
existing_web_hash=""
if [[ -f "$web_hash_file" ]]; then
  existing_web_hash="$(cat "$web_hash_file" 2>/dev/null || true)"
fi

if [[ ! -d "apps/web/node_modules" || "$existing_web_hash" != "$web_hash" ]]; then
  rm -rf apps/web/node_modules
  export npm_config_jobs="${npm_config_jobs:-1}"
  npm --prefix apps/web ci --no-audit --no-fund
  printf '%s' "$web_hash" > "$web_hash_file"
fi
