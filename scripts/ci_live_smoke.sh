#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
eval "$(python3 scripts/ci_contract.py shell-exports)"

mkdir -p .runtime-cache
uv sync --frozen --extra dev --extra e2e

missing=()
[[ -n "${GEMINI_API_KEY:-}" ]] || missing+=("GEMINI_API_KEY")
[[ -n "${RESEND_API_KEY:-}" ]] || missing+=("RESEND_API_KEY")
[[ -n "${RESEND_FROM_EMAIL:-}" ]] || missing+=("RESEND_FROM_EMAIL")
[[ -n "${YOUTUBE_API_KEY:-}" ]] || missing+=("YOUTUBE_API_KEY")
if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "live smoke is required but missing secrets: ${missing[*]}" >&2
  exit 1
fi

pg_url="$(python3 - "$DATABASE_URL" <<'PY'
from urllib.parse import urlsplit, urlunsplit
import sys

value = sys.argv[1]
parts = urlsplit(value)
print(urlunsplit((parts.scheme.split("+", 1)[0], parts.netloc, parts.path, parts.query, parts.fragment)))
PY
)"

for _ in $(seq 1 30); do
  if pg_isready -d "$pg_url" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

for migration in $(find infra/migrations -maxdepth 1 -type f -name '*.sql' | sort); do
  psql "$pg_url" -v ON_ERROR_STOP=1 -f "$migration"
done

temporal server start-dev --ip 127.0.0.1 --port 7233 > .runtime-cache/live-smoke-temporal.log 2>&1 &
LIVE_SMOKE_TEMPORAL_PID="$!"
scripts/dev_api.sh --host 127.0.0.1 --port 18080 --no-reload > .runtime-cache/live-smoke-api.log 2>&1 &
LIVE_SMOKE_API_PID="$!"
scripts/dev_worker.sh --no-show-hints > .runtime-cache/live-smoke-worker.log 2>&1 &
LIVE_SMOKE_WORKER_PID="$!"

cleanup() {
  kill "${LIVE_SMOKE_API_PID}" >/dev/null 2>&1 || true
  kill "${LIVE_SMOKE_WORKER_PID}" >/dev/null 2>&1 || true
  kill "${LIVE_SMOKE_TEMPORAL_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:18080/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

./scripts/e2e_live_smoke.sh \
  --api-base-url "http://127.0.0.1:18080" \
  --require-api "1" \
  --require-secrets "1" \
  --computer-use-strict "1" \
  --computer-use-skip "0" \
  --timeout-seconds "600" \
  --heartbeat-seconds "30" \
  --diagnostics-json ".runtime-cache/e2e-live-smoke-result.json"
