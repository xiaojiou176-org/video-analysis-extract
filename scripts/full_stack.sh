#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="full_stack"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.runtime-cache/full-stack"
LOG_DIR="$ROOT_DIR/logs/full-stack"
mkdir -p "$RUN_DIR" "$LOG_DIR"
LAST_FAILURE_REASON_FILE="$RUN_DIR/last_failure_reason"

ENV_PROFILE="${ENV_PROFILE:-local}"
API_PORT="9000"
WEB_PORT="3000"
API_HEALTH_URL="http://127.0.0.1:${API_PORT}/healthz"
API_PORT_EXPLICIT="0"
WEB_PORT_EXPLICIT="0"
API_HEALTH_URL_EXPLICIT="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    --api-port)
      API_PORT="${2:-}"
      API_PORT_EXPLICIT="1"
      shift 2
      ;;
    --web-port)
      WEB_PORT="${2:-}"
      WEB_PORT_EXPLICIT="1"
      shift 2
      ;;
    --api-health-url)
      API_HEALTH_URL="${2:-}"
      API_HEALTH_URL_EXPLICIT="1"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"

api_port_cli=""
web_port_cli=""
api_health_url_cli=""
if [[ "$API_PORT_EXPLICIT" == "1" ]]; then
  api_port_cli="$API_PORT"
fi
if [[ "$WEB_PORT_EXPLICIT" == "1" ]]; then
  web_port_cli="$WEB_PORT"
fi
if [[ "$API_HEALTH_URL_EXPLICIT" == "1" ]]; then
  api_health_url_cli="$API_HEALTH_URL"
fi

API_PORT="$(resolve_runtime_route_value "$ROOT_DIR" "API_PORT" "$api_port_cli" "9000")"
WEB_PORT="$(resolve_runtime_route_value "$ROOT_DIR" "WEB_PORT" "$web_port_cli" "3000")"
VD_API_BASE_URL="$(resolve_runtime_route_value "$ROOT_DIR" "VD_API_BASE_URL" "" "http://127.0.0.1:${API_PORT}")"
NEXT_PUBLIC_API_BASE_URL="$(resolve_runtime_route_value "$ROOT_DIR" "NEXT_PUBLIC_API_BASE_URL" "" "http://127.0.0.1:${API_PORT}")"
API_HEALTH_URL="$(resolve_runtime_route_value "$ROOT_DIR" "API_HEALTH_URL" "$api_health_url_cli" "${VD_API_BASE_URL}/healthz")"

export API_PORT WEB_PORT VD_API_BASE_URL NEXT_PUBLIC_API_BASE_URL API_HEALTH_URL
if [[ -z "${VD_API_KEY:-}" && -z "${CI:-}" && -z "${GITHUB_ACTIONS:-}" ]]; then
  export VD_API_KEY="video-digestor-local-dev-token"
fi
if [[ -z "${WEB_ACTION_SESSION_TOKEN:-}" && -n "${VD_API_KEY:-}" ]]; then
  export WEB_ACTION_SESSION_TOKEN="$VD_API_KEY"
fi
if ! [[ "$API_PORT" =~ ^[0-9]+$ ]] || (( API_PORT <= 0 || API_PORT > 65535 )); then
  echo "[full_stack] --api-port must be an integer in [1,65535]" >&2
  exit 2
fi
if ! [[ "$WEB_PORT" =~ ^[0-9]+$ ]] || (( WEB_PORT <= 0 || WEB_PORT > 65535 )); then
  echo "[full_stack] --web-port must be an integer in [1,65535]" >&2
  exit 2
fi

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }

usage() {
  cat <<'EOF'
Usage: ./scripts/full_stack.sh [--profile <name>] [--api-port <port>] [--web-port <port>] [--api-health-url <url>] [up|down|restart|status|logs]

Starts/stops local app processes:
- API (dev_api.sh)
- Worker (dev_worker.sh)
- Web (next dev)

Notes:
- `scripts/dev_mcp.sh` is an interactive stdio entrypoint, not a background daemon managed by this script.
- Run `./scripts/dev_mcp.sh` manually in a dedicated terminal when you need local MCP debugging.
EOF
}

LOCK_DIR_PATH="$RUN_DIR/.global-lock"
LOCK_HELD="0"
LOCK_TIMEOUT_SECONDS="30"

acquire_global_lock() {
  local elapsed=0
  while true; do
    if mkdir "$LOCK_DIR_PATH" >/dev/null 2>&1; then
      printf '%s\n' "$$" > "$LOCK_DIR_PATH/pid"
      LOCK_HELD="1"
      log "lock acquired pid=$$"
      return 0
    fi

    if [[ -f "$LOCK_DIR_PATH/pid" ]]; then
      local owner_pid
      owner_pid="$(cat "$LOCK_DIR_PATH/pid" 2>/dev/null || true)"
      if [[ -n "$owner_pid" ]] && ! kill -0 "$owner_pid" 2>/dev/null; then
        rm -rf "$LOCK_DIR_PATH"
        continue
      fi
    fi

    elapsed=$((elapsed + 1))
    if (( elapsed >= LOCK_TIMEOUT_SECONDS )); then
      log "ERROR: lock acquisition timed out after ${LOCK_TIMEOUT_SECONDS}s"
      return 1
    fi
    sleep 1
  done
}

release_global_lock() {
  if [[ "$LOCK_HELD" == "1" ]]; then
    rm -rf "$LOCK_DIR_PATH"
    LOCK_HELD="0"
    log "lock released pid=$$"
  fi
}

pid_meta_file() {
  local name="$1"
  printf '%s/%s.pid\n' "$RUN_DIR" "$name"
}

service_signature_id() {
  local name="$1"
  case "$name" in
    api) echo "api_dev_server" ;;
    worker) echo "worker_main_runner" ;;
    web) echo "web_next_dev" ;;
    *) echo "unknown_service" ;;
  esac
}

service_signature_regex() {
  local name="$1"
  case "$name" in
    api) echo "(apps\\.api\\.app\\.main:app|scripts/dev_api\\.sh|uvicorn.*apps\\.api\\.app\\.main:app)" ;;
    worker) echo "(worker\\.main run-worker|scripts/dev_worker\\.sh)" ;;
    web) echo "(next dev|next-server)" ;;
    *) echo "" ;;
  esac
}

service_expected_port() {
  local name="$1"
  case "$name" in
    api) echo "$API_PORT" ;;
    web) echo "$WEB_PORT" ;;
    *) echo "" ;;
  esac
}

read_pid_meta_field() {
  local file="$1"
  local key="$2"
  if [[ ! -f "$file" ]]; then
    return 1
  fi
  awk -F= -v key="$key" '$1 == key {print substr($0, index($0, "=") + 1)}' "$file" | head -n 1
}

read_pid_from_meta_or_legacy() {
  local file="$1"
  local from_meta
  from_meta="$(read_pid_meta_field "$file" "pid" 2>/dev/null || true)"
  if [[ -n "$from_meta" ]]; then
    printf '%s\n' "$from_meta"
    return 0
  fi
  local legacy
  legacy="$(cat "$file" 2>/dev/null || true)"
  if [[ "$legacy" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$legacy"
    return 0
  fi
  return 1
}

read_pid_cmdline() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

pid_matches_signature() {
  local name="$1"
  local pid="$2"
  local pattern
  pattern="$(service_signature_regex "$name")"
  [[ -n "$pattern" ]] || return 1
  local cmd
  cmd="$(read_pid_cmdline "$pid")"
  [[ -n "$cmd" ]] || return 1
  if [[ "$name" != "web" && "$cmd" != *"$ROOT_DIR"* ]]; then
    return 1
  fi
  [[ "$cmd" =~ $pattern ]]
}

pid_matches_port_constraint() {
  local name="$1"
  local pid="$2"
  local expected_port
  expected_port="$(service_expected_port "$name")"
  if [[ -z "$expected_port" ]]; then
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -Pan -p "$pid" -iTCP:"$expected_port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 0
}

pid_matches_service() {
  local name="$1"
  local pid="$2"
  if ! [[ "$pid" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi
  if ! pid_matches_signature "$name" "$pid"; then
    return 1
  fi
  if ! pid_matches_port_constraint "$name" "$pid"; then
    return 1
  fi
  return 0
}

write_pid_meta() {
  local name="$1"
  local pid="$2"
  local file
  file="$(pid_meta_file "$name")"
  local pgid signature started_at
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  signature="$(service_signature_id "$name")"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local tmp_file
  tmp_file="$(mktemp)"
  {
    printf 'pid=%s\n' "$pid"
    printf 'pgid=%s\n' "$pgid"
    printf 'service=%s\n' "$name"
    printf 'signature=%s\n' "$signature"
    printf 'started_at=%s\n' "$started_at"
  } > "$tmp_file"
  mv "$tmp_file" "$file"
}

find_live_pid_by_pattern() {
  local name="$1"
  local pattern
  pattern="$(service_signature_regex "$name")"
  [[ -n "$pattern" ]] || return 1
  if ! command -v pgrep >/dev/null 2>&1; then
    return 1
  fi
  local pid
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    if pid_matches_service "$name" "$pid"; then
      printf '%s\n' "$pid"
      return 0
    fi
  done < <(pgrep -f -- "$pattern" || true)
  return 1
}

resolve_live_pid() {
  local name="$1"
  local file
  file="$(pid_meta_file "$name")"
  if [[ -f "$file" ]]; then
    local file_pid
    file_pid="$(read_pid_from_meta_or_legacy "$file" || true)"
    if [[ -n "$file_pid" ]] && pid_matches_service "$name" "$file_pid"; then
      printf '%s\n' "$file_pid"
      return 0
    fi
  fi
  if find_live_pid_by_pattern "$name"; then
    return 0
  fi
  return 1
}

sync_pid_meta_if_needed() {
  local name="$1"
  local file
  file="$(pid_meta_file "$name")"
  local pid
  if ! pid="$(resolve_live_pid "$name")"; then
    rm -f "$file"
    return 1
  fi
  local current
  current="$(read_pid_from_meta_or_legacy "$file" || true)"
  if [[ "$current" != "$pid" ]]; then
    write_pid_meta "$name" "$pid"
    log "$name pid metadata healed: pid=$pid"
    return 0
  fi
  local signature
  signature="$(read_pid_meta_field "$file" "signature" 2>/dev/null || true)"
  if [[ "$signature" != "$(service_signature_id "$name")" ]]; then
    write_pid_meta "$name" "$pid"
    log "$name pid metadata normalized: pid=$pid"
  fi
  return 0
}

START_STATE="unknown"

start_one() {
  local name="$1"
  shift
  local log_file="$LOG_DIR/${name}.log"
  local existing_pid
  if existing_pid="$(resolve_live_pid "$name")"; then
    sync_pid_meta_if_needed "$name" >/dev/null 2>&1 || true
    log "$name already running pid=${existing_pid}"
    START_STATE="existing"
    return 0
  fi
  log "starting $name"
  if command -v setsid >/dev/null 2>&1; then
    nohup setsid "$@" >"$log_file" 2>&1 &
  else
    nohup "$@" >"$log_file" 2>&1 &
  fi
  local launched_pid=$!
  write_pid_meta "$name" "$launched_pid"
  START_STATE="started"
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
    if [[ "$START_STATE" == "existing" ]]; then
      return 0
    fi
    sleep "$wait_seconds"
    local pid
    if pid="$(resolve_live_pid "$name")"; then
      write_pid_meta "$name" "$pid"
      START_STATE="started"
      return 0
    fi
    log "DIAGNOSE stage=worker_start_retry attempt=${attempt}/${attempts} conclusion=worker_exited_or_signature_mismatch"
    stop_one "$name"
  done
  log "ERROR: ${name} failed to start after ${attempts} attempts"
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
  local file
  file="$(pid_meta_file "$name")"
  local target_pid=""
  local target_pgid=""

  if [[ -f "$file" ]]; then
    local candidate_pid
    candidate_pid="$(read_pid_from_meta_or_legacy "$file" || true)"
    if [[ -n "$candidate_pid" ]] && pid_matches_service "$name" "$candidate_pid"; then
      target_pid="$candidate_pid"
      target_pgid="$(read_pid_meta_field "$file" "pgid" 2>/dev/null || true)"
    fi
  fi

  if [[ -z "$target_pid" ]]; then
    if target_pid="$(find_live_pid_by_pattern "$name")"; then
      target_pgid="$(ps -o pgid= -p "$target_pid" 2>/dev/null | tr -d ' ' || true)"
      write_pid_meta "$name" "$target_pid"
      log "DIAGNOSE stage=stop_${name} conclusion=pid_metadata_stale_recovered pid=${target_pid}"
    fi
  fi

  if [[ -z "$target_pid" ]]; then
    rm -f "$file"
    return 0
  fi

  local self_pgid=""
  self_pgid="$(ps -o pgid= -p "$$" 2>/dev/null | tr -d ' ' || true)"
  if [[ -n "$target_pgid" && "$target_pgid" =~ ^[0-9]+$ && "$target_pgid" != "$self_pgid" ]]; then
    kill -TERM "-${target_pgid}" 2>/dev/null || kill -TERM "$target_pid" 2>/dev/null || true
    local i
    for i in $(seq 1 10); do
      if ! kill -0 "$target_pid" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "$target_pid" 2>/dev/null; then
      kill -KILL "-${target_pgid}" 2>/dev/null || kill -KILL "$target_pid" 2>/dev/null || true
    fi
  else
    kill -TERM "$target_pid" 2>/dev/null || true
    sleep 1
    kill -KILL "$target_pid" 2>/dev/null || true
  fi

  rm -f "$file"
}

status_one() {
  local name="$1"
  local file
  file="$(pid_meta_file "$name")"
  local pid
  if pid="$(resolve_live_pid "$name")"; then
    sync_pid_meta_if_needed "$name" >/dev/null 2>&1 || true
    local pgid signature started_at
    pgid="$(read_pid_meta_field "$file" "pgid" 2>/dev/null || true)"
    signature="$(read_pid_meta_field "$file" "signature" 2>/dev/null || true)"
    started_at="$(read_pid_meta_field "$file" "started_at" 2>/dev/null || true)"
    echo "$name: running pid=$pid pgid=${pgid:-unknown} signature=${signature:-unknown} started_at=${started_at:-unknown}"
  else
    rm -f "$file"
    echo "$name: stopped"
  fi
}

emit_failure_diagnostics() {
  local stage="$1"
  local conclusion="$2"
  local service="${3:-}"
  printf 'stage=%s conclusion=%s service=%s timestamp=%s\n' \
    "$stage" "$conclusion" "${service:-none}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LAST_FAILURE_REASON_FILE"
  log "DIAGNOSE stage=${stage} conclusion=${conclusion}"
  if [[ -n "$service" ]]; then
    show_service_log_hint "$service"
  fi
}

worker_required_env_check() {
  local -a required_keys=(
    "SQLITE_PATH"
    "DATABASE_URL"
    "TEMPORAL_TARGET_HOST"
    "TEMPORAL_NAMESPACE"
    "TEMPORAL_TASK_QUEUE"
    "PIPELINE_WORKSPACE_DIR"
    "PIPELINE_ARTIFACT_ROOT"
  )
  local -a missing=()
  local key
  for key in "${required_keys[@]}"; do
    if [[ -z "${!key:-}" ]]; then
      missing+=("$key")
    fi
  done
  if (( ${#missing[@]} > 0 )); then
    log "DIAGNOSE stage=worker_preflight_env conclusion=missing_required_env vars=${missing[*]}"
    return 1
  fi
  return 0
}

worker_temporal_preflight_check() {
  local temporal_host="${TEMPORAL_TARGET_HOST:-localhost:7233}"
  if [[ "$temporal_host" != *:* ]]; then
    log "DIAGNOSE stage=worker_preflight_temporal conclusion=invalid_temporal_target_host value=${temporal_host}"
    return 1
  fi
  local temporal_addr_host="${temporal_host%:*}"
  local temporal_addr_port="${temporal_host##*:}"
  if ! [[ "$temporal_addr_port" =~ ^[0-9]+$ ]]; then
    log "DIAGNOSE stage=worker_preflight_temporal conclusion=invalid_temporal_port value=${temporal_addr_port}"
    return 1
  fi
  if ! wait_for_tcp "$temporal_addr_host" "$temporal_addr_port" 60; then
    log "DIAGNOSE stage=worker_preflight_temporal conclusion=temporal_unreachable target=${temporal_host}"
    return 1
  fi
  return 0
}

STARTED_THIS_RUN=()

rollback_started_services() {
  local i
  for ((i=${#STARTED_THIS_RUN[@]} - 1; i>=0; i--)); do
    local service_name="${STARTED_THIS_RUN[$i]}"
    log "rollback: stopping ${service_name}"
    stop_one "$service_name"
  done
  STARTED_THIS_RUN=()
}

refresh_runtime_route_snapshot() {
  if declare -F write_runtime_resolved_env >/dev/null 2>&1; then
    write_runtime_resolved_env "$ROOT_DIR" "$SCRIPT_NAME" \
      "API_PORT=${API_PORT}" \
      "WEB_PORT=${WEB_PORT}" \
      "VD_API_BASE_URL=${VD_API_BASE_URL}" \
      "NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}" \
      "API_HEALTH_URL=${API_HEALTH_URL}"
  fi
}

build_web_start_command() {
  local next_bin="$ROOT_DIR/apps/web/node_modules/.bin/next"
  if [[ -x "$next_bin" ]]; then
    printf '%s\0' "bash" "-lc" "cd \"$ROOT_DIR/apps/web\" && exec ./node_modules/.bin/next dev --hostname 127.0.0.1 --port \"$WEB_PORT\""
    return 0
  fi

  printf '%s\0' "npm" "--prefix" "$ROOT_DIR/apps/web" "run" "dev" "--" "--hostname" "127.0.0.1" "--port" "$WEB_PORT"
}

run_up() {
  STARTED_THIS_RUN=()
  rm -f "$LAST_FAILURE_REASON_FILE"

  if ! worker_required_env_check; then
    emit_failure_diagnostics "worker_preflight_env" "missing_worker_required_env"
    rollback_started_services
    return 1
  fi
  if ! worker_temporal_preflight_check; then
    emit_failure_diagnostics "worker_preflight_temporal" "temporal_not_ready"
    rollback_started_services
    return 1
  fi

  start_one api "$ROOT_DIR/scripts/dev_api.sh" --host 127.0.0.1 --port "$API_PORT" --no-reload
  if [[ "$START_STATE" == "started" ]]; then
    STARTED_THIS_RUN+=("api")
  fi
  if ! wait_for_http_ok "$API_HEALTH_URL" 60; then
    emit_failure_diagnostics "api_health" "api_health_check_failed" "api"
    rollback_started_services
    return 1
  fi
  sync_pid_meta_if_needed "api" >/dev/null 2>&1 || true

  local -a web_cmd=()
  local web_part
  while IFS= read -r -d '' web_part; do
    web_cmd+=("$web_part")
  done < <(build_web_start_command)

  start_one web env NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:${API_PORT}" API_PORT="$API_PORT" "${web_cmd[@]}"
  if [[ "$START_STATE" == "started" ]]; then
    STARTED_THIS_RUN+=("web")
  fi
  if ! wait_for_tcp 127.0.0.1 "$WEB_PORT" 60; then
    emit_failure_diagnostics "web_port_check" "web_port_unreachable" "web"
    rollback_started_services
    return 1
  fi
  sync_pid_meta_if_needed "web" >/dev/null 2>&1 || true

  start_one_retry worker 10 2 env TEMPORAL_TARGET_HOST="${TEMPORAL_TARGET_HOST:-localhost:7233}" "$ROOT_DIR/scripts/dev_worker.sh"
  if [[ "$START_STATE" == "started" ]]; then
    STARTED_THIS_RUN+=("worker")
  fi
  if ! sync_pid_meta_if_needed "worker" >/dev/null 2>&1; then
    emit_failure_diagnostics "worker_start" "worker_process_not_detected" "worker"
    rollback_started_services
    return 1
  fi

  VD_API_BASE_URL="http://127.0.0.1:${API_PORT}"
  NEXT_PUBLIC_API_BASE_URL="$VD_API_BASE_URL"
  API_HEALTH_URL="${VD_API_BASE_URL}/healthz"
  export VD_API_BASE_URL NEXT_PUBLIC_API_BASE_URL API_HEALTH_URL
  refresh_runtime_route_snapshot

  log "full stack is ready (api=${API_HEALTH_URL}, web=http://127.0.0.1:${WEB_PORT})"
  log "mcp is interactive-only; run ./scripts/dev_mcp.sh manually when needed"
  return 0
}

run_down() {
  stop_one web
  stop_one worker
  stop_one api
}

cmd="${1:-up}"
case "$cmd" in
  up|down|restart|status|logs)
    if ! acquire_global_lock; then
      exit 1
    fi
    trap release_global_lock EXIT INT TERM
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage
    exit 1
    ;;
esac

case "$cmd" in
  up)
    run_up
    ;;
  down)
    run_down
    ;;
  restart)
    run_down
    run_up
    ;;
  status)
    status_one api
    status_one worker
    status_one web
    echo "mcp: interactive-only (run ./scripts/dev_mcp.sh manually when needed)"
    ;;
  logs)
    tail -n 120 "$LOG_DIR"/*.log 2>/dev/null || true
    ;;
esac
