#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="runner_workspace_maintenance"
WORKSPACE=""
INCLUDE_RUNNER_DIAG="0"
RUNNER_DIAG_MAX_AGE_DAYS="2"
STABLE_PYTHON=""

usage() {
  cat <<'EOF'
Usage: bash scripts/governance/runner_workspace_maintenance.sh --workspace <path> [--include-runner-diag 0|1] [--runner-diag-max-age-days <n>]
EOF
}

log() {
  printf '[%s] %s\n' "$SCRIPT_NAME" "$*" >&2
}

resolve_stable_python() {
  local candidate
  for candidate in /usr/bin/python3 /usr/local/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
    [[ -n "$candidate" ]] || continue
    [[ -x "$candidate" ]] || continue
    if [[ "$candidate" == /tmp/video-digestor-strict-ci/* ]]; then
      continue
    fi
    STABLE_PYTHON="$candidate"
    return 0
  done
  echo "[${SCRIPT_NAME}] unable to find a stable python3 interpreter" >&2
  exit 1
}

require_workspace() {
  [[ -n "$WORKSPACE" ]] || {
    usage >&2
    exit 2
  }
}

print_disk_usage() {
  local path="$1"
  if [[ -e "$path" ]]; then
    df -h "$path" >&2 || true
  fi
}

cleanup_glob() {
  local pattern="$1"
  "$STABLE_PYTHON" - <<'PY' "$pattern"
from glob import glob
from pathlib import Path
import shutil
import sys

pattern = sys.argv[1]
matches = [Path(item) for item in glob(pattern)]
if not matches and Path(pattern).exists():
    matches = [Path(pattern)]

for target in matches:
    if not target.exists():
        continue
    print(f"[runner_workspace_maintenance] removing stale path: {target}", file=sys.stderr)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            continue
    if target.exists():
        raise SystemExit(f"failed to remove stale path: {target}")
PY
}

cleanup_runner_diag_pages() {
  local workspace="$1"
  local runner_root=""
  if [[ "$workspace" == *"/_work/"* ]]; then
    runner_root="${workspace%%/_work/*}"
  fi
  [[ -n "$runner_root" ]] || return 0

  local diag_pages="$runner_root/_diag/pages"
  [[ -d "$diag_pages" ]] || return 0

  log "pruning runner diag pages older than ${RUNNER_DIAG_MAX_AGE_DAYS} day(s): $diag_pages"
  find "$diag_pages" -type f -mtime "+${RUNNER_DIAG_MAX_AGE_DAYS}" -print -delete || true
}

while (($# > 0)); do
  case "$1" in
    --workspace)
      WORKSPACE="${2:-}"
      shift 2
      ;;
    --include-runner-diag)
      INCLUDE_RUNNER_DIAG="${2:-}"
      shift 2
      ;;
    --runner-diag-max-age-days)
      RUNNER_DIAG_MAX_AGE_DAYS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[${SCRIPT_NAME}] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_workspace
resolve_stable_python

if [[ "$INCLUDE_RUNNER_DIAG" != "0" && "$INCLUDE_RUNNER_DIAG" != "1" ]]; then
  echo "[${SCRIPT_NAME}] --include-runner-diag must be 0 or 1" >&2
  exit 2
fi

if ! [[ "$RUNNER_DIAG_MAX_AGE_DAYS" =~ ^[0-9]+$ ]]; then
  echo "[${SCRIPT_NAME}] --runner-diag-max-age-days must be a non-negative integer" >&2
  exit 2
fi

WORKSPACE="$(cd "$WORKSPACE" && pwd)"

log "disk usage before cleanup"
print_disk_usage "$WORKSPACE"
print_disk_usage /tmp

cleanup_glob "$WORKSPACE/.runtime-cache"
cleanup_glob "$WORKSPACE/mutants"
cleanup_glob "/tmp/video-digestor-strict-ci"
cleanup_glob "/tmp/video-digestor-api-web-e2e-*"
cleanup_glob "/tmp/video-digestor-worker-web-e2e-*"
cleanup_glob "/tmp/video-digestor-live-smoke-*"
cleanup_glob "/tmp/video-digestor-api-smoke*"
cleanup_glob "/tmp/temporal-cli-*"

if [[ "$INCLUDE_RUNNER_DIAG" == "1" ]]; then
  cleanup_runner_diag_pages "$WORKSPACE"
fi

log "disk usage after cleanup"
print_disk_usage "$WORKSPACE"
print_disk_usage /tmp
