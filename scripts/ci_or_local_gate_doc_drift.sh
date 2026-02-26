#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="staged"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci_or_local_gate_doc_drift.sh [--scope staged|push]

Checks required documentation updates for high-risk code changes.
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

  if git -C "$ROOT_DIR" rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    git -C "$ROOT_DIR" rev-parse HEAD~1
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
    # Push scope checks the outgoing commit range, and also includes local pending
    # changes so developers can satisfy required docs before creating the next commit.
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
      if ! contains_file "$line" "${changed_files[@]-}"; then
        changed_files+=("$line")
      fi
    done <<< "$diff_output"
  fi
}

contains_file() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
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

check_required_docs() {
  local reason="$1"
  shift
  local -a required=("$@")
  local missing=0
  local doc

  for doc in "${required[@]}"; do
    if ! contains_file "$doc" "${changed_files[@]}"; then
      ((missing += 1))
      echo "[doc-drift] missing required doc update for ${reason}: ${doc}" >&2
    fi
  done

  if ((missing > 0)); then
    violations+=("$reason")
  fi
}

has_changed_matching() {
  local pattern="$1"
  local f
  for f in "${changed_files[@]}"; do
    if [[ "$f" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

load_changed_files

echo "[doc-drift] scope=${SCOPE}, changed_files=${#changed_files[@]}"

if ((${#changed_files[@]} == 0)); then
  echo "[doc-drift] no changed files, skip"
  exit 0
fi

violations=()

if has_changed_matching 'infra/migrations/*.sql'; then
  check_required_docs "infra/migrations/*.sql" \
    "README.md" \
    "docs/runbook-local.md"
fi

if contains_file "apps/worker/worker/pipeline/types.py" "${changed_files[@]}"; then
  if pipeline_steps_changed; then
    check_required_docs "PIPELINE_STEPS in apps/worker/worker/pipeline/types.py" \
      "docs/state-machine.md"
  fi
fi

if contains_file ".env.example" "${changed_files[@]}" || contains_file "infra/config/env.contract.json" "${changed_files[@]}"; then
  check_required_docs "environment variable contract" \
    ".env.example" \
    "ENVIRONMENT.md" \
    "infra/config/env.contract.json"
fi

if has_changed_matching 'apps/api/app/routers/*.py' || \
   has_changed_matching 'apps/api/app/services/*.py' || \
   has_changed_matching 'apps/mcp/**/*.py'; then
  check_required_docs "api behavior/signature contract changes" \
    "README.md" \
    "docs/runbook-local.md" \
    "docs/testing.md"
fi

if contains_file "apps/mcp/schemas/tools.json" "${changed_files[@]}" || \
   has_changed_matching 'packages/shared-contracts/jsonschema/*.json'; then
  check_required_docs "schema signature contract changes" \
    "docs/testing.md"
fi

if has_changed_matching 'scripts/dev_*.sh' || \
   contains_file "scripts/full_stack.sh" "${changed_files[@]}" || \
   contains_file "scripts/bootstrap_full_stack.sh" "${changed_files[@]}" || \
   contains_file "scripts/smoke_full_stack.sh" "${changed_files[@]}"; then
  check_required_docs "local startup script parameters/defaults" \
    "README.md" \
    "docs/start-here.md" \
    "docs/runbook-local.md"
fi

if has_changed_matching 'infra/compose/*.compose.yml' || \
   has_changed_matching '.devcontainer/*' || \
   has_changed_matching '.devcontainer/**'; then
  check_required_docs "compose/devcontainer startup topology" \
    "README.md" \
    "docs/start-here.md" \
    "docs/runbook-local.md"
fi

if contains_file "pyproject.toml" "${changed_files[@]}" || \
   contains_file "uv.lock" "${changed_files[@]}" || \
   has_changed_matching 'requirements*.txt' || \
   has_changed_matching 'requirements/*.txt' || \
   has_changed_matching 'apps/*/package.json' || \
   has_changed_matching 'apps/*/package-lock.json' || \
   has_changed_matching 'apps/*/pnpm-lock.yaml'; then
  check_required_docs "dependency governance policy" \
    "docs/reference/dependency-governance.md"
fi

if contains_file "scripts/dev_api.sh" "${changed_files[@]}" || \
   contains_file "scripts/dev_worker.sh" "${changed_files[@]}" || \
   contains_file "scripts/dev_mcp.sh" "${changed_files[@]}" || \
   contains_file "scripts/run_daily_digest.sh" "${changed_files[@]}" || \
   contains_file "scripts/run_failure_alerts.sh" "${changed_files[@]}" || \
   contains_file "apps/api/app/security.py" "${changed_files[@]}"; then
  check_required_docs "logging governance policy" \
    "docs/reference/logging.md"
fi

if contains_file "scripts/start_ops_workflows.sh" "${changed_files[@]}" || \
   contains_file "apps/worker/worker/main.py" "${changed_files[@]}" || \
   contains_file "apps/worker/worker/temporal/activities_cleanup.py" "${changed_files[@]}" || \
   contains_file "apps/worker/worker/pipeline/step_executor.py" "${changed_files[@]}" || \
   contains_file "apps/worker/worker/pipeline/steps/llm_client.py" "${changed_files[@]}"; then
  check_required_docs "cache governance policy" \
    "docs/reference/cache.md"
fi

if ((${#violations[@]} > 0)); then
  echo "[doc-drift] failed: ${#violations[@]} trigger(s) missing required docs" >&2
  exit 1
fi

echo "[doc-drift] passed"
