#!/usr/bin/env bash
set -euo pipefail

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push .githooks/commit-msg
chmod +x scripts/quality_gate.sh scripts/ci_or_local_gate_doc_drift.sh

echo "Git hooks installed: pre-commit + pre-push + commit-msg (quality gate wired)"
echo "hooksPath: $(git config --get core.hooksPath)"

for hook in pre-commit pre-push commit-msg; do
  if [[ -f ".githooks/$hook" && -x ".githooks/$hook" ]]; then
    echo ".githooks/$hook: executable"
  else
    echo ".githooks/$hook: NOT executable"
  fi
done
