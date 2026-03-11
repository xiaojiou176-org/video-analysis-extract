#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p .runtime-cache
uv sync --frozen --extra dev --extra e2e

uv run --with uvicorn uvicorn apps.api.app.main:app --host 127.0.0.1 --port 18081 > .runtime-cache/pr-llm-real-smoke.log 2>&1 &
api_pid="$!"
trap 'kill "${api_pid}" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:18081/healthz" >/dev/null; then
    break
  fi
  sleep 1
done

./scripts/smoke_llm_real_local.sh \
  --api-base-url "http://127.0.0.1:18081" \
  --diagnostics-json ".runtime-cache/pr-llm-real-smoke-result.json" \
  --heartbeat-seconds "30" \
  --max-retries "2"
