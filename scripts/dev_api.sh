#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "dev_api"

API_APP="${API_APP:-apps.api.app.main:app}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
DEV_API_RELOAD="${DEV_API_RELOAD:-1}"

if [[ ! -d "$ROOT_DIR/apps/api" ]]; then
  echo "[dev_api] API directory not found: $ROOT_DIR/apps/api" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
cd "$ROOT_DIR"

uvicorn_args=("$API_APP" "--host" "$API_HOST" "--port" "$API_PORT")
if [[ "$DEV_API_RELOAD" == "1" ]]; then
  uvicorn_args+=("--reload")
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn "${uvicorn_args[@]}"
fi

exec python -m uvicorn "${uvicorn_args[@]}"
