#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKDIR_ROOT="${MUTATION_WORKDIR_ROOT:-/tmp/video-digestor-mutation/workdir}"
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
  integrations
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

mkdir -p "$WORKSPACE/.runtime-cache/tmp" "$WORKSPACE/.runtime-cache/reports"

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
python3 - <<'PY' "$REPORT_PATH"
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import write_runtime_metadata  # noqa: E402

report_path = Path(sys.argv[1])
write_runtime_metadata(
    report_path,
    source_entrypoint="scripts/ci/run_mutmut.sh",
    verification_scope="mutation-cicd-stats",
    source_run_id="mutation-cicd-stats",
    freshness_window_hours=24,
    extra={"report_kind": "mutation-cicd-stats"},
)
PY
echo "[run_mutmut] exported stats to $REPORT_PATH"
