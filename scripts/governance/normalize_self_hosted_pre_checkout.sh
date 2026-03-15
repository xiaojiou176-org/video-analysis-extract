#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="normalize_self_hosted_pre_checkout"
WORKSPACE=""
INCLUDE_RUNNER_DIAG="0"

usage() {
  cat <<'EOF'
Usage: bash scripts/normalize_self_hosted_pre_checkout.sh --workspace <path> [--include-runner-diag 0|1]
EOF
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

[[ -n "$WORKSPACE" ]] || {
  usage >&2
  exit 2
}

workspace="$(cd "$WORKSPACE" && pwd)"
uid="$(id -u)"
gid="$(id -g)"

if command -v sudo >/dev/null 2>&1; then
  if sudo find "$workspace" -mindepth 1 -uid 0 -print -quit | grep -q .; then
    echo "[${SCRIPT_NAME}] detected root-owned residue under $workspace; normalizing ownership"
    sudo chown -R "$uid:$gid" "$workspace"
  fi
fi

helper="$workspace/scripts/governance/runner_workspace_maintenance.sh"
if [[ -x "$helper" ]]; then
  bash "$helper" --workspace "$workspace" --include-runner-diag "$INCLUDE_RUNNER_DIAG"
  exit 0
fi

stale_paths=(
  "$workspace/.runtime-cache"
  "$workspace/apps/web/node_modules"
)
if command -v sudo >/dev/null 2>&1; then
  for path in "${stale_paths[@]}"; do
    if sudo test -e "$path"; then
      echo "[${SCRIPT_NAME}] removing stale workspace path: $path"
      sudo rm -rf "$path"
    fi
  done
else
  for path in "${stale_paths[@]}"; do
    rm -rf "$path" || true
  done
fi
