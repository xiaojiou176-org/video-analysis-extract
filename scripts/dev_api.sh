#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_APP="${API_APP:-apps.api.app.main:app}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"

if [[ ! -d "$ROOT_DIR/apps/api" ]]; then
  echo "[dev_api] API directory not found: $ROOT_DIR/apps/api" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn "$API_APP" --reload --host "$API_HOST" --port "$API_PORT"
fi

exec python -m uvicorn "$API_APP" --reload --host "$API_HOST" --port "$API_PORT"
