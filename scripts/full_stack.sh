#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="full_stack"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.runtime-cache/full-stack"
LOG_DIR="$ROOT_DIR/logs/full-stack"
mkdir -p "$RUN_DIR" "$LOG_DIR"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

if [[ -n "${WEB_BASE_URL:-}" ]]; then
  WEB_PORT="${WEB_PORT:-$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u = os.getenv("WEB_BASE_URL", "")
p = urlparse(u).port
print(p or 3000)
PY
)}"
else
  WEB_PORT="${WEB_PORT:-3000}"
fi
API_PORT="${API_PORT:-8000}"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }

usage() {
  cat <<'EOF'
Usage: ./scripts/full_stack.sh [up|down|restart|status|logs]

Starts/stops local app processes:
- API (dev_api.sh)
- Worker (dev_worker.sh)
- MCP (dev_mcp.sh)
- Web (next dev)
EOF
}

start_one() {
  local name="$1"; shift
  local pid_file="$RUN_DIR/${name}.pid"
  local log_file="$LOG_DIR/${name}.log"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    log "$name already running pid=$(cat "$pid_file")"
    return 0
  fi
  log "starting $name"
  nohup "$@" >"$log_file" 2>&1 &
  echo $! > "$pid_file"
}

start_one_retry() {
  local name="$1"
  local attempts="$2"
  local wait_seconds="$3"
  shift 3
  local attempt
  for attempt in $(seq 1 "$attempts"); do
    start_one "$name" "$@"
    sleep "$wait_seconds"
    if [[ -f "$RUN_DIR/${name}.pid" ]] && kill -0 "$(cat "$RUN_DIR/${name}.pid")" 2>/dev/null; then
      return 0
    fi
    log "$name failed to stay up (attempt ${attempt}/${attempts}), retrying"
    stop_one "$name"
  done
  log "ERROR: $name failed to start after ${attempts} attempts"
  return 1
}

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local timeout="${3:-60}"
  local i
  for i in $(seq 1 "$timeout"); do
    if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_one() {
  local name="$1"
  local pid_file="$RUN_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

status_one() {
  local name="$1"
  local pid_file="$RUN_DIR/${name}.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name: running pid=$(cat "$pid_file")"
  else
    echo "$name: stopped"
  fi
}

cmd="${1:-up}"
case "$cmd" in
  up)
    start_one api "$ROOT_DIR/scripts/dev_api.sh"
    start_one mcp "$ROOT_DIR/scripts/dev_mcp.sh"
    start_one web npm --prefix "$ROOT_DIR/apps/web" run dev -- --port "$WEB_PORT"
    temporal_host="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
    temporal_addr_host="${temporal_host%:*}"
    temporal_addr_port="${temporal_host##*:}"
    if wait_for_tcp "$temporal_addr_host" "$temporal_addr_port" 60; then
      start_one_retry worker 10 2 "$ROOT_DIR/scripts/dev_worker.sh"
    else
      log "ERROR: Temporal not reachable at ${temporal_host}"
      exit 1
    fi
    ;;
  down)
    stop_one web
    stop_one mcp
    stop_one worker
    stop_one api
    ;;
  restart)
    "$0" down
    "$0" up
    ;;
  status)
    status_one api
    status_one worker
    status_one mcp
    status_one web
    ;;
  logs)
    tail -n 120 "$LOG_DIR"/*.log 2>/dev/null || true
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
