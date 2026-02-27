#!/usr/bin/env bash
set -euo pipefail

workflow_file=".github/workflows/ci.yml"

[[ -f "$workflow_file" ]] || {
  echo "[check_ci_smoke_drift] missing workflow file: $workflow_file" >&2
  exit 1
}

required_patterns=(
  "pr-llm-real-smoke:"
  "scripts/smoke_llm_real_local.sh"
  "--api-base-url \"http://127.0.0.1:18081\""
  "--diagnostics-json \".runtime-cache/pr-llm-real-smoke-result.json\""
  "--heartbeat-seconds \"30\""
  "--max-retries \"2\""
  "ci-failure-diagnostics-pr-llm-real-smoke"
  "external-playwright-smoke:"
  "scripts/external_playwright_smoke.sh"
  "--url \"\${{ vars.EXTERNAL_SMOKE_URL || 'https://example.com' }}\""
  "--expect-text \"\${{ vars.EXTERNAL_SMOKE_EXPECT_TEXT || 'Example Domain' }}\""
  "--timeout-ms \"\${{ vars.EXTERNAL_SMOKE_TIMEOUT_MS || '45000' }}\""
  "--retries \"\${{ vars.EXTERNAL_SMOKE_RETRIES || '2' }}\""
)

missing=()
for pattern in "${required_patterns[@]}"; do
  if ! rg -n --fixed-strings -- "$pattern" "$workflow_file" >/dev/null; then
    missing+=("$pattern")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  {
    echo "[check_ci_smoke_drift] missing required CI smoke fields:"
    for item in "${missing[@]}"; do
      echo "  - $item"
    done
  } >&2
  exit 1
fi

echo "[check_ci_smoke_drift] passed"
