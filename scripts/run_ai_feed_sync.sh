#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./scripts/lib/load_env.sh
source "$ROOT_DIR/scripts/lib/load_env.sh"
load_repo_env "$ROOT_DIR" "run_ai_feed_sync"

if [[ -f "$ROOT_DIR/.env.reader-stack" ]]; then
  load_env_file "$ROOT_DIR/.env.reader-stack" "run_ai_feed_sync"
fi

exec python3 "$ROOT_DIR/scripts/sync_ai_feed_to_miniflux.py"
