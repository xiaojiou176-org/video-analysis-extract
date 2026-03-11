#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
eval "$(python3 scripts/ci_contract.py shell-exports)"

MODE=""
DEBUG_BUILD="0"

usage() {
  cat <<'EOF'
Usage: ./scripts/strict_ci_entry.sh --mode <pre-push|python-tests|api-real-smoke|pr-llm-real-smoke|web-test-build|web-e2e|live-smoke> [args...]

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
    exec "${command[@]}"
  fi

  if [[ "$DEBUG_BUILD" == "1" ]]; then
    VD_STANDARD_ENV_ALLOW_LOCAL_BUILD="1" exec "$ROOT_DIR/scripts/run_in_standard_env.sh" "${command[@]}"
  fi

  exec "$ROOT_DIR/scripts/run_in_standard_env.sh" "${command[@]}"
}

case "$MODE" in
  pre-push)
    run_inside_standard_env bash -lc \
      "./scripts/quality_gate.sh --mode pre-push --profile ci --profile live-smoke --heartbeat-seconds 20 --mutation-min-score ${STRICT_CI_MUTATION_MIN_SCORE} --mutation-min-effective-ratio ${STRICT_CI_MUTATION_MIN_EFFECTIVE_RATIO} --mutation-max-no-tests-ratio ${STRICT_CI_MUTATION_MAX_NO_TESTS_RATIO} ${FORWARDED_ARGS}"
    ;;
  python-tests)
    run_inside_standard_env bash -lc "./scripts/ci_python_tests.sh ${FORWARDED_ARGS}"
    ;;
  api-real-smoke)
    run_inside_standard_env bash -lc "./scripts/ci_api_real_smoke.sh ${FORWARDED_ARGS}"
    ;;
  pr-llm-real-smoke)
    run_inside_standard_env bash -lc "./scripts/ci_pr_llm_real_smoke.sh ${FORWARDED_ARGS}"
    ;;
  web-test-build)
    run_inside_standard_env bash -lc "./scripts/ci_web_test_build.sh ${FORWARDED_ARGS}"
    ;;
  web-e2e)
    run_inside_standard_env bash -lc "./scripts/ci_web_e2e.sh ${FORWARDED_ARGS}"
    ;;
  live-smoke)
    run_inside_standard_env bash -lc "./scripts/ci_live_smoke.sh ${FORWARDED_ARGS}"
    ;;
  *)
    echo "[strict-ci-entry] unsupported mode: $MODE" >&2
    exit 2
    ;;
esac
