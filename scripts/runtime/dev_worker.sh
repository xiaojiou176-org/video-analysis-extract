#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
# shellcheck source=./scripts/lib/standard_env.sh
source "$ROOT_DIR/scripts/lib/standard_env.sh"
load_repo_env "$ROOT_DIR" "dev_worker"
ensure_external_uv_project_environment "$ROOT_DIR"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

WORKER_DIR="$ROOT_DIR/apps/worker"
WORKER_ENTRY="worker.main"
WORKER_COMMAND="run-worker"
SHOW_HINTS=1

usage() {
  cat <<'EOF'
Usage: ./bin/dev-worker [options] [-- <command args...>]

Options:
  --worker-dir <path>  Worker project directory (default: <repo>/apps/worker)
  --entry <module>     Python module entry (default: worker.main)
  --command <name>     Worker subcommand (default: run-worker)
  --show-hints         Show startup env hints (default)
  --no-show-hints      Hide startup env hints
  -h, --help           Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --worker-dir)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "[dev_worker] --worker-dir requires a non-empty value" >&2
        exit 2
      fi
      WORKER_DIR="$2"
      shift 2
      ;;
    --entry)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "[dev_worker] --entry requires a non-empty value" >&2
        exit 2
      fi
      WORKER_ENTRY="$2"
      shift 2
      ;;
    --command)
      if [[ $# -lt 2 || -z "${2:-}" || "${2:-}" == --* ]]; then
        echo "[dev_worker] --command requires a non-empty value" >&2
        exit 2
      fi
      WORKER_COMMAND="$2"
      shift 2
      ;;
    --show-hints)
      SHOW_HINTS=1
      shift
      ;;
    --no-show-hints)
      SHOW_HINTS=0
      shift
      ;;
    --)
      shift
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [[ ! -d "$WORKER_DIR" ]]; then
  echo "[dev_worker] Worker directory not found: $WORKER_DIR" >&2
  echo "[dev_worker] Use --worker-dir to point to your worker service path." >&2
  exit 1
fi

export PYTHONPATH="$WORKER_DIR:$ROOT_DIR:${PYTHONPATH:-}"

if [[ "$SHOW_HINTS" == "1" ]]; then
  cat >&2 <<EOF
[dev_worker] Phase3 env hints:
[dev_worker]   DATABASE_URL=${DATABASE_URL:-postgresql+psycopg://localhost:5432/video_analysis}
[dev_worker]   TEMPORAL_TARGET_HOST=${TEMPORAL_TARGET_HOST:-localhost:7233}
[dev_worker]   TEMPORAL_NAMESPACE=${TEMPORAL_NAMESPACE:-default}
[dev_worker]   TEMPORAL_TASK_QUEUE=${TEMPORAL_TASK_QUEUE:-video-analysis-worker}
[dev_worker]   SQLITE_PATH=${SQLITE_PATH:-$HOME/.video-digestor/state/worker_state.db}
[dev_worker]   REQUEST_TIMEOUT_SECONDS=${REQUEST_TIMEOUT_SECONDS:-15}
[dev_worker]   REQUEST_RETRY_ATTEMPTS=${REQUEST_RETRY_ATTEMPTS:-3}
[dev_worker]   REQUEST_RETRY_BACKOFF_SECONDS=${REQUEST_RETRY_BACKOFF_SECONDS:-0.5}
[dev_worker]   LOCK_TTL_SECONDS=${LOCK_TTL_SECONDS:-90}
[dev_worker]   RSSHUB_BASE_URL=${RSSHUB_BASE_URL:-https://rsshub.app}
[dev_worker]   PIPELINE_WORKSPACE_DIR=${PIPELINE_WORKSPACE_DIR:-$HOME/.video-digestor/workspace}
[dev_worker]   PIPELINE_ARTIFACT_ROOT=${PIPELINE_ARTIFACT_ROOT:-$HOME/.video-digestor/artifacts}
[dev_worker]   PIPELINE_RETRY_ATTEMPTS=${PIPELINE_RETRY_ATTEMPTS:-2}
[dev_worker]   PIPELINE_RETRY_BACKOFF_SECONDS=${PIPELINE_RETRY_BACKOFF_SECONDS:-1.0}
[dev_worker]   PIPELINE_SUBPROCESS_TIMEOUT_SECONDS=${PIPELINE_SUBPROCESS_TIMEOUT_SECONDS:-180}
[dev_worker]   PIPELINE_MAX_FRAMES=${PIPELINE_MAX_FRAMES:-6}
[dev_worker]   PIPELINE_FRAME_INTERVAL_SECONDS=${PIPELINE_FRAME_INTERVAL_SECONDS:-30}
[dev_worker]   GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.1-pro-preview}
[dev_worker]   GEMINI_FAST_MODEL=${GEMINI_FAST_MODEL:-gemini-3-flash-preview}
[dev_worker]   GEMINI_EMBEDDING_MODEL=${GEMINI_EMBEDDING_MODEL:-gemini-embedding-001}
[dev_worker]   GEMINI_THINKING_LEVEL=${GEMINI_THINKING_LEVEL:-high}
[dev_worker]   GEMINI_INCLUDE_THOUGHTS=${GEMINI_INCLUDE_THOUGHTS:-false}
[dev_worker]   GEMINI_CONTEXT_CACHE_ENABLED=${GEMINI_CONTEXT_CACHE_ENABLED:-true}
[dev_worker]   GEMINI_CONTEXT_CACHE_TTL_SECONDS=${GEMINI_CONTEXT_CACHE_TTL_SECONDS:-21600}
[dev_worker]   GEMINI_CONTEXT_CACHE_MIN_CHARS=${GEMINI_CONTEXT_CACHE_MIN_CHARS:-4096}
[dev_worker]   DIGEST_LOCAL_TIMEZONE=${DIGEST_LOCAL_TIMEZONE:-system-local}
[dev_worker]   DIGEST_DAILY_LOCAL_HOUR=${DIGEST_DAILY_LOCAL_HOUR:-9}
[dev_worker] Set --no-show-hints to hide this block.
EOF
fi

cd "$WORKER_DIR"

if command -v uv >/dev/null 2>&1; then
  exec uv run python -m "$WORKER_ENTRY" "$WORKER_COMMAND" "$@"
fi

exec python -m "$WORKER_ENTRY" "$WORKER_COMMAND" "$@"
