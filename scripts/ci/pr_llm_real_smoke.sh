#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
SCRIPT_NAME="ci_pr_llm_real_smoke"

# shellcheck source=./scripts/runtime/logging.sh
source "$ROOT_DIR/scripts/runtime/logging.sh"
vd_log_init "tests" "$SCRIPT_NAME" "$ROOT_DIR/.runtime-cache/logs/tests/ci-pr-llm-real-smoke.jsonl"

log() {
  vd_log info ci_pr_llm_real_smoke "$*"
}

mkdir -p .runtime-cache/logs/tests .runtime-cache/reports/tests
uv sync --frozen --extra dev --extra e2e

SMOKE_WRITE_TOKEN="${VD_API_KEY:-video-digestor-local-dev-token}"
export VD_API_KEY="${VD_API_KEY:-$SMOKE_WRITE_TOKEN}"
export WEB_ACTION_SESSION_TOKEN="${WEB_ACTION_SESSION_TOKEN:-$SMOKE_WRITE_TOKEN}"

log "starting pr llm real smoke"
./scripts/runtime/dev_api.sh --host 127.0.0.1 --port 18081 --no-reload > .runtime-cache/logs/tests/pr-llm-real-smoke.log 2>&1 &
api_pid="$!"
trap 'kill "${api_pid}" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:18081/healthz" >/dev/null; then
    break
  fi
  sleep 1
done

./scripts/ci/smoke_llm_real_local.sh \
  --api-base-url "http://127.0.0.1:18081" \
  --diagnostics-json ".runtime-cache/reports/tests/pr-llm-real-smoke-result.json" \
  --heartbeat-seconds "30" \
  --max-retries "2"
