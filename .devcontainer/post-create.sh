#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
eval "$(python3 scripts/ci/contract.py shell-exports)"

if [[ "${PWD}" != "${STRICT_CI_DEVCONTAINER_WORKSPACE_FOLDER}" ]]; then
  echo "[devcontainer] expected workspace folder ${STRICT_CI_DEVCONTAINER_WORKSPACE_FOLDER}, got ${PWD}" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user --upgrade "uv==${STRICT_CI_UV_VERSION}"
fi

export UV_CACHE_DIR="${STRICT_CI_UV_CACHE_DIR}"
export PLAYWRIGHT_BROWSERS_PATH="${STRICT_CI_PLAYWRIGHT_BROWSERS_PATH}"
export PRE_COMMIT_HOME="${STRICT_CI_PRE_COMMIT_HOME}"

if ! uv --version | grep -q " ${STRICT_CI_UV_VERSION}$"; then
  echo "[devcontainer] uv version drift detected; expected ${STRICT_CI_UV_VERSION}" >&2
  exit 1
fi

uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci

node_major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
if [[ "${node_major}" != "${STRICT_CI_NODE_MAJOR}" ]]; then
  echo "[devcontainer] node major drift detected; expected ${STRICT_CI_NODE_MAJOR}, got ${node_major}" >&2
  exit 1
fi

if ! uv run --with playwright python - <<'PY' >/dev/null
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    browser.close()
PY
then
  echo "[devcontainer] chromium browser drift detected; rebuild the strict standard image" >&2
  exit 1
fi

python3 scripts/governance/check_env_contract.py --strict --env-file .env.example
