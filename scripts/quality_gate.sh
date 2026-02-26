#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="pre-push"
HEARTBEAT_SECONDS="25"
MUTATION_MIN_SCORE="0.60"
PROFILE_ONLY="0"
FINAL_CHECK="0"
FINAL_SKIP_PREPUSH="0"
PROFILES=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/quality_gate.sh [--mode pre-commit|pre-push] [--heartbeat-seconds N] [--mutation-min-score N] [--profile NAME ...] [--profile-only]
  scripts/quality_gate.sh --final-check [--skip-prepush] [--heartbeat-seconds N] [--mutation-min-score N]

Modes:
  pre-commit  Run fast local commit gate (parallel checks + staged doc drift).
  pre-push    Run short checks first, then long tests with heartbeat logs.
Profiles:
  local       Validate local profile governance.
  ci          Validate CI profile governance.
  live-smoke  Validate live-smoke profile governance.
Flags:
  --profile NAME   Append explicit profile checks (repeatable).
  --profile-only   Run profile checks only, skip other quality gates.
  --final-check    Shortcut to run scripts/env/final_governance_check.sh.
  --skip-prepush   Used with --final-check to skip final pre-push phase.

Quality policy (blocking):
  - Lint errors must be zero (frontend + backend full lint).
  - Placebo assertions are forbidden.
  - Documentation drift gate is mandatory.
  - Secrets leak scan is mandatory.
  - Coverage thresholds: total >= 80%, core modules >= 95%.
  - Mutation testing (Python core): mutation score >= configured threshold.
USAGE
}

while (($# > 0)); do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="${2:-}"
      shift 2
      ;;
    --mutation-min-score)
      MUTATION_MIN_SCORE="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILES+=("${2:-}")
      shift 2
      ;;
    --profile-only)
      PROFILE_ONLY="1"
      shift
      ;;
    --final-check)
      FINAL_CHECK="1"
      shift
      ;;
    --skip-prepush)
      FINAL_SKIP_PREPUSH="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[quality-gate] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$MODE" != "pre-commit" && "$MODE" != "pre-push" ]]; then
  echo "[quality-gate] invalid --mode: $MODE (expected pre-commit or pre-push)" >&2
  exit 2
fi

if ! [[ "$HEARTBEAT_SECONDS" =~ ^[0-9]+$ ]] || ((HEARTBEAT_SECONDS < 5)); then
  echo "[quality-gate] invalid --heartbeat-seconds: $HEARTBEAT_SECONDS" >&2
  exit 2
fi

if ! [[ "$MUTATION_MIN_SCORE" =~ ^0(\.[0-9]+)?$|^1(\.0+)?$ ]]; then
  echo "[quality-gate] invalid --mutation-min-score: $MUTATION_MIN_SCORE (expected 0.0..1.0)" >&2
  exit 2
fi

if [[ "$PROFILE_ONLY" != "0" && "$PROFILE_ONLY" != "1" ]]; then
  echo "[quality-gate] invalid --profile-only: $PROFILE_ONLY (expected flag)" >&2
  exit 2
fi

if [[ "$FINAL_SKIP_PREPUSH" == "1" && "$FINAL_CHECK" != "1" ]]; then
  echo "[quality-gate] --skip-prepush can only be used with --final-check" >&2
  exit 2
fi

if [[ "$FINAL_CHECK" == "1" ]]; then
  final_cmd=(
    bash
    "$ROOT_DIR/scripts/env/final_governance_check.sh"
    --heartbeat-seconds
    "$HEARTBEAT_SECONDS"
    --mutation-min-score
    "$MUTATION_MIN_SCORE"
  )
  if [[ "$FINAL_SKIP_PREPUSH" == "1" ]]; then
    final_cmd+=(--skip-prepush)
  fi
  exec "${final_cmd[@]}"
fi

if ((${#PROFILES[@]} == 0)); then
  if [[ "$MODE" == "pre-commit" ]]; then
    PROFILES=("local")
  else
    PROFILES=("ci" "live-smoke")
  fi
fi

for profile in "${PROFILES[@]}"; do
  if [[ "$profile" != "local" && "$profile" != "ci" && "$profile" != "live-smoke" ]]; then
    echo "[quality-gate] invalid --profile: $profile (expected local|ci|live-smoke)" >&2
    exit 2
  fi
done

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cleanup_mutation_artifacts() {
  rm -rf "$ROOT_DIR/mutants" "$ROOT_DIR/apps/worker/mutants"
}

RUN_IDS=()
RUN_NAMES=()
RUN_PIDS=()

run_async_gate() {
  local gate_id="$1"
  local gate_name="$2"
  local gate_cmd="$3"
  local gate_log="$TMP_DIR/${gate_id}.log"

  echo "[quality-gate] start: $gate_name"
  (
    cd "$ROOT_DIR"
    eval "$gate_cmd"
  ) >"$gate_log" 2>&1 &

  RUN_IDS+=("$gate_id")
  RUN_NAMES+=("$gate_name")
  RUN_PIDS+=("$!")
}

reset_async_buffers() {
  RUN_IDS=()
  RUN_NAMES=()
  RUN_PIDS=()
}

run_secrets_scan() {
  local matches filtered
  matches="$(
    rg -n --hidden --no-ignore-vcs \
      --glob "!.git/**" \
      --glob "!node_modules/**" \
      --glob "!.venv/**" \
      --glob "!.runtime-cache/**" \
      --glob "!dist/**" \
      --glob "!build/**" \
      --glob "!coverage/**" \
      --glob "!.next/**" \
      -e 'sk-[A-Za-z0-9]{20,}' \
      -e 'ghp_[A-Za-z0-9]{20,}' \
      -e 'AKIA[0-9A-Z]{16}' \
      -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
      . || true
  )"

  filtered="$(
    printf '%s\n' "$matches" | rg -v \
      -e 'ghp_12345678901234567890' \
      -e 'AKIAIOSFODNN7EXAMPLE' \
      -e 'sk-test' \
      -e 'sk-dummy' \
      -e 'sk-placeholder' || true
  )"

  if [[ -n "$filtered" ]]; then
    printf '%s\n' "$filtered" >&2
    echo "[quality-gate] secrets leak scan failed" >&2
    return 1
  fi

  echo "[quality-gate] secrets leak scan passed"
}

run_hollow_log_guard() {
  local matches
  matches="$(
    rg -n -i \
      --glob '*.py' \
      -e 'logger\.(debug|info|warning|error|exception)\(\s*f?["'"'"'](something went wrong|unexpected error|error occurred|unknown error)["'"'"']' \
      apps/api apps/worker || true
  )"

  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches" >&2
    echo "[quality-gate] hollow log message guard failed" >&2
    return 1
  fi

  echo "[quality-gate] hollow log message guard passed"
}

run_mutation_gate() {
  local stats_file="mutants/mutmut-cicd-stats.json"
  echo "[quality-gate] mutation gate target=apps/worker/worker/pipeline/steps/llm_step_gates.py threshold=${MUTATION_MIN_SCORE}"

  if ! command -v uv >/dev/null 2>&1; then
    echo "[quality-gate] mutation gate failed: uv is required to auto-install/run mutmut." >&2
    echo "[quality-gate] install hint: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    return 1
  fi

  rm -rf "$ROOT_DIR/mutants"

  if ! DATABASE_URL='sqlite+pysqlite:///:memory:' \
    PYTHONPATH="$ROOT_DIR:$ROOT_DIR/apps/worker" \
    uv run --extra dev --with mutmut mutmut run; then
    echo "[quality-gate] mutation gate failed: mutmut run did not pass." >&2
    echo "[quality-gate] install hint: uv sync --frozen --extra dev --extra e2e" >&2
    return 1
  fi

  if ! PYTHONPATH="$ROOT_DIR:$ROOT_DIR/apps/worker" \
    uv run --extra dev --with mutmut mutmut export-cicd-stats; then
    echo "[quality-gate] mutation gate failed: unable to export mutmut stats." >&2
    return 1
  fi

  if [[ ! -f "$stats_file" ]]; then
    echo "[quality-gate] mutation gate failed: stats file missing at $stats_file." >&2
    return 1
  fi

  if ! python3 - "$stats_file" "$MUTATION_MIN_SCORE" <<'PY'
import json
import sys
from pathlib import Path

stats_path = Path(sys.argv[1])
threshold = float(sys.argv[2])
stats = json.loads(stats_path.read_text(encoding="utf-8"))
killed = int(stats.get("killed", 0))
survived = int(stats.get("survived", 0))
total = int(stats.get("total", killed + survived))
effective = killed + survived
if effective <= 0:
    print(
        f"[quality-gate] mutation gate failed: killed+survived=0 (total={total}), no effective mutants.",
        file=sys.stderr,
    )
    raise SystemExit(1)
score = killed / effective
print(
    f"[quality-gate] mutation stats: killed={killed}, survived={survived}, "
    f"effective={effective}, total={total}, score={score:.4f}, threshold={threshold:.4f}"
)
if score < threshold:
    print(
        f"[quality-gate] mutation gate failed: score {score:.4f} < threshold {threshold:.4f}.",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
  then
    return 1
  fi

  echo "[quality-gate] mutation gate passed"
}

report_gate_failure() {
  local gate_name="$1"
  local gate_log="$2"

  echo "[quality-gate] FAIL: $gate_name" >&2
  echo "[quality-gate] ----- ${gate_name} log (tail -n 80) -----" >&2
  tail -n 80 "$gate_log" >&2 || true
  echo "[quality-gate] ----------------------------------------" >&2
}

ensure_parallel_batch() {
  local phase_name="$1"
  local batch_size="${#RUN_PIDS[@]}"
  if ((batch_size < 2)); then
    echo "[quality-gate] invalid batch configuration: phase '${phase_name}' has ${batch_size} task(s), expected >= 2 for parallel execution" >&2
    exit 1
  fi
  echo "[quality-gate] phase '${phase_name}' parallel tasks=${batch_size}"
}

wait_async_gates() {
  local had_failure=0
  local idx gate_id gate_name gate_pid gate_log

  for idx in "${!RUN_PIDS[@]}"; do
    gate_id="${RUN_IDS[$idx]}"
    gate_name="${RUN_NAMES[$idx]}"
    gate_pid="${RUN_PIDS[$idx]}"
    gate_log="$TMP_DIR/${gate_id}.log"

    if ! wait "$gate_pid"; then
      had_failure=1
      report_gate_failure "$gate_name" "$gate_log"
    else
      echo "[quality-gate] pass: $gate_name"
    fi
  done

  return "$had_failure"
}

wait_async_gates_with_heartbeat() {
  local had_failure=0
  local running_names
  local idx gate_id gate_name gate_pid gate_log

  while :; do
    running_names=""
    for idx in "${!RUN_PIDS[@]}"; do
      gate_pid="${RUN_PIDS[$idx]}"
      gate_name="${RUN_NAMES[$idx]}"
      if kill -0 "$gate_pid" >/dev/null 2>&1; then
        if [[ -z "$running_names" ]]; then
          running_names="$gate_name"
        else
          running_names="$running_names, $gate_name"
        fi
      fi
    done

    if [[ -z "$running_names" ]]; then
      break
    fi

    echo "[quality-gate][heartbeat] long phase running: $running_names"
    sleep "$HEARTBEAT_SECONDS"
  done

  for idx in "${!RUN_PIDS[@]}"; do
    gate_id="${RUN_IDS[$idx]}"
    gate_name="${RUN_NAMES[$idx]}"
    gate_pid="${RUN_PIDS[$idx]}"
    gate_log="$TMP_DIR/${gate_id}.log"

    if ! wait "$gate_pid"; then
      had_failure=1
      report_gate_failure "$gate_name" "$gate_log"
    else
      echo "[quality-gate] pass: $gate_name"
    fi
  done

  return "$had_failure"
}

run_sync_gate_with_heartbeat() {
  local gate_id="$1"
  local gate_name="$2"
  local gate_cmd="$3"
  local gate_log="$TMP_DIR/${gate_id}.log"
  local gate_pid running=true

  echo "[quality-gate] start: $gate_name"
  (
    cd "$ROOT_DIR"
    eval "$gate_cmd"
  ) >"$gate_log" 2>&1 &
  gate_pid="$!"

  while $running; do
    if kill -0 "$gate_pid" >/dev/null 2>&1; then
      echo "[quality-gate][heartbeat] running: $gate_name"
      sleep "$HEARTBEAT_SECONDS"
    else
      running=false
    fi
  done

  if ! wait "$gate_pid"; then
    report_gate_failure "$gate_name" "$gate_log"
    return 1
  fi

  echo "[quality-gate] pass: $gate_name"
}

run_profile_gate() {
  local profile_name="$1"

  echo "[quality-gate] profile gate start: ${profile_name}"

  case "$profile_name" in
    local)
      python3 - <<'PY'
import json
import re
from pathlib import Path

contract = json.loads(Path("infra/config/env.contract.json").read_text(encoding="utf-8"))
variables = {item["name"]: item for item in contract.get("variables", [])}
profile = variables.get("PROFILE")
if profile is None:
    raise SystemExit("local profile gate failed: PROFILE missing in env.contract")
if profile.get("default") != "local":
    raise SystemExit("local profile gate failed: PROFILE default must be 'local'")

env_example = Path(".env.example").read_text(encoding="utf-8")
match = re.search(r"^\s*export\s+PROFILE\s*=\s*['\"]?([^'\"\n]+)['\"]?\s*$", env_example, re.MULTILINE)
if not match:
    raise SystemExit("local profile gate failed: PROFILE missing in .env.example")
if match.group(1).strip() != "local":
    raise SystemExit("local profile gate failed: .env.example PROFILE must be local")
print("local profile gate passed")
PY
      ;;
    ci)
      python3 - <<'PY'
import json
from pathlib import Path

contract = json.loads(Path("infra/config/env.contract.json").read_text(encoding="utf-8"))
variables = {item["name"]: item for item in contract.get("variables", [])}
required = {
    "DATABASE_URL",
    "TEMPORAL_TARGET_HOST",
    "TEMPORAL_NAMESPACE",
    "TEMPORAL_TASK_QUEUE",
    "SQLITE_PATH",
    "SQLITE_STATE_PATH",
    "PIPELINE_WORKSPACE_DIR",
    "PIPELINE_ARTIFACT_ROOT",
    "UI_AUDIT_GEMINI_ENABLED",
    "NOTIFICATION_ENABLED",
    "VD_ALLOW_UNAUTH_WRITE",
}
missing = sorted(name for name in required if name not in variables)
if missing:
    raise SystemExit("ci profile gate failed: missing env contract vars: " + ", ".join(missing))
print("ci profile gate passed")
PY
      ;;
    live-smoke)
      python3 - <<'PY'
import json
from pathlib import Path

contract = json.loads(Path("infra/config/env.contract.json").read_text(encoding="utf-8"))
variables = {item["name"]: item for item in contract.get("variables", [])}
required = {
    "LIVE_SMOKE_API_BASE_URL",
    "LIVE_SMOKE_REQUIRE_API",
    "LIVE_SMOKE_REQUIRE_SECRETS",
    "LIVE_SMOKE_COMPUTER_USE_STRICT",
    "LIVE_SMOKE_COMPUTER_USE_SKIP",
    "LIVE_SMOKE_COMPUTER_USE_SKIP_REASON",
    "LIVE_SMOKE_COMPUTER_USE_CMD",
    "LIVE_SMOKE_HEARTBEAT_SECONDS",
    "LIVE_SMOKE_DIAGNOSTICS_JSON",
    "GEMINI_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "YOUTUBE_API_KEY",
}
missing = sorted(name for name in required if name not in variables)
if missing:
    raise SystemExit("live-smoke profile gate failed: missing env contract vars: " + ", ".join(missing))
if str(variables["LIVE_SMOKE_COMPUTER_USE_STRICT"].get("default")) != "1":
    raise SystemExit("live-smoke profile gate failed: LIVE_SMOKE_COMPUTER_USE_STRICT default must be '1'")
print("live-smoke profile gate passed")
PY
      ;;
  esac

  echo "[quality-gate] profile gate passed: ${profile_name}"
}

run_profile_gates_parallel() {
  local phase_name="$1"
  local profile

  if ((${#PROFILES[@]} < 2)); then
    for profile in "${PROFILES[@]}"; do
      run_profile_gate "$profile"
    done
    return 0
  fi

  reset_async_buffers
  for profile in "${PROFILES[@]}"; do
    run_async_gate "profile_${profile//-/_}" "profile gate (${profile})" "run_profile_gate '${profile}'"
  done

  ensure_parallel_batch "$phase_name"
  if ! wait_async_gates; then
    echo "[quality-gate] profile gate phase failed: ${phase_name}" >&2
    exit 1
  fi
}

run_pre_commit_mode() {
  cleanup_mutation_artifacts

  echo "[quality-gate] mode=pre-commit"
  echo "[quality-gate] phase=profile-gates (parallel)"
  run_profile_gates_parallel "pre-commit/profile-gates"
  if [[ "$PROFILE_ONLY" == "1" ]]; then
    echo "[quality-gate] profile-only passed"
    exit 0
  fi
  reset_async_buffers

  run_async_gate "doc_drift_staged" "documentation drift gate (staged)" \
    "bash scripts/ci_or_local_gate_doc_drift.sh --scope staged"
  run_async_gate "placebo" "placebo assertion guard" \
    "python3 scripts/check_test_assertions.py --path ."
  run_async_gate "secrets_scan" "secrets leak scan" \
    "run_secrets_scan"
  run_async_gate "hollow_log_guard" "hollow log message guard" \
    "run_hollow_log_guard"
  run_async_gate "structured_log_guard" "structured log critical-path guard" \
    "python3 scripts/check_structured_logs.py"
  run_async_gate "iac_entrypoint_guard" "iac entrypoint guard" \
    "bash scripts/check_iac_entrypoint.sh ."
  run_async_gate "env_budget_guard" "env budget guard" \
    "python3 scripts/check_env_budget.py"
  run_async_gate "web_lint" "frontend lint" \
    "npm --prefix apps/web run lint"
  run_async_gate "ruff_full" "backend lint (ruff full rules)" \
    "uv run --with ruff ruff check apps scripts"

  ensure_parallel_batch "pre-commit/short-checks"

  if ! wait_async_gates; then
    echo "[quality-gate] pre-commit gate failed" >&2
    exit 1
  fi

  echo "[quality-gate] pre-commit gate passed"
}

run_pre_push_mode() {
  cleanup_mutation_artifacts

  echo "[quality-gate] mode=pre-push"
  echo "[quality-gate] phase=profile-gates (parallel)"
  run_profile_gates_parallel "pre-push/profile-gates"
  if [[ "$PROFILE_ONLY" == "1" ]]; then
    echo "[quality-gate] profile-only passed"
    exit 0
  fi

  echo "[quality-gate] phase=short-checks (parallel)"
  reset_async_buffers

  run_async_gate "env_contract" "env contract" \
    "python3 scripts/check_env_contract.py --strict"
  run_async_gate "env_budget_guard" "env budget guard" \
    "python3 scripts/check_env_budget.py"
  run_async_gate "doc_drift_push" "documentation drift gate (push range)" \
    "bash scripts/ci_or_local_gate_doc_drift.sh --scope push"
  run_async_gate "placebo" "placebo assertion guard" \
    "python3 scripts/check_test_assertions.py --path ."
  run_async_gate "secrets_scan" "secrets leak scan" \
    "run_secrets_scan"
  run_async_gate "hollow_log_guard" "hollow log message guard" \
    "run_hollow_log_guard"
  run_async_gate "structured_log_guard" "structured log critical-path guard" \
    "python3 scripts/check_structured_logs.py"
  run_async_gate "iac_entrypoint_guard" "iac entrypoint guard" \
    "bash scripts/check_iac_entrypoint.sh ."
  run_async_gate "web_lint" "frontend lint" \
    "npm --prefix apps/web run lint"
  run_async_gate "ruff_full" "backend lint (ruff full rules)" \
    "uv run --with ruff ruff check apps scripts"

  ensure_parallel_batch "pre-push/short-checks"

  if ! wait_async_gates; then
    echo "[quality-gate] pre-push failed in short-checks phase" >&2
    exit 1
  fi

  echo "[quality-gate] phase=long-tests (parallel + heartbeat=${HEARTBEAT_SECONDS}s)"
  reset_async_buffers

  run_async_gate "web_unit_tests" "web unit tests" \
    "npm --prefix apps/web run test -- --coverage"
  run_async_gate "python_tests_with_coverage" "python tests + total coverage gate (>=80%)" \
    "PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA --cov=apps/worker/worker --cov=apps/api --cov=apps/mcp --cov-report=term-missing:skip-covered --cov-fail-under=80"

  ensure_parallel_batch "pre-push/long-tests"

  if ! wait_async_gates_with_heartbeat; then
    echo "[quality-gate] pre-push failed in long-tests phase" >&2
    exit 1
  fi

  echo "[quality-gate] phase=coverage-core-gates (parallel)"
  reset_async_buffers

  run_async_gate "coverage_worker_core_95" "worker core coverage gate (>=95%)" \
    "uv run coverage report --include=\"*/apps/worker/worker/pipeline/orchestrator.py,*/apps/worker/worker/pipeline/policies.py,*/apps/worker/worker/pipeline/runner.py,*/apps/worker/worker/pipeline/types.py\" --show-missing --fail-under=95"
  run_async_gate "coverage_api_core_95" "api core coverage gate (>=95%)" \
    "uv run coverage report --include=\"*/apps/api/app/routers/ingest.py,*/apps/api/app/routers/jobs.py,*/apps/api/app/routers/subscriptions.py,*/apps/api/app/routers/videos.py,*/apps/api/app/services/jobs.py,*/apps/api/app/services/subscriptions.py,*/apps/api/app/services/videos.py\" --show-missing --fail-under=95"

  ensure_parallel_batch "pre-push/coverage-core-gates"

  if ! wait_async_gates; then
    echo "[quality-gate] pre-push failed in coverage-core-gates phase" >&2
    exit 1
  fi

  echo "[quality-gate] phase=mutation-gate (heartbeat=${HEARTBEAT_SECONDS}s)"
  if ! run_sync_gate_with_heartbeat "mutation_gate" "mutation gate" "run_mutation_gate"; then
    echo "[quality-gate] pre-push failed in mutation-gate phase" >&2
    exit 1
  fi

  echo "[quality-gate] all checks passed"
}

if [[ "$MODE" == "pre-commit" ]]; then
  run_pre_commit_mode
else
  run_pre_push_mode
fi
