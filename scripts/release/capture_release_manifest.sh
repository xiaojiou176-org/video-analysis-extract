#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="capture_release_manifest"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RELEASE_TAG="${1:-}"
OUT_DIR="${2:-$ROOT_DIR/artifacts/releases}"

if [[ -z "$RELEASE_TAG" ]]; then
  echo "[$SCRIPT_NAME] usage: $0 <release-tag> [output-dir]" >&2
  exit 2
fi

if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[$SCRIPT_NAME] not a git repository: $ROOT_DIR" >&2
  exit 1
fi

release_dir="$OUT_DIR/$RELEASE_TAG"
mkdir -p "$release_dir"

manifest_path="$release_dir/manifest.json"
checksums_path="$release_dir/checksums.sha256"
rollback_dir="$release_dir/rollback"
rollback_readiness_path="$rollback_dir/db-rollback-readiness.json"
rollback_drill_path="$rollback_dir/drill.json"

(
  cd "$ROOT_DIR"
  {
    [[ -f uv.lock ]] && sha256sum uv.lock
    [[ -f .env.example ]] && sha256sum .env.example
    [[ -f apps/web/package-lock.json ]] && sha256sum apps/web/package-lock.json
    find infra/migrations -maxdepth 1 -type f -name '*.sql' | sort | while read -r f; do
      sha256sum "$f"
    done
  } > "$checksums_path"
)

python3 "$ROOT_DIR/scripts/release/verify_db_rollback_readiness.py" \
  --repo-root "$ROOT_DIR" \
  --release-tag "$RELEASE_TAG" \
  --write-drill-template \
  --output "$rollback_readiness_path"

python3 - "$ROOT_DIR" "$RELEASE_TAG" "$manifest_path" "$checksums_path" "$rollback_readiness_path" "$rollback_drill_path" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
release_tag = sys.argv[2]
manifest_path = Path(sys.argv[3])
checksums_path = Path(sys.argv[4])
rollback_readiness_path = Path(sys.argv[5])
rollback_drill_path = Path(sys.argv[6])


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=root, text=True).strip()


head_sha = run(["git", "rev-parse", "HEAD"])
branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
status_short = run(["git", "status", "--short"])
latest_tag = ""
try:
    latest_tag = run(["git", "describe", "--tags", "--abbrev=0"])
except Exception:
    latest_tag = ""

manifest = {
    "manifest_version": 1,
    "release_tag": release_tag,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "evidence_scope": "current-run",
    "git": {
        "head_sha": head_sha,
        "branch": branch,
        "latest_tag": latest_tag,
        "dirty": bool(status_short.strip()),
    },
    "artifacts": {
        "checksums_file": checksums_path.relative_to(root).as_posix(),
        "rollback_readiness_file": rollback_readiness_path.relative_to(root).as_posix(),
        "rollback_drill_file": rollback_drill_path.relative_to(root).as_posix(),
    },
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

echo "[$SCRIPT_NAME] manifest: $manifest_path"
echo "[$SCRIPT_NAME] checksums: $checksums_path"
echo "[$SCRIPT_NAME] rollback_readiness: $rollback_readiness_path"
echo "[$SCRIPT_NAME] rollback_drill_template: $rollback_drill_path"
