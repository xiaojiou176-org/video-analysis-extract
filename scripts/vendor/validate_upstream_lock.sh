#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="validate_upstream_lock"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

STRICT_NO_FILES=0
DRY_RUN=0
SEARCH_ROOT="$ROOT_DIR"
declare -a TARGET_FILES=()

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/vendor/validate_upstream_lock.sh [--root <dir>] [--strict-no-files]
  scripts/vendor/validate_upstream_lock.sh --file <path/to/UPSTREAM.lock> [--file ...]
  scripts/vendor/validate_upstream_lock.sh --root . --dry-run

Options:
  --root <dir>          Scan directory recursively for files named UPSTREAM.lock.
  --file <path>         Validate specific lock file (can repeat).
  --strict-no-files     Fail when no UPSTREAM.lock is found.
  --dry-run             Only print candidate files without validating content.
  -h, --help            Show this message.
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --root) SEARCH_ROOT="${2:-}"; shift 2 ;;
      --file) TARGET_FILES+=("${2:-}"); shift 2 ;;
      --strict-no-files) STRICT_NO_FILES=1; shift ;;
      --dry-run) DRY_RUN=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) fail "unknown argument: $1 (use --help)" ;;
    esac
  done
}

discover_files() {
  if [[ "${#TARGET_FILES[@]}" -gt 0 ]]; then
    return 0
  fi
  while IFS= read -r file; do
    TARGET_FILES+=("$file")
  done < <(find "$SEARCH_ROOT" -type f -name 'UPSTREAM.lock' | sort)
}

validate_file() {
  local file_path="$1"
  [[ -f "$file_path" ]] || fail "file not found: $file_path"
  python3 - "$file_path" <<'PY'
import re
import sys
from pathlib import Path

file_path = Path(sys.argv[1])
text = file_path.read_text(encoding="utf-8")

required_fields = [
    "schema_version",
    "vendor",
    "upstream_repo",
    "upstream_ref",
    "upstream_commit",
    "subtree_prefix",
    "sync_strategy",
    "sync_timestamp_utc",
    "sync_actor",
]

kv: dict[str, str] = {}
for line_no, raw in enumerate(text.splitlines(), 1):
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    m = re.match(r"^([a-z_][a-z0-9_]*)\s*:\s*(.+)$", line)
    if not m:
        raise SystemExit(f"{file_path}:{line_no} invalid line format: {raw}")
    key, value = m.group(1), m.group(2).strip().strip("\"'")
    if not value:
        raise SystemExit(f"{file_path}:{line_no} empty value for key: {key}")
    kv[key] = value

for req in required_fields:
    if not kv.get(req):
        raise SystemExit(f"{file_path} missing required field: {req}")

if kv["sync_strategy"] != "subtree":
    raise SystemExit(f"{file_path} sync_strategy must be subtree")
if not re.match(r"^(1|v1)$", kv["schema_version"]):
    raise SystemExit(f"{file_path} schema_version must be 1 or v1")
if not re.match(r"^[A-Za-z0-9._-]+$", kv["vendor"]):
    raise SystemExit(f"{file_path} vendor contains invalid characters")
if not re.match(r"^(https://|git@).+", kv["upstream_repo"]):
    raise SystemExit(f"{file_path} upstream_repo must start with https:// or git@")
if not re.match(r"^[A-Za-z0-9._/\-]+$", kv["upstream_ref"]):
    raise SystemExit(f"{file_path} upstream_ref contains invalid characters")
if not re.match(r"^[0-9a-fA-F]{7,40}$", kv["upstream_commit"]):
    raise SystemExit(f"{file_path} upstream_commit must be 7-40 hex chars")
if not re.match(r"^vendor/[A-Za-z0-9._/\-]+$", kv["subtree_prefix"]):
    raise SystemExit(f"{file_path} subtree_prefix must start with vendor/")
if ".." in kv["subtree_prefix"]:
    raise SystemExit(f"{file_path} subtree_prefix cannot contain '..'")
if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", kv["sync_timestamp_utc"]):
    raise SystemExit(f"{file_path} sync_timestamp_utc must be UTC ISO8601 (YYYY-MM-DDTHH:MM:SSZ)")
PY
}

main() {
  parse_args "$@"
  discover_files

  if [[ "${#TARGET_FILES[@]}" -eq 0 ]]; then
    if [[ "$STRICT_NO_FILES" -eq 1 ]]; then
      fail "no UPSTREAM.lock files found under: $SEARCH_ROOT"
    fi
    log "no UPSTREAM.lock files found, skipping."
    exit 0
  fi

  local file
  if [[ "$DRY_RUN" -eq 1 ]]; then
    for file in "${TARGET_FILES[@]}"; do
      log "[dry-run] candidate: $file"
    done
    exit 0
  fi

  for file in "${TARGET_FILES[@]}"; do
    validate_file "$file"
    log "validated: $file"
  done
}

main "$@"
