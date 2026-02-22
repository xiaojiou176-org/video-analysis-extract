#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "dev_worker"

WORKER_DIR="${WORKER_DIR:-$ROOT_DIR/apps/worker}"
WORKER_ENTRY="${WORKER_ENTRY:-worker.main}"
WORKER_COMMAND="${WORKER_COMMAND:-run-worker}"
SHOW_HINTS="${DEV_WORKER_SHOW_HINTS:-1}"

if [[ ! -d "$WORKER_DIR" ]]; then
  echo "[dev_worker] Worker directory not found: $WORKER_DIR" >&2
  echo "[dev_worker] Set WORKER_DIR to your worker service path." >&2
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
[dev_worker]   DIGEST_LOCAL_TIMEZONE=${DIGEST_LOCAL_TIMEZONE:-system-local}
[dev_worker]   DIGEST_DAILY_LOCAL_HOUR=${DIGEST_DAILY_LOCAL_HOUR:-9}
[dev_worker] Set DEV_WORKER_SHOW_HINTS=0 to hide this block.
EOF
fi

cd "$WORKER_DIR"

if command -v uv >/dev/null 2>&1; then
  exec uv run python -m "$WORKER_ENTRY" "$WORKER_COMMAND" "$@"
fi

exec python -m "$WORKER_ENTRY" "$WORKER_COMMAND" "$@"
