#!/usr/bin/env bash
set -euo pipefail

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/pre-push
chmod +x scripts/quality_gate.sh scripts/ci_or_local_gate_doc_drift.sh

echo "Git hooks installed: pre-commit + pre-push (quality gate wired)"
