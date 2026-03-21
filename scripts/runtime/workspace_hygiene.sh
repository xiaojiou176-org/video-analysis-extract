#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="workspace_hygiene"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

apply_changes=0

usage() {
  cat <<'EOF'
Usage: ./bin/workspace-hygiene [--apply]

Detects repo-side runtime residue that is forbidden by root/runtime governance:
  - .cache / cache / logs / mutants / playwright-report / test-results / htmlcov
  - .coverage / .pytest_cache / .ruff_cache
  - .venv
  - venv
  - apps/web/node_modules
  - .runtime-cache/tmp/uv-project-env
  - source-tree __pycache__ directories
  - source-tree *.pyc / *.pyo files

Default mode only reports. Use --apply to remove the residue.
EOF
}

log() { printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      apply_changes=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "error: unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

declare -a dir_targets=()
declare -a file_targets=()

for rel in \
  ".cache" \
  ".pytest_cache" \
  ".ruff_cache" \
  ".venv" \
  "venv" \
  "cache" \
  "logs" \
  "mutants" \
  "playwright-report" \
  "test-results" \
  "htmlcov"; do
  if [[ -d "$ROOT_DIR/$rel" ]]; then
    dir_targets+=("$ROOT_DIR/$rel")
  fi
done

for rel in ".coverage"; do
  if [[ -f "$ROOT_DIR/$rel" ]]; then
    file_targets+=("$ROOT_DIR/$rel")
  fi
done

if [[ -d "$ROOT_DIR/.venv" ]]; then
  dir_targets+=("$ROOT_DIR/.venv")
fi
if [[ -d "$ROOT_DIR/apps/web/node_modules" ]]; then
  dir_targets+=("$ROOT_DIR/apps/web/node_modules")
fi
if [[ -d "$ROOT_DIR/.runtime-cache/tmp/uv-project-env" ]]; then
  dir_targets+=("$ROOT_DIR/.runtime-cache/tmp/uv-project-env")
fi

while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  dir_targets+=("$path")
done < <(
  find "$ROOT_DIR" \
    -path "$ROOT_DIR/.git" -prune -o \
    -path "$ROOT_DIR/.runtime-cache" -prune -o \
    -path "$ROOT_DIR/apps/web/node_modules" -prune -o \
    -type d -name __pycache__ -print 2>/dev/null | sort
)

while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  file_targets+=("$path")
done < <(
  find "$ROOT_DIR" \
    -path "$ROOT_DIR/.git" -prune -o \
    -path "$ROOT_DIR/.runtime-cache" -prune -o \
    -path "$ROOT_DIR/apps/web/node_modules" -prune -o \
    -type f \( -name '*.pyc' -o -name '*.pyo' \) -print 2>/dev/null | sort
)

if (( ${#dir_targets[@]} == 0 && ${#file_targets[@]} == 0 )); then
  log "no forbidden workspace runtime residue detected"
  exit 0
fi

log "detected forbidden workspace runtime residue"
for target in "${dir_targets[@]}"; do
  log "dir: ${target#$ROOT_DIR/}"
done
for target in "${file_targets[@]}"; do
  log "file: ${target#$ROOT_DIR/}"
done

if (( apply_changes == 0 )); then
  log "run './bin/workspace-hygiene --apply' to remove these paths"
  exit 1
fi

for target in "${dir_targets[@]}"; do
  rm -rf "$target"
done
for target in "${file_targets[@]}"; do
  rm -f "$target"
done

log "workspace runtime residue removed"
