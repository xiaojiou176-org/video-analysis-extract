#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNTIME_ROOT="$ROOT_DIR/.runtime-cache/tmp/web-runtime"
WORKSPACE_WEB_DIR="$RUNTIME_ROOT/workspace/apps/web"
STATE_DIR="$ROOT_DIR/.runtime-cache/run/web-runtime"
HASH_FILE="$STATE_DIR/package.sha256"
READY_FILE="$STATE_DIR/ready"
LOCK_DIR="$STATE_DIR/.prepare-lock"
SHELL_EXPORTS="0"
SKIP_INSTALL="0"

usage() {
  cat <<'EOF'
Usage: scripts/ci/prepare_web_runtime.sh [--shell-exports] [--skip-install 0|1]

Creates a repo-side runtime workspace for apps/web under .runtime-cache/tmp/web-runtime
so repo-tracked source directories do not host machine dependency state.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --shell-exports)
      SHELL_EXPORTS="1"
      shift
      ;;
    --skip-install)
      SKIP_INSTALL="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[prepare_web_runtime] unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$RUNTIME_ROOT" "$STATE_DIR"

PACKAGE_HASH="$(
  python3 - <<'PY' "$ROOT_DIR"
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

root = Path(sys.argv[1])
source_dir = root / "apps" / "web"
blocked_names = {
    "node_modules",
    ".next",
    "coverage",
    "out",
    "build",
    "tsconfig.tsbuildinfo",
    ".DS_Store",
}

digest = hashlib.sha256()
for path in sorted(source_dir.rglob("*")):
    rel = path.relative_to(source_dir).as_posix()
    if any(part in blocked_names for part in path.parts):
        continue
    if any(part.startswith(".next-e2e-") for part in path.parts):
        continue
    if path.is_dir():
        continue
    digest.update(rel.encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest(), end="")
PY
)"

acquire_lock() {
  local attempts=0
  while ! mkdir "$LOCK_DIR" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if (( attempts > 120 )); then
      echo "[prepare_web_runtime] timeout waiting for lock: $LOCK_DIR" >&2
      exit 1
    fi
    sleep 1
  done
}

release_lock() {
  rm -rf "$LOCK_DIR"
}

workspace_ready() {
  [[ -f "$READY_FILE" ]] || return 1
  [[ -f "$HASH_FILE" ]] || return 1
  [[ -d "$WORKSPACE_WEB_DIR" ]] || return 1
  [[ "$(cat "$HASH_FILE" 2>/dev/null || true)" == "$PACKAGE_HASH" ]] || return 1
  [[ -f "$WORKSPACE_WEB_DIR/eslint.config.mjs" ]] || return 1
  [[ -f "$WORKSPACE_WEB_DIR/tsconfig.json" ]] || return 1
  if [[ "$SKIP_INSTALL" != "1" ]]; then
    [[ -x "$WORKSPACE_WEB_DIR/node_modules/.bin/next" ]] || return 1
  fi
  return 0
}

acquire_lock
trap release_lock EXIT

if workspace_ready; then
  if [[ "$SHELL_EXPORTS" == "1" ]]; then
    printf 'export WEB_RUNTIME_ROOT=%q\n' "$RUNTIME_ROOT"
    printf 'export WEB_RUNTIME_WEB_DIR=%q\n' "$WORKSPACE_WEB_DIR"
    printf 'export WEB_RUNTIME_PACKAGE_HASH=%q\n' "$PACKAGE_HASH"
  else
    printf 'WEB_RUNTIME_ROOT=%s\n' "$RUNTIME_ROOT"
    printf 'WEB_RUNTIME_WEB_DIR=%s\n' "$WORKSPACE_WEB_DIR"
    printf 'WEB_RUNTIME_PACKAGE_HASH=%s\n' "$PACKAGE_HASH"
  fi
  exit 0
fi

python3 - <<'PY' "$ROOT_DIR"
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
web_dir = root / "apps" / "web"
for child in web_dir.iterdir():
    if child.name == "node_modules" or child.name == ".next" or child.name.startswith(".next-e2e-"):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
PY

python3 - <<'PY' "$ROOT_DIR" "$WORKSPACE_WEB_DIR"
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
source_dir = root / "apps" / "web"
target_dir = Path(sys.argv[2])

def ignore(_path: str, names: list[str]) -> set[str]:
    blocked = {
        "node_modules",
        ".next",
        ".next-e2e-gw0",
        "coverage",
        "out",
        "build",
        "tsconfig.tsbuildinfo",
        ".DS_Store",
    }
    ignored = {name for name in names if name in blocked}
    ignored.update({name for name in names if name.startswith(".next-e2e-")})
    return ignored

if target_dir.exists():
    shutil.rmtree(target_dir)
target_dir.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source_dir, target_dir, ignore=ignore, copy_function=shutil.copy)
PY

CURRENT_HASH=""
if [[ -f "$HASH_FILE" ]]; then
  CURRENT_HASH="$(cat "$HASH_FILE" 2>/dev/null || true)"
fi

if [[ "$SKIP_INSTALL" != "1" ]]; then
  if [[ ! -x "$WORKSPACE_WEB_DIR/node_modules/.bin/next" || "$CURRENT_HASH" != "$PACKAGE_HASH" ]]; then
    if [[ "$SHELL_EXPORTS" == "1" ]]; then
      (cd "$WORKSPACE_WEB_DIR" && npm ci --no-audit --no-fund) >&2
    else
      (cd "$WORKSPACE_WEB_DIR" && npm ci --no-audit --no-fund)
    fi
    printf '%s' "$PACKAGE_HASH" > "$HASH_FILE"
  fi
fi

printf '%s\n' "$PACKAGE_HASH" > "$HASH_FILE"
printf 'ready\n' > "$READY_FILE"

if [[ "$SHELL_EXPORTS" == "1" ]]; then
  printf 'export WEB_RUNTIME_ROOT=%q\n' "$RUNTIME_ROOT"
  printf 'export WEB_RUNTIME_WEB_DIR=%q\n' "$WORKSPACE_WEB_DIR"
  printf 'export WEB_RUNTIME_PACKAGE_HASH=%q\n' "$PACKAGE_HASH"
  printf 'export VIDEO_ANALYSIS_REPO_ROOT=%q\n' "$ROOT_DIR"
else
  printf 'WEB_RUNTIME_ROOT=%s\n' "$RUNTIME_ROOT"
  printf 'WEB_RUNTIME_WEB_DIR=%s\n' "$WORKSPACE_WEB_DIR"
  printf 'WEB_RUNTIME_PACKAGE_HASH=%s\n' "$PACKAGE_HASH"
  printf 'VIDEO_ANALYSIS_REPO_ROOT=%s\n' "$ROOT_DIR"
fi
