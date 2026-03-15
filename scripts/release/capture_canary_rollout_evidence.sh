#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RELEASE_TAG="${1:-$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo v0.0.0)}"
RELEASE_DIR="$REPO_ROOT/artifacts/releases/$RELEASE_TAG"
CANARY_DIR="$RELEASE_DIR/canary"
EVIDENCE_JSON="$CANARY_DIR/canary-rollout-evidence.json"
EVIDENCE_LOG="$CANARY_DIR/canary-rollout-dryrun.log"
TMP_ROUTING="$REPO_ROOT/.runtime-cache/tmp/release-readiness/canary-routing.dryrun.conf"

mkdir -p "$CANARY_DIR" "$(dirname "$TMP_ROUTING")"

{
  echo "[capture_canary_rollout_evidence] release_tag=$RELEASE_TAG"
  echo "[capture_canary_rollout_evidence] script=scripts/deploy/canary_rollout.sh"
  echo "[capture_canary_rollout_evidence] mode=dry-run"
  echo
  bash "$REPO_ROOT/scripts/deploy/canary_rollout.sh" \
    --target 10 \
    --step 5 \
    --settle-seconds 1 \
    --routing-snippet "$TMP_ROUTING" \
    --dry-run 1
} >"$EVIDENCE_LOG" 2>&1

python3 - "$EVIDENCE_JSON" "$EVIDENCE_LOG" "$RELEASE_TAG" <<'PY'
import json
import os
import sys
from datetime import UTC, datetime

output_path, log_path, release_tag = sys.argv[1], sys.argv[2], sys.argv[3]
payload = {
    "release_tag": release_tag,
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "dry-run",
    "script": "scripts/deploy/canary_rollout.sh",
    "command": (
        "scripts/deploy/canary_rollout.sh --target 10 --step 5 "
        "--settle-seconds 1 --routing-snippet <tmp> --dry-run 1"
    ),
    "log_file": os.path.relpath(log_path),
}
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(output_path)
PY

echo "$EVIDENCE_JSON"
echo "$EVIDENCE_LOG"
