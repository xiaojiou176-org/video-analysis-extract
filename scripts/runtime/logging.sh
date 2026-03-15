#!/usr/bin/env bash
set -euo pipefail

vd_uuid() {
  python3 - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
}

vd_log_init() {
  local channel="$1"
  local component="$2"
  local path="${3:-}"

  vd_log_channel="$channel"
  vd_log_component="$component"
  vd_log_run_id="${vd_log_run_id:-$(vd_uuid)}"
  vd_log_repo_commit="${vd_log_repo_commit:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf unknown)}"
  vd_log_entrypoint="${vd_log_entrypoint:-$component}"
  vd_log_env_profile="${vd_log_env_profile:-${ENV_PROFILE:-unknown}}"
  if [[ "${channel}" == "tests" && -z "${vd_test_run_id:-}" ]]; then
    vd_test_run_id="$vd_log_run_id"
  fi
  if [[ "${channel}" == "governance" && -z "${vd_gate_run_id:-}" ]]; then
    vd_gate_run_id="$vd_log_run_id"
  fi
  if [[ -n "$path" ]]; then
    vd_log_path="$path"
  else
    vd_log_path="$ROOT_DIR/.runtime-cache/logs/${channel}/${vd_log_run_id}.jsonl"
  fi
  mkdir -p "$(dirname "$vd_log_path")"
}

vd_log_json_only() {
  local severity="$1"
  local event="$2"
  shift 2
  local message="$*"
  local source_kind="${vd_log_source_kind:-}"
  if [[ -z "$source_kind" ]]; then
    case "${vd_log_channel:-}" in
      tests) source_kind="test" ;;
      governance) source_kind="governance" ;;
      infra) source_kind="infra" ;;
      *) source_kind="app" ;;
    esac
  fi
  python3 "$ROOT_DIR/scripts/runtime/log_jsonl_event.py" \
    --path "${vd_log_path:?}" \
    --run-id "${vd_log_run_id:?}" \
    --trace-id "${vd_trace_id:-}" \
    --request-id "${vd_request_id:-${vd_log_run_id:-}}" \
    --service "${vd_log_service:-${vd_log_component:?}}" \
    --component "${vd_log_component:?}" \
    --channel "${vd_log_channel:?}" \
    --source-kind "$source_kind" \
    --test-run-id "${vd_test_run_id:-}" \
    --gate-run-id "${vd_gate_run_id:-}" \
    --entrypoint "${vd_log_entrypoint:-${vd_log_component:?}}" \
    --env-profile "${vd_log_env_profile:-unknown}" \
    --repo-commit "${vd_log_repo_commit:-unknown}" \
    --event "$event" \
    --severity "$severity" \
    --message "$message" >/dev/null 2>&1 || true
}

vd_log() {
  local severity="$1"
  local event="$2"
  shift 2
  local message="$*"
  printf '[%s] %s\n' "${vd_log_component:-unknown_component}" "$message" >&2
  vd_log_json_only "$severity" "$event" "$message"
}
