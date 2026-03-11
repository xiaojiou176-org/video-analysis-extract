#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/standard_env.sh"
ALLOW_LOCAL_BUILD="${VD_STANDARD_ENV_ALLOW_LOCAL_BUILD:-0}"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/run_in_standard_env.sh <command> [args...]
USAGE
}

if (($# == 0)); then
  usage >&2
  exit 2
fi

if [[ "${VD_IN_STANDARD_ENV:-0}" == "1" ]]; then
  exec "$@"
fi

if [[ "$ALLOW_LOCAL_BUILD" == "1" ]]; then
  build_standard_env_image
fi
run_in_standard_env "$@"
