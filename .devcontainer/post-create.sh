#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user --upgrade "uv>=0.10,<1.0"
fi

uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci

# Browser install is best-effort in devcontainer; CI remains the source of truth.
uv run --with playwright python -m playwright install chromium || true

python3 scripts/check_env_contract.py --strict --env-file .env.example
