#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

bash "$ROOT_DIR/bin/workspace-hygiene" --normalize --quiet

subdir_args=()
assert_clean=0
apply=0
normalize_only=0

while (($# > 0)); do
  case "$1" in
    --subdir)
      subdir_args+=("$1" "${2:-}")
      shift 2
      ;;
    --assert-clean)
      assert_clean=1
      shift
      ;;
    --apply)
      apply=1
      shift
      ;;
    --normalize-only)
      normalize_only=1
      shift
      ;;
    *)
      echo "[run_runtime_cache_maintenance] unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

cmd=(python3 "$ROOT_DIR/scripts/runtime/prune_runtime_cache.py")
if (( apply == 1 )); then
  cmd+=(--apply)
fi
if (( assert_clean == 1 )); then
  cmd+=(--assert-clean)
fi
if (( normalize_only == 1 )); then
  cmd+=(--normalize-only)
fi
cmd+=("${subdir_args[@]}")
"${cmd[@]}"
python3 "$ROOT_DIR/scripts/runtime/build_evidence_index.py" --rebuild-all
