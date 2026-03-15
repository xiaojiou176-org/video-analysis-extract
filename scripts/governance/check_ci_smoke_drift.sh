#!/usr/bin/env bash
set -euo pipefail

workflow_file=".github/workflows/ci.yml"

[[ -f "$workflow_file" ]] || {
  echo "[check_ci_smoke_drift] missing workflow file: $workflow_file" >&2
  exit 1
}

required_patterns=(
  "pr-llm-real-smoke:"
  "./bin/strict-ci --mode pr-llm-real-smoke"
  "ci-failure-diagnostics-pr-llm-real-smoke"
  "external-playwright-smoke:"
  "scripts/ci/external_playwright_smoke.sh"
  "--url \"\${{ vars.EXTERNAL_SMOKE_URL || 'https://example.com' }}\""
  "--expect-text \"\${{ vars.EXTERNAL_SMOKE_EXPECT_TEXT || 'Example Domain' }}\""
  "--timeout-ms \"\${{ vars.EXTERNAL_SMOKE_TIMEOUT_MS || '45000' }}\""
  "--retries \"\${{ vars.EXTERNAL_SMOKE_RETRIES || '2' }}\""
  "live-smoke:"
  "./bin/strict-ci --mode live-smoke"
  "GEMINI_API_KEY"
  "RESEND_API_KEY"
  "YOUTUBE_API_KEY"
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

required_repo_scripts=(
  "scripts/ci/pr_llm_real_smoke.sh"
  "scripts/ci/live_smoke.sh"
)
for path in "${required_repo_scripts[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "[check_ci_smoke_drift] missing required repo smoke script: $path" >&2
    exit 1
  fi
done

unexpected=()
for pattern in "${forbidden_patterns[@]}"; do
  if has_pattern "$pattern"; then
    unexpected+=("$pattern")
  fi
done

if [[ ${#unexpected[@]} -gt 0 ]]; then
  {
    echo "[check_ci_smoke_drift] unexpected deprecated env wiring found:"
    for item in "${unexpected[@]}"; do
      echo "  - $item"
    done
  } >&2
  exit 1
fi

echo "[check_ci_smoke_drift] passed"
