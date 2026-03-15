#!/usr/bin/env bash
set -euo pipefail

vd_entrypoint_bootstrap() {
  local channel="$1"
  local entrypoint_name="$2"
  shift 2

  export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

  # shellcheck source=./scripts/runtime/logging.sh
  source "$ROOT_DIR/scripts/runtime/logging.sh"
  vd_log_entrypoint="$entrypoint_name"
  vd_log_init "$channel" "$entrypoint_name"

  export vd_log_channel
  export vd_log_component
  export vd_log_run_id
  export vd_log_repo_commit
  export vd_log_entrypoint
  export vd_log_env_profile
  export vd_log_path
  export vd_test_run_id
  export vd_gate_run_id

  python3 "$ROOT_DIR/scripts/runtime/write_run_manifest.py" \
    --run-id "$vd_log_run_id" \
    --entrypoint "$entrypoint_name" \
    --channel "$channel" \
    --argv "$@"
}
