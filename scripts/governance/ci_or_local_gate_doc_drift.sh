#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCOPE="staged"
CHANGE_CONTRACT_PATH="$ROOT_DIR/config/docs/change-contract.json"

usage() {
  cat <<'USAGE'
Usage:
  scripts/governance/ci_or_local_gate_doc_drift.sh [--scope staged|push]

Checks required documentation updates for high-risk code changes using the
docs control plane contract in `config/docs/change-contract.json`.
USAGE
}

while (($# > 0)); do
  case "$1" in
    --scope)
      SCOPE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[doc-drift] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$SCOPE" != "staged" && "$SCOPE" != "push" ]]; then
  echo "[doc-drift] invalid --scope: $SCOPE (expected staged or push)" >&2
  exit 2
fi

empty_tree_sha="$(git -C "$ROOT_DIR" hash-object -t tree /dev/null)"

get_push_base() {
  if git -C "$ROOT_DIR" rev-parse --verify '@{upstream}' >/dev/null 2>&1; then
    git -C "$ROOT_DIR" merge-base HEAD '@{upstream}'
    return
  fi

  local remote_head_ref=""
  remote_head_ref="$(git -C "$ROOT_DIR" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [[ -n "$remote_head_ref" ]]; then
    local remote_head_merge_base=""
    remote_head_merge_base="$(git -C "$ROOT_DIR" merge-base HEAD "$remote_head_ref" 2>/dev/null || true)"
    if [[ -n "$remote_head_merge_base" ]]; then
      echo "$remote_head_merge_base"
      return
    fi
  fi

  local candidate=""
  for candidate in origin/main origin/master origin/trunk; do
    if git -C "$ROOT_DIR" rev-parse --verify "$candidate" >/dev/null 2>&1; then
      local candidate_merge_base=""
      candidate_merge_base="$(git -C "$ROOT_DIR" merge-base HEAD "$candidate" 2>/dev/null || true)"
      if [[ -n "$candidate_merge_base" ]]; then
        echo "$candidate_merge_base"
        return
      fi
    fi
  done

  local root_commit=""
  root_commit="$(git -C "$ROOT_DIR" rev-list --max-parents=0 HEAD 2>/dev/null | head -n 1 || true)"
  if [[ -n "$root_commit" ]]; then
    local head_sha=""
    head_sha="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)"
    if [[ -n "$head_sha" && "$root_commit" == "$head_sha" ]]; then
      echo "$empty_tree_sha"
      return
    fi
    echo "$root_commit"
    return
  fi

  echo "$empty_tree_sha"
}

load_changed_files() {
  local diff_output=""
  if [[ "$SCOPE" == "staged" ]]; then
    diff_output="$(git -C "$ROOT_DIR" diff --cached --name-only)"
  else
    local base
    base="$(get_push_base)"
    diff_output+="$(
      git -C "$ROOT_DIR" diff --name-only "$base"..HEAD
    )"$'\n'
    diff_output+="$(
      git -C "$ROOT_DIR" diff --name-only
    )"$'\n'
    diff_output+="$(
      git -C "$ROOT_DIR" diff --cached --name-only
    )"$'\n'
    diff_output+="$(
      git -C "$ROOT_DIR" ls-files --others --exclude-standard
    )"
  fi

  changed_files=()
  if [[ -n "$diff_output" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      changed_files+=("$line")
    done <<< "$diff_output"
  fi
}

pipeline_steps_changed() {
  local target="apps/worker/worker/pipeline/types.py"

  if [[ "$SCOPE" == "staged" ]]; then
    git -C "$ROOT_DIR" diff --cached -- "$target" | rg -q 'PIPELINE_STEPS'
    return
  fi

  local base
  base="$(get_push_base)"
  git -C "$ROOT_DIR" diff "$base"..HEAD -- "$target" | rg -q 'PIPELINE_STEPS'
}

load_changed_files

echo "[doc-drift] scope=${SCOPE}, changed_files=${#changed_files[@]}"

if ((${#changed_files[@]} == 0)); then
  echo "[doc-drift] no changed files, skip"
  exit 0
fi

PIPELINE_STEPS_CHANGED="0"
if pipeline_steps_changed; then
  PIPELINE_STEPS_CHANGED="1"
fi

changed_file_list="$(printf '%s\n' "${changed_files[@]}")"

ROOT_DIR="$ROOT_DIR" \
CHANGE_CONTRACT_PATH="$CHANGE_CONTRACT_PATH" \
CHANGED_FILE_LIST="$changed_file_list" \
PIPELINE_STEPS_CHANGED="$PIPELINE_STEPS_CHANGED" \
python3 - <<'PY'
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
contract_path = Path(os.environ["CHANGE_CONTRACT_PATH"])
changed_files = [line.strip() for line in os.environ["CHANGED_FILE_LIST"].splitlines() if line.strip()]
pipeline_steps_changed = os.environ.get("PIPELINE_STEPS_CHANGED", "0") == "1"

payload = json.loads(contract_path.read_text(encoding="utf-8"))
rules = payload.get("rules", [])

violations: list[str] = []


def matches_any(patterns: list[str]) -> bool:
    for changed in changed_files:
        for pattern in patterns:
            if fnmatch.fnmatch(changed, pattern):
                return True
    return False


for rule in rules:
    rule_id = str(rule.get("id", "unknown"))
    patterns = [str(item) for item in rule.get("when", [])]
    if not patterns:
        continue
    if not matches_any(patterns):
        continue
    if rule.get("special_check") == "pipeline_steps_changed" and not pipeline_steps_changed:
        continue

    required = [str(item) for item in rule.get("required_paths", [])]
    missing = [path for path in required if path not in changed_files]
    for path in missing:
        print(f"[doc-drift] missing required doc update for {rule_id}: {path}", file=sys.stderr)
    if missing:
        violations.append(rule_id)

if violations:
    print(f"[doc-drift] failed: {len(violations)} trigger(s) missing required docs", file=sys.stderr)
    raise SystemExit(1)

print("[doc-drift] passed")
PY
