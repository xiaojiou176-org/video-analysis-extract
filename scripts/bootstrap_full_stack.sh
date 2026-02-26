#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="bootstrap_full_stack"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"

PROFILE="${PROFILE:-local}"
INSTALL_DEPS="${INSTALL_DEPS:-1}"
WITH_CORE_SERVICES="${WITH_CORE_SERVICES:-1}"
WITH_READER_STACK="${WITH_READER_STACK:-1}"
READER_ENV_FILE="${READER_ENV_FILE:-$ROOT_DIR/env/profiles/reader.env}"
OFFLINE_FALLBACK="${OFFLINE_FALLBACK:-1}"
FALLBACK_MARKER_DIR="$ROOT_DIR/.runtime-cache/full-stack"
FALLBACK_MARKER_FILE="$FALLBACK_MARKER_DIR/offline-fallback.flag"

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }
fail() { log "ERROR: $*"; exit 1; }

apply_psql_migrations() {
  local psql_url="$1"
  local migration
  for migration in $(cd "$ROOT_DIR" && ls infra/migrations/*.sql | sort); do
    psql "$psql_url" -v ON_ERROR_STOP=1 -f "$ROOT_DIR/$migration" >/dev/null
  done
}

is_truthy() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

mark_offline_fallback() {
  local reason="$1"
  mkdir -p "$FALLBACK_MARKER_DIR"
  {
    echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "reason=${reason}"
  } > "$FALLBACK_MARKER_FILE"
  log "OFFLINE_FALLBACK active: ${reason}"
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
    return $?
  fi
  return 1
}

pick_free_port() {
  local preferred="$1"
  shift
  local candidate
  if ! port_in_use "$preferred"; then
    echo "$preferred"
    return 0
  fi
  for candidate in "$@"; do
    if ! port_in_use "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done
  fail "no free port found from candidates: $preferred $*"
}

usage() {
  cat <<'EOF'
Usage: ./scripts/bootstrap_full_stack.sh [--profile local|gce] [--install-deps 0|1] [--with-core-services 0|1] [--with-reader-stack 0|1] [--reader-env-file <path>] [--offline-fallback 0|1]

Goal:
  Clone repo and reach runnable state for 80%+ functionality.

Examples:
  ./scripts/bootstrap_full_stack.sh
  ./scripts/bootstrap_full_stack.sh --profile gce --with-reader-stack 1 --reader-env-file env/profiles/reader.env
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --install-deps) INSTALL_DEPS="$2"; shift 2 ;;
    --with-core-services) WITH_CORE_SERVICES="$2"; shift 2 ;;
    --with-reader-stack) WITH_READER_STACK="$2"; shift 2 ;;
    --reader-env-file) READER_ENV_FILE="$2"; shift 2 ;;
    --offline-fallback) OFFLINE_FALLBACK="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[[ "$PROFILE" == "local" || "$PROFILE" == "gce" ]] || fail "--profile must be local|gce"
rm -f "$FALLBACK_MARKER_FILE"

command -v python3 >/dev/null 2>&1 || fail "python3 not found"
command -v uv >/dev/null 2>&1 || fail "uv not found"
command -v npm >/dev/null 2>&1 || fail "npm not found"

if is_truthy "$INSTALL_DEPS"; then
  log "Installing Python deps via uv"
  (cd "$ROOT_DIR" && uv sync --frozen --extra dev --extra e2e)
  log "Installing Web deps via npm ci"
  (cd "$ROOT_DIR" && npm --prefix apps/web ci)
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  log "No .env found, creating from .env.example"
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if grep -q "postgresql+psycopg://localhost:5432/video_analysis" "$ROOT_DIR/.env"; then
  log "Upgrading DATABASE_URL in .env for dockerized postgres compatibility"
  sed -i.bak "s|postgresql+psycopg://localhost:5432/video_analysis|postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis|g" "$ROOT_DIR/.env"
fi

load_repo_env "$ROOT_DIR" "$SCRIPT_NAME"

API_PORT_CURRENT="${API_PORT:-8000}"
WEB_PORT_CURRENT="${WEB_PORT:-3000}"
API_PORT_PICKED="$(pick_free_port "$API_PORT_CURRENT" 18000 18001 18002)"
WEB_PORT_PICKED="$(pick_free_port "$WEB_PORT_CURRENT" 13000 13001 13002)"
if is_truthy "$WITH_READER_STACK"; then
  NEXTFLUX_PORT_CURRENT="${NEXTFLUX_PORT:-3000}"
  if [[ "$WEB_PORT_PICKED" == "$NEXTFLUX_PORT_CURRENT" ]]; then
    WEB_PORT_PICKED="$(pick_free_port 3001 13000 13001 13002)"
  fi
fi
if [[ "$API_PORT_PICKED" != "$API_PORT_CURRENT" || "$WEB_PORT_PICKED" != "$WEB_PORT_CURRENT" ]]; then
  log "Port conflict detected; applying API_PORT=${API_PORT_PICKED}, WEB_PORT=${WEB_PORT_PICKED}"
  cat >> "$ROOT_DIR/.env" <<EOF
export API_PORT='${API_PORT_PICKED}'
export WEB_PORT='${WEB_PORT_PICKED}'
export VD_API_BASE_URL='http://127.0.0.1:${API_PORT_PICKED}'
export NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:${API_PORT_PICKED}'
export WEB_BASE_URL='http://127.0.0.1:${WEB_PORT_PICKED}'
EOF
fi

log "Validating env contract"
(cd "$ROOT_DIR" && python3 scripts/check_env_contract.py --strict)

if is_truthy "$WITH_CORE_SERVICES"; then
  command -v docker >/dev/null 2>&1 || fail "docker not found; required for core services"
  log "Starting core services (postgres/redis/temporal)"
  if ! (cd "$ROOT_DIR" && ./scripts/deploy_core_services.sh up --env-file "$ROOT_DIR/.env"); then
    if is_truthy "$OFFLINE_FALLBACK"; then
      mark_offline_fallback "core_services_start_failed"
      log "Continuing without dockerized core services."
    else
      fail "core services failed and OFFLINE_FALLBACK=0"
    fi
  fi
fi

if command -v psql >/dev/null 2>&1; then
  DB_URL="${DATABASE_URL:-postgresql+psycopg://localhost:5432/video_analysis}"
  PSQL_URL="${DB_URL/postgresql+psycopg:\/\//postgresql://}"
  if [[ "$DB_URL" == postgresql* ]]; then
    DB_NAME="$(python3 - <<'PY'
import os
from urllib.parse import urlparse
u = os.getenv('DATABASE_URL', 'postgresql+psycopg://localhost:5432/video_analysis')
u = u.replace('postgresql+psycopg://', 'postgresql://', 1)
path = urlparse(u).path.strip('/')
print(path or 'video_analysis')
PY
)"
    DB_CONN_JSON="$(PSQL_URL="$PSQL_URL" python3 - <<'PY'
import json, os
from urllib.parse import urlparse
u = os.getenv('PSQL_URL','postgresql://localhost:5432/video_analysis')
p = urlparse(u)
print(json.dumps({
  'host': p.hostname or '127.0.0.1',
  'port': p.port or 5432,
  'user': p.username or '',
  'password': p.password or '',
}))
PY
)"
    DB_HOST="$(DB_CONN_JSON="$DB_CONN_JSON" python3 - <<'PY'
import json, os
print(json.loads(os.environ['DB_CONN_JSON'])['host'])
PY
)"
    DB_PORT="$(DB_CONN_JSON="$DB_CONN_JSON" python3 - <<'PY'
import json, os
print(json.loads(os.environ['DB_CONN_JSON'])['port'])
PY
)"
    DB_USER="$(DB_CONN_JSON="$DB_CONN_JSON" python3 - <<'PY'
import json, os
print(json.loads(os.environ['DB_CONN_JSON'])['user'])
PY
)"
    DB_PASSWORD="$(DB_CONN_JSON="$DB_CONN_JSON" python3 - <<'PY'
import json, os
print(json.loads(os.environ['DB_CONN_JSON'])['password'])
PY
)"
    log "Ensuring database exists: ${DB_NAME}"
    if [[ -n "$DB_USER" ]]; then
      PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true
    else
      createdb "$DB_NAME" 2>/dev/null || true
    fi
    log "Applying SQL migrations"
    if ! apply_psql_migrations "$PSQL_URL"; then
      FALLBACK_DB_NAME="${DB_NAME}_bootstrap"
      log "Primary DB migration failed; falling back to isolated DB: ${FALLBACK_DB_NAME}"
      if [[ -n "$DB_USER" ]]; then
        PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$FALLBACK_DB_NAME" >/dev/null 2>&1 || true
        PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$FALLBACK_DB_NAME" >/dev/null
      else
        dropdb --if-exists "$FALLBACK_DB_NAME" >/dev/null 2>&1 || true
        createdb "$FALLBACK_DB_NAME" >/dev/null
      fi
      FALLBACK_PSQL_URL="$(PSQL_URL="$PSQL_URL" FALLBACK_DB_NAME="$FALLBACK_DB_NAME" python3 - <<'PY'
import os
from urllib.parse import urlparse, urlunparse
u = os.getenv('PSQL_URL')
p = urlparse(u)
fallback_db = os.getenv('FALLBACK_DB_NAME')
new_path = '/' + fallback_db
print(urlunparse((p.scheme, p.netloc, new_path, p.params, p.query, p.fragment)))
PY
)"
      apply_psql_migrations "$FALLBACK_PSQL_URL"
      FALLBACK_DB_URL="${FALLBACK_PSQL_URL/postgresql:\/\//postgresql+psycopg://}"
      log "Updating .env DATABASE_URL to isolated DB: ${FALLBACK_DB_URL}"
      perl -0pi -e "s|export DATABASE_URL='[^']*'|export DATABASE_URL='${FALLBACK_DB_URL}'|g" "$ROOT_DIR/.env"
      export DATABASE_URL="$FALLBACK_DB_URL"
    fi
  else
    log "Skip psql migrations: DATABASE_URL is not PostgreSQL (${DB_URL})"
  fi
else
  log "Skip psql migrations: psql not found"
fi

if [[ -n "${SQLITE_PATH:-}" ]] && command -v sqlite3 >/dev/null 2>&1; then
  log "Applying SQLite state init"
  sqlite3 "$SQLITE_PATH" < "$ROOT_DIR/infra/sql/sqlite_state_init.sql"
fi

if is_truthy "$WITH_READER_STACK"; then
  command -v docker >/dev/null 2>&1 || fail "docker not found; required for reader stack"
  if [[ ! -f "$READER_ENV_FILE" ]]; then
    log "Reader env not found, creating template at $READER_ENV_FILE"
    mkdir -p "$(dirname "$READER_ENV_FILE")"
    cp "$ROOT_DIR/env/profiles/reader.env" "$READER_ENV_FILE"
    log "Template created. Update credentials in $READER_ENV_FILE before deploy."
  fi
  log "Starting reader stack"
  if ! (cd "$ROOT_DIR" && ./scripts/deploy_reader_stack.sh up --env-file "$READER_ENV_FILE"); then
    if is_truthy "$OFFLINE_FALLBACK"; then
      mark_offline_fallback "reader_stack_start_failed"
      log "Continuing without reader stack."
    else
      fail "reader stack failed and OFFLINE_FALLBACK=0"
    fi
  fi
fi

cat <<EOF
[$SCRIPT_NAME] Bootstrap complete.
[$SCRIPT_NAME] Next:
[$SCRIPT_NAME]   1) ./scripts/full_stack.sh up
[$SCRIPT_NAME]   2) ./scripts/smoke_full_stack.sh
[$SCRIPT_NAME] Optional reader stack docs:
[$SCRIPT_NAME]   docs/deploy/miniflux-nextflux-gce.md
EOF
