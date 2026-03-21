#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

find ".runtime-cache/tmp" -mindepth 1 -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find ".runtime-cache/run" -mindepth 1 -mtime +1 -exec rm -rf {} + 2>/dev/null || true
find ".runtime-cache/evidence" -mindepth 1 -mtime +14 -exec rm -rf {} + 2>/dev/null || true
find ".runtime-cache/logs" -type f -mtime +30 -delete 2>/dev/null || true
find ".runtime-cache/reports" -type f -mtime +30 -delete 2>/dev/null || true
find ".runtime-cache/tmp" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

echo "[prune-runtime-state] pruned internal runtime state under .runtime-cache using built-in TTL policy"
