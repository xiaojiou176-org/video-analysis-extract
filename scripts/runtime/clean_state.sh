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

echo "[clean-runtime-state] cleaned runtime caches and transient reports"
