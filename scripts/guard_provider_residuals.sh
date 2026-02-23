#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

# Minimal allowlist: guard implementation itself + workflow wiring + historical planning note.
ALLOWLIST=(
  ".github/workflows/ci.yml"
  "scripts/guard_provider_residuals.sh"
  "Gemini 3 生态代码库深度治理与重构计划.md"
)

TARGETS=(
  "apps"
  "docs"
  "infra"
  "packages"
  "scripts"
  "README.md"
  "ENVIRONMENT.md"
)

RG_ARGS=(
  -n
  --color=never
  -e "\\bopenai\\b"
  -e "\\bOpenAI\\b"
  -e "OPENAI_"
  -e "chat\\.completions"
  -e "responses\\.create"
  -e "gpt-"
)

for file in "${ALLOWLIST[@]}"; do
  RG_ARGS+=(--glob "!$file")
done

if rg "${RG_ARGS[@]}" "${TARGETS[@]}"; then
  echo ""
  echo "provider residual guard failed: forbidden provider-specific tokens detected."
  exit 1
fi

echo "provider residual guard passed: no forbidden provider-specific tokens found."
