#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
eval "$(python3 scripts/ci_contract.py shell-exports)"

mkdir -p .runtime-cache/ui-audit
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci

base_ref="${CI_BASE_REF:-}"
head_ref="${CI_HEAD_SHA:-HEAD}"
if [[ -n "$base_ref" ]]; then
  python3 scripts/check_design_tokens.py \
    --from-ref "$base_ref" \
    --to-ref "$head_ref" \
    apps/web
else
  python3 scripts/check_design_tokens.py --all-lines apps/web
fi

npm --prefix apps/web run test:coverage
python3 scripts/check_web_coverage_threshold.py \
  --summary-path apps/web/coverage/coverage-summary.json \
  --global-threshold "$STRICT_CI_COVERAGE_MIN" \
  --core-threshold "$STRICT_CI_CORE_COVERAGE_MIN" \
  --metric lines \
  --metric functions \
  --metric branches
npm --prefix apps/web run build
python3 scripts/check_web_button_coverage.py \
  --threshold "$STRICT_CI_WEB_BUTTON_COMBINED_THRESHOLD" \
  --e2e-threshold "$STRICT_CI_WEB_BUTTON_E2E_THRESHOLD" \
  --unit-threshold "$STRICT_CI_WEB_BUTTON_UNIT_THRESHOLD"
