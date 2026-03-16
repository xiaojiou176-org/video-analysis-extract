#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

rm -rf \
  .runtime-cache \
  .coverage \
  .pytest_cache \
  .ruff_cache \
  logs \
  mutants \
  scripts/.runtime-cache \
  scripts/ci/__pycache__ \
  scripts/governance/__pycache__ \
  scripts/runtime/__pycache__ \
  apps/web/coverage \
  apps/web/.vitest-coverage

python3 scripts/runtime/clean_source_runtime_residue.py --apply >/dev/null 2>&1 || true

echo "[clean-runtime-state] cleaned runtime caches and transient reports"
