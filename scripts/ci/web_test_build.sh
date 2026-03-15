#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
eval "$(python3 scripts/ci/contract.py shell-exports)"

if [[ "${STRICT_CI_BOOTSTRAP_RUNTIME_READY:-0}" != "1" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/scripts/ci/bootstrap_strict_ci_runtime.sh"
fi

mkdir -p .runtime-cache/reports/ui-audit
uv sync --frozen --extra dev --extra e2e
eval "$(bash scripts/ci/prepare_web_runtime.sh --shell-exports)"
export VIDEO_ANALYSIS_REPO_ROOT="$ROOT_DIR"

base_ref="${CI_BASE_REF:-}"
head_ref="${CI_HEAD_SHA:-HEAD}"
if [[ -n "$base_ref" ]]; then
  python3 scripts/governance/check_design_tokens.py \
    --from-ref "$base_ref" \
    --to-ref "$head_ref" \
    apps/web
else
  python3 scripts/governance/check_design_tokens.py --all-lines apps/web
fi

VIDEO_ANALYSIS_REPO_ROOT="$ROOT_DIR" npm --prefix "$WEB_RUNTIME_WEB_DIR" run test:coverage
python3 scripts/governance/check_web_coverage_threshold.py \
  --summary-path .runtime-cache/reports/web-coverage/coverage-summary.json \
  --global-threshold "$STRICT_CI_COVERAGE_MIN" \
  --core-threshold "$STRICT_CI_CORE_COVERAGE_MIN" \
  --metric lines \
  --metric functions \
  --metric branches
VIDEO_ANALYSIS_REPO_ROOT="$ROOT_DIR" npm --prefix "$WEB_RUNTIME_WEB_DIR" run build
python3 scripts/governance/check_web_button_coverage.py \
  --threshold "$STRICT_CI_WEB_BUTTON_COMBINED_THRESHOLD" \
  --e2e-threshold "$STRICT_CI_WEB_BUTTON_E2E_THRESHOLD" \
  --unit-threshold "$STRICT_CI_WEB_BUTTON_UNIT_THRESHOLD"
