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
  ".github"
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
  -i
  --pcre2
  --color=never
  -e "\\bopenai\\b"
  -e "OPENAI_"
  -e "api\\.openai\\.com"
  -e "\\bfrom\\s+openai\\s+import\\b"
  -e "\\bimport\\s+openai\\b"
  -e "\\bAsync?OpenAI\\b"
  -e "\\bOpenAI\\s*\\("
  -e "\\bclient\\.responses\\.create\\b"
  -e "\\bclient\\.chat\\.completions\\.create\\b"
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
