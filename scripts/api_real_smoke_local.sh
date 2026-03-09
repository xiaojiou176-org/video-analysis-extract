#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="api_real_smoke_local"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PROFILE="${ENV_PROFILE:-local}"
API_HOST="127.0.0.1"
API_PORT="18080"
API_PORT_EXPLICIT="0"
DATABASE_URL_EXPLICIT="0"
DATABASE_URL_OVERRIDE=""
POSTGRES_READY_TIMEOUT_SECONDS="45"
API_HEALTH_TIMEOUT_SECONDS="60"
WORKFLOW_CLOSURE_TIMEOUT_SECONDS="120"
WORKER_READINESS_TIMEOUT_SECONDS="45"

API_PID=""
WORKER_PID=""
SMOKE_DATABASE_NAME=""
SMOKE_DATABASE_URL=""
ADMIN_DATABASE_URL=""
ADMIN_DATABASE_PG_URL=""
WORKFLOW_PROBE_ROOT=""

usage() {
  cat <<'EOF'
Usage: ./scripts/api_real_smoke_local.sh [options]

Options:
  --profile, --env-profile <name>       Env profile passed to load_repo_env (default: local)
  --api-host <host>                     API bind host for the local smoke server (default: 127.0.0.1)
  --api-port <port>                     API bind port for the local smoke server (default: 18080)
  --database-url <url>                  Override DATABASE_URL for the real Postgres smoke
  --postgres-ready-timeout-seconds <n>  Timeout waiting for Postgres readiness (default: 45)
  --api-health-timeout-seconds <n>      Timeout waiting for API /healthz (default: 60)
  --workflow-closure-timeout-seconds <n>
                                        Timeout waiting for API -> Temporal -> worker cleanup closure (default: 120)
  -h, --help                            Show this help
EOF
}

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail_with_kind() {
  local kind="$1"
  local reason="$2"
  log "failure_kind=${kind} reason=${reason}"
  exit 1
}

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail_with_kind "tooling_missing" "required command not found: ${cmd}"
}

preflight_loopback_ipv4_connectivity() {
  local probe_result=""
  if ! probe_result="$(
    python3 - <<'PY'
import errno
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        return


server = HTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
thread = threading.Thread(target=server.handle_request, daemon=True)
thread.start()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2.0)
try:
    sock.connect(("127.0.0.1", port))
except OSError as exc:
    print(f"error:{exc.errno}:{exc}")
else:
    print("ok")
finally:
    sock.close()
    server.server_close()
PY
  )"; then
    fail_with_kind "loopback_probe_error" "failed running IPv4 loopback preflight probe"
  fi

  if [[ "$probe_result" == ok ]]; then
    return 0
  fi

  if [[ "$probe_result" == error:49:* ]]; then
    fail_with_kind \
      "host_loopback_ipv4_exhausted" \
      "local IPv4 loopback connect probe failed with EADDRNOTAVAIL (Errno 49). This host cannot reliably run real smoke right now; reduce local MCP/Codex bridge connections or retry on a cleaner runner."
  fi

  fail_with_kind \
    "host_loopback_ipv4_unhealthy" \
    "local IPv4 loopback connect probe failed: ${probe_result}"
}

port_is_listening() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  python3 - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    result = sock.connect_ex(("127.0.0.1", port))
raise SystemExit(0 if result == 0 else 1)
PY
}

choose_available_api_port() {
  local candidate="$1"
  local limit="${2:-20}"
  local offset
  for offset in $(seq 0 "$limit"); do
    local port=$((candidate + offset))
    if ! port_is_listening "$port"; then
      printf '%s\n' "$port"
      return 0
    fi
  done
  return 1
}

redact_database_url() {
  DATABASE_URL_TO_REDACT="${1:-}" python3 - <<'PY'
import os
from urllib.parse import urlsplit, urlunsplit

raw = os.environ.get("DATABASE_URL_TO_REDACT", "")
if not raw:
    print("")
    raise SystemExit(0)
parts = urlsplit(raw)
hostname = parts.hostname or ""
port = f":{parts.port}" if parts.port else ""
username = parts.username or ""
if parts.password:
    auth = f"{username}:***@" if username else "***@"
else:
    auth = f"{username}@" if username else ""
netloc = f"{auth}{hostname}{port}"
print(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)))
PY
}

temporal_task_queue_has_worker_pollers() {
  TEMPORAL_TARGET_HOST="$TEMPORAL_TARGET_HOST" \
  TEMPORAL_NAMESPACE="$TEMPORAL_NAMESPACE" \
  TEMPORAL_TASK_QUEUE="$TEMPORAL_TASK_QUEUE" \
    uv run python - <<'PY' >/dev/null 2>&1
import asyncio
import os

from temporalio.api.enums.v1 import TaskQueueType
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest
from temporalio.client import Client


async def main() -> int:
    client = await Client.connect(
        os.environ["TEMPORAL_TARGET_HOST"],
        namespace=os.environ["TEMPORAL_NAMESPACE"],
    )
    task_queue = TaskQueue(name=os.environ["TEMPORAL_TASK_QUEUE"])
    for task_queue_type in (
        TaskQueueType.TASK_QUEUE_TYPE_WORKFLOW,
        TaskQueueType.TASK_QUEUE_TYPE_ACTIVITY,
    ):
        response = await client.workflow_service.describe_task_queue(
            DescribeTaskQueueRequest(
                namespace=os.environ["TEMPORAL_NAMESPACE"],
                task_queue=task_queue,
                task_queue_type=task_queue_type,
            )
        )
        if len(response.pollers) == 0:
            return 1
    return 0


raise SystemExit(asyncio.run(main()))
PY
}

ensure_cleanup_worker_online() {
  if temporal_task_queue_has_worker_pollers; then
    log "detected existing temporal worker pollers on task queue ${TEMPORAL_TASK_QUEUE}; reusing running worker"
    return 0
  fi

  log "no active temporal worker pollers detected on ${TEMPORAL_TASK_QUEUE}; starting temporary worker for cleanup workflow probe"
  (cd "$ROOT_DIR" && ./scripts/dev_worker.sh --no-show-hints >"$WORKER_LOG" 2>&1) &
  WORKER_PID="$!"
  for _ in $(seq 1 "$WORKER_READINESS_TIMEOUT_SECONDS"); do
    if ! kill -0 "$WORKER_PID" >/dev/null 2>&1; then
      tail -n 80 "$WORKER_LOG" >&2 || true
      fail_with_kind "worker_boot_error" "temporary worker exited before cleanup workflow probe"
    fi
    if temporal_task_queue_has_worker_pollers; then
      log "temporary worker is online for task queue ${TEMPORAL_TASK_QUEUE}"
      return 0
    fi
    sleep 1
  done

  tail -n 80 "$WORKER_LOG" >&2 || true
  fail_with_kind "worker_boot_error" "timed out waiting for worker pollers on task queue ${TEMPORAL_TASK_QUEUE}"
}

run_cleanup_workflow_closure_probe() {
  WORKFLOW_PROBE_ROOT="$ROOT_DIR/.runtime-cache/api-real-smoke-workflow-${SMOKE_DATABASE_NAME}"
  local workspace_dir="$WORKFLOW_PROBE_ROOT/workspace"
  local cache_dir="$WORKFLOW_PROBE_ROOT/cache"
  local media_file="$workspace_dir/job-1/downloads/media.mp4"
  local frame_file="$workspace_dir/job-1/frames/frame_001.jpg"
  local digest_file="$workspace_dir/job-1/artifacts/digest.md"
  local cache_old_file="$cache_dir/stale-cache.bin"
  local cache_keep_file="$cache_dir/fresh-cache.bin"
  local payload
  local response_file
  local status
  local body
  local write_token="video-digestor-local-dev-token"

  mkdir -p \
    "$(dirname "$media_file")" \
    "$(dirname "$frame_file")" \
    "$(dirname "$digest_file")" \
    "$cache_dir"
  printf 'video-bytes' >"$media_file"
  printf 'frame-bytes' >"$frame_file"
  printf 'keep-digest' >"$digest_file"
  printf 'stale-cache' >"$cache_old_file"
  printf 'fresh-cache' >"$cache_keep_file"

  WORKFLOW_MEDIA_FILE="$media_file" \
  WORKFLOW_FRAME_FILE="$frame_file" \
  WORKFLOW_DIGEST_FILE="$digest_file" \
  WORKFLOW_CACHE_OLD_FILE="$cache_old_file" \
  python3 - <<'PY'
import os
from datetime import datetime, timedelta, timezone

old_ts = (datetime.now(timezone.utc) - timedelta(hours=3)).timestamp()
for env_name in (
    "WORKFLOW_MEDIA_FILE",
    "WORKFLOW_FRAME_FILE",
    "WORKFLOW_DIGEST_FILE",
    "WORKFLOW_CACHE_OLD_FILE",
):
    path = os.environ[env_name]
    os.utime(path, (old_ts, old_ts))
PY

  payload="$(
    WORKSPACE_DIR="$workspace_dir" \
    CACHE_DIR="$cache_dir" \
    python3 - <<'PY'
import json
import os

print(
    json.dumps(
        {
            "workflow": "cleanup",
            "run_once": True,
            "wait_for_result": True,
            "payload": {
                "workspace_dir": os.environ["WORKSPACE_DIR"],
                "cache_dir": os.environ["CACHE_DIR"],
                "older_than_hours": 1,
                "cache_older_than_hours": 1,
                "cache_max_size_mb": 1,
            },
        }
    )
)
PY
  )"

  response_file="$(mktemp)"
  status="$(
    curl -sS \
      --max-time "$WORKFLOW_CLOSURE_TIMEOUT_SECONDS" \
      -o "$response_file" \
      -w '%{http_code}' \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -H "X-API-Key: ${write_token}" \
      -H "Authorization: Bearer ${write_token}" \
      -X POST "${API_BASE_URL}/api/v1/workflows/run" \
      --data "$payload"
  )"
  body="$(cat "$response_file")"
  rm -f "$response_file"

  if [[ "$status" != "200" ]]; then
    fail_with_kind \
      "workflow_closure_failure" \
      "cleanup workflow probe failed on ${API_BASE_URL}/api/v1/workflows/run (status=${status} body=${body})"
  fi

  if ! \
    WORKFLOW_RESPONSE_BODY="$body" \
    EXPECT_WORKSPACE_DIR="$workspace_dir" \
    EXPECT_CACHE_DIR="$cache_dir" \
    EXPECT_MEDIA_FILE="$media_file" \
    EXPECT_FRAME_FILE="$frame_file" \
    EXPECT_DIGEST_FILE="$digest_file" \
    EXPECT_CACHE_OLD_FILE="$cache_old_file" \
    EXPECT_CACHE_KEEP_FILE="$cache_keep_file" \
    python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(os.environ["WORKFLOW_RESPONSE_BODY"])
result = payload.get("result") or {}

assert payload["workflow"] == "cleanup"
assert payload["workflow_name"] == "CleanupWorkspaceWorkflow"
assert payload["status"] == "completed"
assert result.get("ok") is True
assert result.get("workspace_dir") == os.environ["EXPECT_WORKSPACE_DIR"]
assert result.get("cache_dir") == os.environ["EXPECT_CACHE_DIR"]
assert int(result.get("deleted_files", 0)) >= 2
assert int(result.get("cache_deleted_files_by_age", 0)) >= 1
assert not Path(os.environ["EXPECT_MEDIA_FILE"]).exists()
assert not Path(os.environ["EXPECT_FRAME_FILE"]).exists()
assert Path(os.environ["EXPECT_DIGEST_FILE"]).exists()
assert not Path(os.environ["EXPECT_CACHE_OLD_FILE"]).exists()
assert Path(os.environ["EXPECT_CACHE_KEEP_FILE"]).exists()
PY
  then
    fail_with_kind \
      "workflow_closure_failure" \
      "cleanup workflow probe returned unexpected payload or filesystem state: ${body}"
  fi

  log "api -> temporal -> worker cleanup workflow closure probe passed"
}

cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" 2>/dev/null || true
  fi

  if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" >/dev/null 2>&1; then
    kill "$WORKER_PID" >/dev/null 2>&1 || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi

  if [[ -n "$SMOKE_DATABASE_NAME" && -n "$ADMIN_DATABASE_PG_URL" ]]; then
    ADMIN_DATABASE_URL="$ADMIN_DATABASE_PG_URL" \
    SMOKE_DATABASE_NAME="$SMOKE_DATABASE_NAME" \
      uv run python - <<'PY' >/dev/null 2>&1 || true
import os

import psycopg
from psycopg import sql

admin_url = os.environ["ADMIN_DATABASE_URL"]
smoke_db = os.environ["SMOKE_DATABASE_NAME"]

with psycopg.connect(admin_url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s
              AND pid <> pg_backend_pid()
            """,
            (smoke_db,),
        )
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(smoke_db)))
PY
  fi

  if [[ -n "$WORKFLOW_PROBE_ROOT" ]]; then
    WORKFLOW_PROBE_ROOT="$WORKFLOW_PROBE_ROOT" python3 - <<'PY' >/dev/null 2>&1 || true
import os
import shutil
from pathlib import Path

root = Path(os.environ["WORKFLOW_PROBE_ROOT"]).expanduser()
if root.exists():
    shutil.rmtree(root, ignore_errors=True)
PY
  fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile|--env-profile)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    --api-host)
      API_HOST="${2:-}"
      shift 2
      ;;
    --api-port)
      API_PORT="${2:-}"
      API_PORT_EXPLICIT="1"
      shift 2
      ;;
    --database-url)
      DATABASE_URL_OVERRIDE="${2:-}"
      DATABASE_URL_EXPLICIT="1"
      shift 2
      ;;
    --postgres-ready-timeout-seconds)
      POSTGRES_READY_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --api-health-timeout-seconds)
      API_HEALTH_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --workflow-closure-timeout-seconds)
      WORKFLOW_CLOSURE_TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail_with_kind "invalid_argument" "unknown argument: $1"
      ;;
  esac
done

if ! [[ "$API_PORT" =~ ^[0-9]+$ ]] || ((API_PORT <= 0 || API_PORT > 65535)); then
  fail_with_kind "invalid_argument" "--api-port must be an integer in [1,65535]"
fi
if ! [[ "$POSTGRES_READY_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ((POSTGRES_READY_TIMEOUT_SECONDS < 1)); then
  fail_with_kind "invalid_argument" "--postgres-ready-timeout-seconds must be a positive integer"
fi
if ! [[ "$API_HEALTH_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ((API_HEALTH_TIMEOUT_SECONDS < 1)); then
  fail_with_kind "invalid_argument" "--api-health-timeout-seconds must be a positive integer"
fi
if ! [[ "$WORKFLOW_CLOSURE_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ((WORKFLOW_CLOSURE_TIMEOUT_SECONDS < 1)); then
  fail_with_kind "invalid_argument" "--workflow-closure-timeout-seconds must be a positive integer"
fi
if ! [[ "$WORKER_READINESS_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || ((WORKER_READINESS_TIMEOUT_SECONDS < 1)); then
  fail_with_kind "invalid_argument" "WORKER_READINESS_TIMEOUT_SECONDS must be a positive integer"
fi

resolved_api_host="$API_HOST"
resolved_api_port="$API_PORT"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"
API_HOST="$resolved_api_host"
API_PORT="$resolved_api_port"
if [[ "$DATABASE_URL_EXPLICIT" == "1" ]]; then
  export DATABASE_URL="$DATABASE_URL_OVERRIDE"
fi

require_command python3
require_command uv
require_command psql
require_command curl

preflight_loopback_ipv4_connectivity

DATABASE_URL="${DATABASE_URL:-}"
[[ -n "$DATABASE_URL" ]] || fail_with_kind "config_error" "DATABASE_URL is required"

driver_name="$(
  DATABASE_URL="$DATABASE_URL" uv run python - <<'PY'
import os
from sqlalchemy.engine import make_url

print(make_url(os.environ["DATABASE_URL"]).drivername)
PY
)"
if [[ "$driver_name" != "postgresql+psycopg" ]]; then
  fail_with_kind "config_error" "DATABASE_URL must use postgresql+psycopg, got '${driver_name}'"
fi

db_binding="$(
  DATABASE_URL="$DATABASE_URL" uv run python - <<'PY'
import os
import shlex
import uuid
from sqlalchemy.engine import make_url

base = make_url(os.environ["DATABASE_URL"])
smoke_db_name = f"video_analysis_api_smoke_local_{uuid.uuid4().hex[:8]}"
admin_db_name = base.database or "postgres"
smoke_url = base.set(database=smoke_db_name).render_as_string(hide_password=False)
admin_url = base.set(database=admin_db_name).render_as_string(hide_password=False)
admin_pg_url = base.set(drivername="postgresql", database=admin_db_name).render_as_string(hide_password=False)

print(f"SMOKE_DATABASE_NAME={shlex.quote(smoke_db_name)}")
print(f"SMOKE_DATABASE_URL={shlex.quote(smoke_url)}")
print(f"ADMIN_DATABASE_URL={shlex.quote(admin_url)}")
print(f"ADMIN_DATABASE_PG_URL={shlex.quote(admin_pg_url)}")
PY
)"
eval "$db_binding"

log "verifying postgres connectivity: $(redact_database_url "$ADMIN_DATABASE_URL")"
postgres_ready="0"
for _ in $(seq 1 "$POSTGRES_READY_TIMEOUT_SECONDS"); do
  if ADMIN_DATABASE_URL="$ADMIN_DATABASE_PG_URL" uv run python - <<'PY'
import os
import psycopg

with psycopg.connect(os.environ["ADMIN_DATABASE_URL"], connect_timeout=3) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
PY
  then
    postgres_ready="1"
    break
  fi
  sleep 1
done
if [[ "$postgres_ready" != "1" ]]; then
  fail_with_kind "postgres_unreachable" "timed out waiting for postgres server readiness"
fi

log "creating isolated smoke database: ${SMOKE_DATABASE_NAME}"
if ! ADMIN_DATABASE_URL="$ADMIN_DATABASE_PG_URL" SMOKE_DATABASE_NAME="$SMOKE_DATABASE_NAME" uv run python - <<'PY'
import os

import psycopg
from psycopg import sql

admin_url = os.environ["ADMIN_DATABASE_URL"]
smoke_db = os.environ["SMOKE_DATABASE_NAME"]

with psycopg.connect(admin_url, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(smoke_db)))
PY
then
  fail_with_kind "postgres_create_db_error" "failed to create isolated smoke database"
fi

DATABASE_URL="$SMOKE_DATABASE_URL"
PSQL_URL="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"
if [[ "$PSQL_URL" == "$DATABASE_URL" ]]; then
  fail_with_kind "config_error" "failed to derive psql URL from smoke DATABASE_URL"
fi

mapfile -t migration_files < <(find "$ROOT_DIR/infra/migrations" -maxdepth 1 -type f -name '*.sql' | sort)
if [[ "${#migration_files[@]}" -eq 0 ]]; then
  fail_with_kind "migration_error" "no SQL migrations found under infra/migrations"
fi
log "applying migrations to isolated smoke database"
for migration in "${migration_files[@]}"; do
  if ! PGCONNECT_TIMEOUT=3 psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f "$migration" >/dev/null; then
    fail_with_kind "migration_error" "failed migration: ${migration}"
  fi
done

mkdir -p "$ROOT_DIR/.runtime-cache"
API_LOG="$ROOT_DIR/.runtime-cache/api-real-smoke-local.log"
WORKER_LOG="$ROOT_DIR/.runtime-cache/api-real-smoke-local-worker.log"
STATE_DB_PATH="$ROOT_DIR/.runtime-cache/api-real-smoke-local-state.sqlite3"
rm -f "$API_LOG" "$WORKER_LOG" "$STATE_DB_PATH"

if port_is_listening "$API_PORT"; then
  if [[ "$API_PORT_EXPLICIT" == "1" ]]; then
    fail_with_kind "api_boot_error" "api port ${API_PORT} is already in use"
  fi
  fallback_port="$(choose_available_api_port "$API_PORT" 20 || true)"
  if [[ -z "${fallback_port:-}" ]]; then
    fail_with_kind "api_boot_error" "default api port ${API_PORT} is already in use and no fallback port was found"
  fi
  log "default api port ${API_PORT} is already in use; using fallback port ${fallback_port}"
  API_PORT="$fallback_port"
fi

export DATABASE_URL
export API_INTEGRATION_SMOKE_STRICT="1"
export TEMPORAL_TARGET_HOST="${TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
export TEMPORAL_NAMESPACE="${TEMPORAL_NAMESPACE:-default}"
export TEMPORAL_TASK_QUEUE="${TEMPORAL_TASK_QUEUE:-video-analysis-worker}"
export SQLITE_STATE_PATH="$STATE_DB_PATH"
export UI_AUDIT_GEMINI_ENABLED="${UI_AUDIT_GEMINI_ENABLED:-false}"
export NOTIFICATION_ENABLED="${NOTIFICATION_ENABLED:-0}"
export VD_ALLOW_UNAUTH_WRITE="${VD_ALLOW_UNAUTH_WRITE:-true}"
export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/apps/worker:${PYTHONPATH:-}"

# Keep pytest in unauth-write mode. dev_api.sh will provision its own local token
# for the spawned API process when no explicit token is exported.
unset VD_API_KEY
unset WEB_ACTION_SESSION_TOKEN

log "starting API smoke server: http://${API_HOST}:${API_PORT}"
(cd "$ROOT_DIR" && ./scripts/dev_api.sh --host "$API_HOST" --port "$API_PORT" --no-reload >"$API_LOG" 2>&1) &
API_PID="$!"

API_BASE_URL="http://${API_HOST}:${API_PORT}"
api_ready="0"
for _ in $(seq 1 "$API_HEALTH_TIMEOUT_SECONDS"); do
  if curl -fsS "${API_BASE_URL}/healthz" >/dev/null 2>&1; then
    api_ready="1"
    break
  fi
  sleep 1
done
if [[ "$api_ready" != "1" ]]; then
  tail -n 80 "$API_LOG" >&2 || true
  fail_with_kind "api_boot_error" "API healthz did not become ready on ${API_BASE_URL}"
fi

if ! curl -fsS "${API_BASE_URL}/api/v1/feed/digests?limit=1" >/dev/null 2>&1; then
  tail -n 80 "$API_LOG" >&2 || true
  fail_with_kind "api_http_probe_failure" "feed digest probe failed on ${API_BASE_URL}/api/v1/feed/digests?limit=1"
fi

ensure_cleanup_worker_online

log "running integration smoke tests with API_INTEGRATION_SMOKE_STRICT=1"
if ! (
  cd "$ROOT_DIR" && \
  env -u VD_API_KEY -u WEB_ACTION_SESSION_TOKEN \
  VD_ALLOW_UNAUTH_WRITE="true" \
  VD_CI_ALLOW_UNAUTH_WRITE="true" \
  API_INTEGRATION_SMOKE_STRICT="1" \
  uv run pytest apps/api/tests/test_api_integration_smoke.py -q -rA
); then
  tail -n 80 "$API_LOG" >&2 || true
  fail_with_kind "integration_test_failure" "apps/api/tests/test_api_integration_smoke.py failed"
fi

log "running API -> Temporal -> worker cleanup workflow closure probe"
if ! run_cleanup_workflow_closure_probe; then
  tail -n 80 "$API_LOG" >&2 || true
  tail -n 80 "$WORKER_LOG" >&2 || true
  fail_with_kind "workflow_closure_failure" "cleanup workflow closure probe failed"
fi

log "real postgres integration smoke passed"
echo "real postgres integration smoke passed"
