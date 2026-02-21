#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_env_file "$ROOT_DIR/.env.local" "dev_mcp"

MCP_DIR="${MCP_DIR:-$ROOT_DIR/apps/mcp}"
MCP_ENTRY="${MCP_ENTRY:-apps.mcp.server}"

if [[ ! -d "$MCP_DIR" ]]; then
  echo "[dev_mcp] MCP directory not found: $MCP_DIR" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

cd "$ROOT_DIR"
if command -v uv >/dev/null 2>&1; then
  exec uv run python -m "$MCP_ENTRY" "$@"
fi

exec python -m "$MCP_ENTRY" "$@"
