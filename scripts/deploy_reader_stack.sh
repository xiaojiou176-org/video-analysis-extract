#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/compose/miniflux-nextflux.compose.yml"
ENV_FILE="$ROOT_DIR/.env.reader-stack"

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy_reader_stack.sh [up|down|restart|status|logs] [--env-file <path>]

Commands:
  up       Start Miniflux + Nextflux stack in background (default)
  down     Stop and remove stack containers
  restart  Restart stack
  status   Show stack status
  logs     Tail stack logs

Notes:
  1) Default env file: .env.reader-stack
  2) Copy env template:
     cp .env.example .env.reader-stack
  3) Required before first `up`:
     - MINIFLUX_DB_PASSWORD
     - MINIFLUX_ADMIN_PASSWORD
     - MINIFLUX_BASE_URL (public URL for your deployment)
EOF
}

ensure_compose() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[reader-stack] docker not found" >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "[reader-stack] docker compose not available" >&2
    exit 1
  fi
}

read_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "[reader-stack] env file not found: $ENV_FILE" >&2
    echo "[reader-stack] create one from template, e.g. cp .env.example .env.reader-stack" >&2
    exit 1
  fi
}

command="up"
while [[ $# -gt 0 ]]; do
  case "$1" in
    up|down|restart|status|logs)
      command="$1"
      shift
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[reader-stack] unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

ensure_compose
read_env_file

case "$command" in
  up)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    ;;
  down)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
    ;;
  restart)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    ;;
  status)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
    ;;
  logs)
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f --tail=200
    ;;
  *)
    echo "[reader-stack] unsupported command: $command" >&2
    exit 1
    ;;
esac
