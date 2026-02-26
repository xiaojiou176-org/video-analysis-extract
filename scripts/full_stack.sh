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
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:${API_PORT}/healthz}"

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

service_match_pattern() {
  local name="$1"
  case "$name" in
    api) echo "apps.api.app.main:app|scripts/dev_api.sh|uvicorn" ;;
    worker) echo "scripts/dev_worker.sh|apps/worker" ;;
    mcp) echo "scripts/dev_mcp.sh|apps/mcp" ;;
    web) echo "next dev|next-server|apps/web" ;;
    *) echo "" ;;
  esac
}

pid_from_pid_file() {
  local name="$1"
  local pid_file="$RUN_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "$pid"
    return 0
  fi
  return 1
}

pid_matches_port() {
  local pid="$1"
  local port="$2"
  if [[ -z "$port" ]]; then
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -Pan -p "$pid" -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 0
}

find_live_pid_by_pattern() {
  local name="$1"
  local pattern
  pattern="$(service_match_pattern "$name")"
  if [[ -z "$pattern" ]] || ! command -v pgrep >/dev/null 2>&1; then
    return 1
  fi
  local expected_port=""
  if [[ "$name" == "api" ]]; then
    expected_port="$API_PORT"
  elif [[ "$name" == "web" ]]; then
    expected_port="$WEB_PORT"
  fi
  local pid cmd
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$cmd" != *"$ROOT_DIR"* ]]; then
      continue
    fi
    if ! pid_matches_port "$pid" "$expected_port"; then
      continue
    fi
    echo "$pid"
    return 0
  done < <(pgrep -f -- "$pattern" || true)
  return 1
}

resolve_live_pid() {
  local name="$1"
  if pid_from_pid_file "$name"; then
    return 0
  fi
  if find_live_pid_by_pattern "$name"; then
    return 0
  fi
  return 1
}

sync_pid_file_if_needed() {
  local name="$1"
  local pid_file="$RUN_DIR/${name}.pid"
  local pid
  if ! pid="$(resolve_live_pid "$name")"; then
    rm -f "$pid_file"
    return 1
  fi
  local current=""
  if [[ -f "$pid_file" ]]; then
    current="$(cat "$pid_file")"
  fi
  if [[ "$current" != "$pid" ]]; then
    echo "$pid" > "$pid_file"
    log "$name pid file healed: $pid"
  fi
  return 0
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

wait_for_http_ok() {
  local url="$1"
  local timeout="${2:-60}"
  local i
  for i in $(seq 1 "$timeout"); do
    if command -v curl >/dev/null 2>&1 && curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

show_service_log_hint() {
  local name="$1"
  local log_file="$LOG_DIR/${name}.log"
  if [[ -f "$log_file" ]]; then
    log "----- ${name} last 40 log lines -----"
    tail -n 40 "$log_file" >&2 || true
    log "----- end ${name} log -----"
  else
    log "no log file found for $name ($log_file)"
  fi
}

stop_one() {
  local name="$1"
  local pid_file="$RUN_DIR/${name}.pid"
  local pid=""
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
  elif resolve_live_pid "$name" >/dev/null 2>&1; then
    pid="$(resolve_live_pid "$name")"
  fi
  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
}

status_one() {
  local name="$1"
  local pid
  if pid="$(resolve_live_pid "$name")"; then
    sync_pid_file_if_needed "$name" >/dev/null 2>&1 || true
    echo "$name: running pid=$pid"
  else
    rm -f "$RUN_DIR/${name}.pid"
    echo "$name: stopped"
  fi
}

cmd="${1:-up}"
case "$cmd" in
  up)
    start_one api env DEV_API_RELOAD=0 "$ROOT_DIR/scripts/dev_api.sh"
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
    if ! wait_for_http_ok "$API_HEALTH_URL" 60; then
      log "ERROR: API health check failed at ${API_HEALTH_URL}"
      show_service_log_hint api
      show_service_log_hint worker
      show_service_log_hint mcp
      exit 1
    fi
    if ! wait_for_tcp 127.0.0.1 "$WEB_PORT" 60; then
      log "ERROR: web port not reachable at 127.0.0.1:${WEB_PORT}"
      show_service_log_hint web
      exit 1
    fi
    log "full stack is ready (api=${API_HEALTH_URL}, web=http://127.0.0.1:${WEB_PORT})"
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
