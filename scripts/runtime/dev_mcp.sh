#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "dev_mcp"

MCP_DIR="$ROOT_DIR/apps/mcp"
MCP_ENTRY="apps.mcp.server"

usage() {
  cat <<'EOF'
Usage: ./bin/dev-mcp [--entry <module>] [--mcp-dir <path>]

Options:
  --entry <module>   Python module entry (default: apps.mcp.server)
  --mcp-dir <path>   MCP project directory (default: <repo>/apps/mcp)
  -h, --help         Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --entry)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "[dev_mcp] --entry requires a non-empty value" >&2
        exit 2
      fi
      MCP_ENTRY="$2"
      shift 2
      ;;
    --mcp-dir)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "[dev_mcp] --mcp-dir requires a non-empty value" >&2
        exit 2
      fi
      MCP_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[dev_mcp] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

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
