#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p .runtime-cache
export API_INTEGRATION_SMOKE_STRICT="${API_INTEGRATION_SMOKE_STRICT:-1}"

uv sync --frozen --extra dev --extra e2e
./scripts/api_real_smoke_local.sh --profile ci "$@"
