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
  "live-smoke:"
  "scripts/e2e_live_smoke.sh"
  "--api-base-url \"http://127.0.0.1:18080\""
  "--require-api \"1\""
  "--require-secrets \"1\""
  "--computer-use-strict \"1\""
  "--computer-use-skip \"0\""
  "--timeout-seconds \"600\""
  "--diagnostics-json \".runtime-cache/e2e-live-smoke-result.json\""
  "--heartbeat-seconds \"30\""
)

forbidden_patterns=(
  "LIVE_SMOKE_REQUIRE_API: \"1\""
  "LIVE_SMOKE_REQUIRE_SECRETS: \"1\""
  "LIVE_SMOKE_COMPUTER_USE_STRICT: \"1\""
  "LIVE_SMOKE_COMPUTER_USE_SKIP: \"0\""
)

missing=()
has_pattern() {
  local pattern="$1"
  if command -v rg >/dev/null 2>&1; then
    rg -n --fixed-strings -- "$pattern" "$workflow_file" >/dev/null
  else
    grep -nF -- "$pattern" "$workflow_file" >/dev/null
  fi
}

for pattern in "${required_patterns[@]}"; do
  if ! has_pattern "$pattern"; then
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

unexpected=()
for pattern in "${forbidden_patterns[@]}"; do
  if has_pattern "$pattern"; then
    unexpected+=("$pattern")
  fi
done

if [[ ${#unexpected[@]} -gt 0 ]]; then
  {
    echo "[check_ci_smoke_drift] unexpected legacy env wiring found:"
    for item in "${unexpected[@]}"; do
      echo "  - $item"
    done
  } >&2
  exit 1
fi

echo "[check_ci_smoke_drift] passed"
