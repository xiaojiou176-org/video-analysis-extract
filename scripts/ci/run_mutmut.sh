#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR_ROOT="$ROOT_DIR/.runtime-cache/temp/mutation/workdir"
WORKSPACE="$WORKDIR_ROOT/repo"
REPORT_DIR="$ROOT_DIR/.runtime-cache/reports/mutation"
REPORT_PATH="$REPORT_DIR/mutmut-cicd-stats.json"

TOP_LEVEL_ITEMS=(
  AGENTS.md
  CLAUDE.md
  README.md
  ENVIRONMENT.md
  .env.example
  apps
  config
  data
  docs
  env
  infra
  packages
  scripts
  templates
  pyproject.toml
  uv.lock
)

mkdir -p "$WORKDIR_ROOT" "$REPORT_DIR"
find "$WORKDIR_ROOT" -mindepth 1 -delete 2>/dev/null || true
mkdir -p "$WORKSPACE"

for item in "${TOP_LEVEL_ITEMS[@]}"; do
  if [[ -e "$ROOT_DIR/$item" ]]; then
    ln -s "$ROOT_DIR/$item" "$WORKSPACE/$item"
  fi
done

mkdir -p "$WORKSPACE/.runtime-cache/temp" "$WORKSPACE/.runtime-cache/reports"

(
  cd "$WORKSPACE"
  DATABASE_URL='sqlite+pysqlite:///:memory:' \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$WORKSPACE:$WORKSPACE/apps/worker" \
    uv run --extra dev --with mutmut mutmut run
  PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$WORKSPACE:$WORKSPACE/apps/worker" \
    uv run --extra dev --with mutmut mutmut export-cicd-stats
)

cp "$WORKSPACE/mutants/mutmut-cicd-stats.json" "$REPORT_PATH"
echo "[run_mutmut] exported stats to $REPORT_PATH"
