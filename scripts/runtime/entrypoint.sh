#!/usr/bin/env bash
set -euo pipefail

vd_entrypoint_bootstrap() {
  local channel="$1"
  local entrypoint_name="$2"
  local explicit_log_path="${3:-}"
  local argv_json="[]"
  shift 3

  if [[ "${VD_SKIP_WORKSPACE_HYGIENE:-0}" != "1" ]]; then
    bash "$ROOT_DIR/bin/workspace-hygiene" --normalize --quiet
  fi

  export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
  export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$ROOT_DIR/.runtime-cache/tmp/pycache}"
  argv_json="$(
    python3 - <<'PY' "$@"
import json
import sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PY
  )"

  # shellcheck source=./scripts/runtime/logging.sh
  source "$ROOT_DIR/scripts/runtime/logging.sh"
  vd_log_entrypoint="$entrypoint_name"
  vd_log_init "$channel" "$entrypoint_name" "$explicit_log_path"
  vd_log info entrypoint_bootstrap "bootstrap entrypoint=${entrypoint_name} channel=${channel}"

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
    --argv-json "$argv_json"
}
