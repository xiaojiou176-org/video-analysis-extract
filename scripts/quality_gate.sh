#!/usr/bin/env bash
set -euo pipefail

echo "[quality-gate] env contract"
python3 scripts/check_env_contract.py --strict

echo "[quality-gate] placebo assertion guard"
python3 scripts/check_test_assertions.py

echo "[quality-gate] backend lint (ruff critical rules)"
uv run --with ruff ruff check apps scripts --select E9,F63,F7,F82

echo "[quality-gate] web lint"
npm --prefix apps/web run lint

echo "[quality-gate] web unit tests"
npm --prefix apps/web run test

echo "[quality-gate] python tests"
PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL="sqlite+pysqlite:///:memory:" \
uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q

echo "[quality-gate] all checks passed"
