#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
eval "$(python3 scripts/ci/contract.py shell-exports)"
SCRIPT_NAME="strict_ci_entry"

# shellcheck source=./scripts/runtime/logging.sh
source "$ROOT_DIR/scripts/runtime/logging.sh"
vd_log_init "governance" "$SCRIPT_NAME" "$ROOT_DIR/.runtime-cache/logs/governance/strict-ci-entry.jsonl"

MODE=""
DEBUG_BUILD="0"

usage() {
  cat <<'EOF'
Usage: ./bin/strict-ci --mode <pre-push|python-tests|api-real-smoke|pr-llm-real-smoke|web-test-build|web-e2e|live-smoke> [args...]

Options:
  --mode <name>     Strict entry mode.
  --debug-build     Build and run the local standard image instead of pulling the pinned registry image.
EOF
}

forward_args=()
while (($# > 0)); do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --debug-build)
      DEBUG_BUILD="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      forward_args+=("$1")
      shift
      ;;
  esac
done

[[ -n "$MODE" ]] || { usage >&2; exit 2; }
vd_log info strict_ci_entry_start "mode=$MODE debug_build=$DEBUG_BUILD"

quoted_forward_args() {
  if ((${#forward_args[@]} == 0)); then
    return 0
  fi
  printf '%q ' "${forward_args[@]}"
}

FORWARDED_ARGS="$(quoted_forward_args || true)"

run_inside_standard_env() {
  local command=("$@")
  if [[ "${VD_IN_STANDARD_ENV:-0}" == "1" ]]; then
    vd_log info strict_ci_entry_passthrough "already inside standard env"
    "${command[@]}"
    return $?
  fi

  if [[ "$DEBUG_BUILD" == "1" ]]; then
    vd_log info strict_ci_entry_diagnostic_mode "using debug-build diagnostic path"
    VD_STANDARD_ENV_ALLOW_LOCAL_BUILD="1" "$ROOT_DIR/scripts/ci/run_in_standard_env.sh" "${command[@]}"
    return $?
  fi

  vd_log info strict_ci_entry_release_qualifying "using pinned-image release-qualifying path"
  "$ROOT_DIR/scripts/ci/run_in_standard_env.sh" "${command[@]}"
  return $?
}

run_with_strict_bootstrap() {
  local inner_command="$1"
  run_inside_standard_env bash -lc "source ./scripts/ci/bootstrap_strict_ci_runtime.sh && ${inner_command}"
}

apply_api_real_smoke_default_database_url() {
  local default_api_real_smoke_database_url="${API_REAL_SMOKE_DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres}"
  if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL}" == "sqlite+pysqlite:///:memory:" ]]; then
    export DATABASE_URL="$default_api_real_smoke_database_url"
  fi
}

apply_web_e2e_default_database_url() {
  local default_web_e2e_database_url="${API_REAL_SMOKE_DATABASE_URL:-postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres}"
  if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL}" == "sqlite+pysqlite:///:memory:" ]]; then
    export DATABASE_URL="$default_web_e2e_database_url"
  fi
}

apply_api_real_smoke_default_temporal_target_host() {
  local default_api_real_smoke_temporal_target_host="${API_REAL_SMOKE_TEMPORAL_TARGET_HOST:-127.0.0.1:7233}"
  local resolved_api_real_smoke_temporal_target_host="${TEMPORAL_TARGET_HOST:-$default_api_real_smoke_temporal_target_host}"
  export TEMPORAL_TARGET_HOST="$resolved_api_real_smoke_temporal_target_host"
}

if ! case "$MODE" in
  pre-push)
    run_with_strict_bootstrap \
      "./scripts/quality_gate.sh --mode pre-push --profile ci --profile live-smoke --heartbeat-seconds 20 --mutation-min-score ${STRICT_CI_MUTATION_MIN_SCORE} --mutation-min-effective-ratio ${STRICT_CI_MUTATION_MIN_EFFECTIVE_RATIO} --mutation-max-no-tests-ratio ${STRICT_CI_MUTATION_MAX_NO_TESTS_RATIO} ${FORWARDED_ARGS}"
    ;;
  python-tests)
    run_with_strict_bootstrap "./scripts/ci/python_tests.sh ${FORWARDED_ARGS}"
    ;;
  api-real-smoke)
    apply_api_real_smoke_default_database_url
    apply_api_real_smoke_default_temporal_target_host
    run_with_strict_bootstrap "./scripts/ci/api_real_smoke.sh ${FORWARDED_ARGS}"
    ;;
  pr-llm-real-smoke)
    run_with_strict_bootstrap "./scripts/ci/pr_llm_real_smoke.sh ${FORWARDED_ARGS}"
    ;;
  web-test-build)
    run_with_strict_bootstrap "./scripts/ci/web_test_build.sh ${FORWARDED_ARGS}"
    ;;
  web-e2e)
    apply_web_e2e_default_database_url
    run_with_strict_bootstrap "./scripts/ci/web_e2e.sh ${FORWARDED_ARGS}"
    ;;
  live-smoke)
    run_with_strict_bootstrap "./scripts/ci/live_smoke.sh ${FORWARDED_ARGS}"
    ;;
  *)
    echo "[strict-ci-entry] unsupported mode: $MODE" >&2
    exit 2
    ;;
esac; then
  vd_log error complete "FAIL"
  exit 1
fi

vd_log info complete "PASS"
