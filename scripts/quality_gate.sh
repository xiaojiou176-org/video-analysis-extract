#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="pre-push"
HEARTBEAT_SECONDS="25"
MUTATION_MIN_SCORE="0.85"
PROFILE_ONLY="0"
FINAL_CHECK="0"
FINAL_SKIP_PREPUSH="0"
CHANGED_BACKEND_INPUT="auto"
CHANGED_WEB_INPUT="auto"
CHANGED_DEPS_INPUT="auto"
CHANGED_MIGRATIONS_INPUT="auto"
CI_DEDUPE="0"
CHANGED_BACKEND="true"
CHANGED_WEB="true"
CHANGED_DEPS="true"
CHANGED_MIGRATIONS="true"
EFFECTIVE_BACKEND_CHANGED="true"
EFFECTIVE_WEB_CHANGED="true"
CHANGED_DETECTION_SOURCE="manual"
CHANGED_DETECTION_RELIABLE="1"
CHANGED_FILE_LIST=""
PROFILES=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/quality_gate.sh [--mode pre-commit|pre-push] [--heartbeat-seconds N] [--mutation-min-score N] [--profile NAME ...] [--profile-only] \
    [--changed-backend true|false|auto] [--changed-web true|false|auto] [--changed-deps true|false|auto] [--changed-migrations true|false|auto] [--ci-dedupe 0|1]
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
  --mutation-min-score N  Mutation score threshold (default: 0.85).
  --profile-only   Run profile checks only, skip other quality gates.
  --changed-backend true|false|auto    Backend change hint (default: auto).
  --changed-web true|false|auto        Frontend change hint (default: auto).
  --changed-deps true|false|auto       Dependency change hint (default: auto).
  --changed-migrations true|false|auto Migration change hint (default: auto).
  --ci-dedupe 0|1  Pre-push only: when 1, skip checks covered by standalone CI jobs.
  --final-check    Shortcut to run scripts/env/final_governance_check.sh.
  --skip-prepush   Used with --final-check to skip final pre-push phase.

Quality policy (blocking):
  - Lint errors must be zero (frontend + backend full lint).
  - Placebo assertions are forbidden.
  - Documentation drift gate is mandatory.
  - Secrets leak scan is mandatory.
  - Coverage thresholds: total >= 80%, core modules >= 95%.
  - Mutation testing (Python core): mutation score >= configured threshold (default: 0.85).
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
    --changed-backend)
      CHANGED_BACKEND_INPUT="${2:-}"
      shift 2
      ;;
    --changed-web)
      CHANGED_WEB_INPUT="${2:-}"
      shift 2
      ;;
    --changed-deps)
      CHANGED_DEPS_INPUT="${2:-}"
      shift 2
      ;;
    --changed-migrations)
      CHANGED_MIGRATIONS_INPUT="${2:-}"
      shift 2
      ;;
    --ci-dedupe)
      CI_DEDUPE="${2:-}"
      shift 2
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

for tristate_arg in \
  "$CHANGED_BACKEND_INPUT" \
  "$CHANGED_WEB_INPUT" \
  "$CHANGED_DEPS_INPUT" \
  "$CHANGED_MIGRATIONS_INPUT"; do
  if [[ "$tristate_arg" != "true" && "$tristate_arg" != "false" && "$tristate_arg" != "auto" ]]; then
    echo "[quality-gate] invalid changed flag: ${tristate_arg} (expected true|false|auto)" >&2
    exit 2
  fi
done

if [[ "$CI_DEDUPE" != "0" && "$CI_DEDUPE" != "1" ]]; then
  echo "[quality-gate] invalid --ci-dedupe: $CI_DEDUPE (expected 0|1)" >&2
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

run_tracked_real_env_guard() {
  local tracked blocked path
  tracked="$(git ls-files | rg '(^|/)\.env($|\.)|(^|/)env/.*\.env$' || true)"

  if [[ -z "$tracked" ]]; then
    echo "[quality-gate] real .env tracking guard passed"
    return 0
  fi

  blocked=""
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    case "$path" in
      env/profiles/*.env|*.env.example|*.env.sample|*.env.template)
        continue
        ;;
      *)
        blocked+="${path}"$'\n'
        ;;
    esac
  done <<< "$tracked"

  if [[ -n "$blocked" ]]; then
    printf '%s' "$blocked" >&2
    echo "[quality-gate] real .env tracking guard failed" >&2
    return 1
  fi

  echo "[quality-gate] real .env tracking guard passed"
}

run_gitleaks_fast_scan() {
  local config_args=()

  if ! command -v gitleaks >/dev/null 2>&1; then
    echo "[quality-gate] gitleaks not found; install gitleaks to proceed" >&2
    return 1
  fi

  if [[ -f "$ROOT_DIR/.gitleaks.toml" ]]; then
    config_args=(--config "$ROOT_DIR/.gitleaks.toml")
  fi

  if gitleaks protect --help >/dev/null 2>&1; then
    gitleaks protect --staged --redact "${config_args[@]}"
  elif gitleaks git --help >/dev/null 2>&1; then
    gitleaks git --staged --redact "${config_args[@]}"
  else
    gitleaks detect --source "$ROOT_DIR" --no-git --redact "${config_args[@]}"
  fi

  echo "[quality-gate] gitleaks lightweight scan passed"
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

run_env_governance_report_non_blocking() {
  local mode_tag="$1"
  local out_dir="$ROOT_DIR/.runtime-cache"
  local json_out="$out_dir/env-governance-${mode_tag}.json"
  local md_out="$out_dir/env-governance-${mode_tag}.md"
  mkdir -p "$out_dir"

  if ! python3 scripts/report_env_governance.py \
    --json-out "$json_out" \
    --md-out "$md_out"; then
    echo "[quality-gate] env governance report detected issues (non-blocking): ${json_out}" >&2
  else
    echo "[quality-gate] env governance report generated: ${json_out}"
  fi
}

print_mutation_target_set() {
  local pyproject_file="$ROOT_DIR/pyproject.toml"

  if [[ ! -f "$pyproject_file" ]]; then
    echo "[quality-gate] mutation target set unavailable: pyproject.toml not found" >&2
    return 1
  fi

  python3 - "$pyproject_file" <<'PY'
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

pyproject_path = Path(sys.argv[1])
data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
paths = data.get("tool", {}).get("mutmut", {}).get("paths_to_mutate", [])
if not paths:
    print("[quality-gate] mutation target set is empty")
    raise SystemExit(1)

grouped = defaultdict(list)
for path in paths:
    if "/worker/pipeline/" in path:
        grouped["worker-pipeline"].append(path)
    elif "/api/app/services/" in path:
        grouped["api-services"].append(path)
    elif "/api/app/routers/" in path:
        grouped["api-routes"].append(path)
    else:
        grouped["other"].append(path)

print(f"[quality-gate] mutation target set count={len(paths)}")
for key in ("worker-pipeline", "api-services", "api-routes", "other"):
    values = grouped.get(key, [])
    if not values:
        continue
    print(f"[quality-gate] mutation target group={key} count={len(values)}")
    for item in values:
        print(f"[quality-gate]   - {item}")
PY
}

run_mutation_gate() {
  local stats_file="mutants/mutmut-cicd-stats.json"
  echo "[quality-gate] mutation gate threshold=${MUTATION_MIN_SCORE}"
  if ! print_mutation_target_set; then
    echo "[quality-gate] mutation gate failed: unable to load target set from pyproject.toml." >&2
    return 1
  fi

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
  if ((batch_size <= 0)); then
    echo "[quality-gate] phase '${phase_name}' no async tasks; skip wait"
    return 0
  fi
  if ((batch_size == 1)); then
    echo "[quality-gate] phase '${phase_name}' single async task; run without parallel requirement"
    return 0
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

is_true() {
  [[ "$1" == "true" ]]
}

detect_changed_files() {
  local changed_files=""
  local upstream_ref=""
  local merge_base=""

  CHANGED_DETECTION_RELIABLE="1"

  if [[ "$MODE" == "pre-commit" ]]; then
    CHANGED_DETECTION_SOURCE="staged"
    if ! changed_files="$(git diff --name-only --cached 2>/dev/null)"; then
      CHANGED_DETECTION_RELIABLE="0"
      CHANGED_DETECTION_SOURCE="staged-unavailable"
    fi
  else
    if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"; then
      if merge_base="$(git merge-base HEAD '@{upstream}' 2>/dev/null)"; then
        CHANGED_DETECTION_SOURCE="upstream:${upstream_ref} (${merge_base}..HEAD)"
        if ! changed_files="$(git diff --name-only "$merge_base" HEAD 2>/dev/null)"; then
          CHANGED_DETECTION_RELIABLE="0"
        fi
      else
        CHANGED_DETECTION_RELIABLE="0"
      fi
    else
      if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
        CHANGED_DETECTION_SOURCE="fallback:HEAD~1..HEAD"
        if ! changed_files="$(git diff --name-only HEAD~1 HEAD 2>/dev/null)"; then
          CHANGED_DETECTION_RELIABLE="0"
        fi
      else
        CHANGED_DETECTION_RELIABLE="0"
        CHANGED_DETECTION_SOURCE="upstream-and-fallback-unavailable"
      fi
    fi
  fi

  if [[ "$CHANGED_DETECTION_RELIABLE" != "1" ]]; then
    CHANGED_FILE_LIST=""
    return
  fi

  CHANGED_FILE_LIST="$changed_files"
}

match_changed_files() {
  local pattern="$1"

  if [[ -z "$CHANGED_FILE_LIST" ]]; then
    return 1
  fi

  printf '%s\n' "$CHANGED_FILE_LIST" | rg -q "$pattern"
}

resolve_changed_flags() {
  local auto_fallback="false"

  detect_changed_files

  if [[ "$CHANGED_DETECTION_RELIABLE" != "1" ]]; then
    auto_fallback="true"
    echo "[quality-gate] changed detection unavailable; conservative fallback=true for auto flags" >&2
  fi

  if [[ "$CHANGED_BACKEND_INPUT" == "auto" ]]; then
    if [[ "$auto_fallback" == "true" ]]; then
      CHANGED_BACKEND="true"
    elif match_changed_files '^(apps/(api|worker|mcp)/|scripts/|infra/sql/|infra/config/|infra/compose/)'; then
      CHANGED_BACKEND="true"
    else
      CHANGED_BACKEND="false"
    fi
  else
    CHANGED_BACKEND="$CHANGED_BACKEND_INPUT"
  fi

  if [[ "$CHANGED_WEB_INPUT" == "auto" ]]; then
    if [[ "$auto_fallback" == "true" ]]; then
      CHANGED_WEB="true"
    elif match_changed_files '^apps/web/'; then
      CHANGED_WEB="true"
    else
      CHANGED_WEB="false"
    fi
  else
    CHANGED_WEB="$CHANGED_WEB_INPUT"
  fi

  if [[ "$CHANGED_DEPS_INPUT" == "auto" ]]; then
    if [[ "$auto_fallback" == "true" ]]; then
      CHANGED_DEPS="true"
    elif match_changed_files '(^|/)(pyproject\.toml|uv\.lock|requirements(\.txt)?|poetry\.lock|Pipfile(\.lock)?|package\.json|package-lock\.json|npm-shrinkwrap\.json|pnpm-lock\.yaml|yarn\.lock)$'; then
      CHANGED_DEPS="true"
    else
      CHANGED_DEPS="false"
    fi
  else
    CHANGED_DEPS="$CHANGED_DEPS_INPUT"
  fi

  if [[ "$CHANGED_MIGRATIONS_INPUT" == "auto" ]]; then
    if [[ "$auto_fallback" == "true" ]]; then
      CHANGED_MIGRATIONS="true"
    elif match_changed_files '^infra/migrations/.*\.sql$'; then
      CHANGED_MIGRATIONS="true"
    else
      CHANGED_MIGRATIONS="false"
    fi
  else
    CHANGED_MIGRATIONS="$CHANGED_MIGRATIONS_INPUT"
  fi

  EFFECTIVE_BACKEND_CHANGED="false"
  if is_true "$CHANGED_BACKEND" || is_true "$CHANGED_DEPS" || is_true "$CHANGED_MIGRATIONS"; then
    EFFECTIVE_BACKEND_CHANGED="true"
  fi

  EFFECTIVE_WEB_CHANGED="false"
  if is_true "$CHANGED_WEB" || is_true "$CHANGED_DEPS"; then
    EFFECTIVE_WEB_CHANGED="true"
  fi

  echo "[quality-gate] changed flags: backend=${CHANGED_BACKEND}, web=${CHANGED_WEB}, deps=${CHANGED_DEPS}, migrations=${CHANGED_MIGRATIONS} effective_backend=${EFFECTIVE_BACKEND_CHANGED} effective_web=${EFFECTIVE_WEB_CHANGED} source=${CHANGED_DETECTION_SOURCE}"
}

run_profile_gate() {
  local profile_name="$1"

  echo "[quality-gate] profile gate start: ${profile_name}"

  case "$profile_name" in
    local)
      python3 - <<'PY'
import re
from pathlib import Path

script = Path("scripts/e2e_live_smoke.sh").read_text(encoding="utf-8")

required = [
    "--profile, --env-profile <name>",
    'ENV_PROFILE="${ENV_PROFILE:-local}"',
    'load_repo_env "$ROOT_DIR" "$SCRIPT_NAME" "$ENV_PROFILE"',
]
missing = sorted(item for item in required if item not in script)
if missing:
    raise SystemExit("local profile gate failed: missing CLI profile bindings: " + ", ".join(missing))
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
import re
from pathlib import Path

script = Path("scripts/e2e_live_smoke.sh").read_text(encoding="utf-8")

required = [
    "--api-base-url <url>",
    "--require-api <0|1>",
    "--require-secrets <0|1>",
    "--computer-use-strict <0|1>",
    "--computer-use-skip <0|1>",
    "--computer-use-skip-reason <text>",
    "--max-retries <n>",
]
missing = sorted(item for item in required if item not in script)
if missing:
    raise SystemExit("live-smoke profile gate failed: missing CLI options: " + ", ".join(missing))

defaults = {
    "LIVE_SMOKE_REQUIRE_API": "1",
    "LIVE_SMOKE_REQUIRE_SECRETS": "0",
    "LIVE_SMOKE_COMPUTER_USE_STRICT": "1",
    "LIVE_SMOKE_COMPUTER_USE_SKIP": "0",
    "LIVE_SMOKE_MAX_RETRIES": "2",
}
for name, expected in defaults.items():
    pattern = rf'^{name}="{re.escape(expected)}"$'
    if not re.search(pattern, script, re.MULTILINE):
        raise SystemExit(f"live-smoke profile gate failed: {name} default must be '{expected}'")
print("live-smoke profile gate passed")
PY
      bash scripts/check_ci_smoke_drift.sh
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
  run_async_gate "tracked_real_env_guard" "real .env tracking guard" \
    "run_tracked_real_env_guard"
  run_async_gate "gitleaks_fast_scan" "gitleaks lightweight scan (if installed)" \
    "run_gitleaks_fast_scan"
  run_async_gate "hollow_log_guard" "hollow log message guard" \
    "run_hollow_log_guard"
  run_async_gate "structured_log_guard" "structured log critical-path guard" \
    "python3 scripts/check_structured_logs.py"
  run_async_gate "iac_entrypoint_guard" "iac entrypoint guard" \
    "bash scripts/check_iac_entrypoint.sh ."
  run_async_gate "env_budget_guard" "env budget guard" \
    "python3 scripts/check_env_budget.py"
  run_async_gate "env_governance_report" "env governance report (non-blocking)" \
    "run_env_governance_report_non_blocking pre-commit"
  if is_true "$EFFECTIVE_WEB_CHANGED"; then
    run_async_gate "web_lint" "frontend lint" \
      "npm --prefix apps/web run lint"
  else
    echo "[quality-gate] skip: frontend lint (effective_web_changed=false)"
  fi
  if is_true "$EFFECTIVE_BACKEND_CHANGED"; then
    run_async_gate "ruff_full" "backend lint (ruff full rules)" \
      "uv run --with ruff ruff check apps scripts"
  else
    echo "[quality-gate] skip: backend lint (effective_backend_changed=false)"
  fi

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
  run_async_gate "env_governance_report" "env governance report (non-blocking)" \
    "run_env_governance_report_non_blocking pre-push"
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
  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: frontend lint (--ci-dedupe=1)"
  elif is_true "$EFFECTIVE_WEB_CHANGED"; then
    run_async_gate "web_lint" "frontend lint" \
      "npm --prefix apps/web run lint"
  else
    echo "[quality-gate] skip: frontend lint (effective_web_changed=false)"
  fi
  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: backend lint (ruff) (--ci-dedupe=1)"
  elif is_true "$EFFECTIVE_BACKEND_CHANGED"; then
    run_async_gate "ruff_full" "backend lint (ruff full rules)" \
      "uv run --with ruff ruff check apps scripts"
  else
    echo "[quality-gate] skip: backend lint (effective_backend_changed=false)"
  fi

  ensure_parallel_batch "pre-push/short-checks"

  if ! wait_async_gates; then
    echo "[quality-gate] pre-push failed in short-checks phase" >&2
    exit 1
  fi

  echo "[quality-gate] phase=long-tests (parallel + heartbeat=${HEARTBEAT_SECONDS}s)"
  reset_async_buffers

  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: web unit tests (--ci-dedupe=1)"
  elif is_true "$EFFECTIVE_WEB_CHANGED"; then
    run_async_gate "web_unit_tests" "web unit tests" \
      "npm --prefix apps/web run test -- --coverage"
  else
    echo "[quality-gate] skip: web unit tests (effective_web_changed=false)"
  fi
  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: web coverage threshold gate (--ci-dedupe=1, covered by CI web-test-build)"
  elif is_true "$EFFECTIVE_WEB_CHANGED"; then
    run_async_gate "web_coverage_threshold" "web coverage threshold gate (global>=80, core>=90)" \
      "python3 scripts/check_web_coverage_threshold.py --summary-path apps/web/coverage/coverage-summary.json --global-threshold 80 --core-threshold 90"
  else
    echo "[quality-gate] skip: web coverage threshold gate (effective_web_changed=false)"
  fi
  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: python tests + total coverage (--ci-dedupe=1)"
  elif is_true "$EFFECTIVE_BACKEND_CHANGED"; then
    run_async_gate "python_tests_with_coverage" "python tests + total coverage gate (>=80%)" \
      "PYTHONPATH=\"$PWD:$PWD/apps/worker\" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA --cov=apps/worker/worker --cov=apps/api --cov=apps/mcp --cov-report=term-missing:skip-covered --cov-fail-under=80"
  else
    echo "[quality-gate] skip: python tests + total coverage (effective_backend_changed=false)"
  fi

  ensure_parallel_batch "pre-push/long-tests"

  if ! wait_async_gates_with_heartbeat; then
    echo "[quality-gate] pre-push failed in long-tests phase" >&2
    exit 1
  fi

  echo "[quality-gate] phase=coverage-core-gates (parallel)"
  reset_async_buffers

  if [[ "$CI_DEDUPE" == "1" ]]; then
    echo "[quality-gate] skip: coverage core gates (--ci-dedupe=1)"
  elif is_true "$EFFECTIVE_BACKEND_CHANGED"; then
    run_async_gate "coverage_worker_core_95" "worker core coverage gate (>=95%)" \
      "uv run coverage report --include=\"*/apps/worker/worker/pipeline/orchestrator.py,*/apps/worker/worker/pipeline/policies.py,*/apps/worker/worker/pipeline/runner.py,*/apps/worker/worker/pipeline/types.py\" --show-missing --fail-under=95"
    run_async_gate "coverage_api_core_95" "api core coverage gate (>=95%)" \
      "uv run coverage report --include=\"*/apps/api/app/routers/ingest.py,*/apps/api/app/routers/jobs.py,*/apps/api/app/routers/subscriptions.py,*/apps/api/app/routers/videos.py,*/apps/api/app/services/jobs.py,*/apps/api/app/services/subscriptions.py,*/apps/api/app/services/videos.py\" --show-missing --fail-under=95"
  else
    echo "[quality-gate] skip: coverage core gates (effective_backend_changed=false)"
  fi

  ensure_parallel_batch "pre-push/coverage-core-gates"

  if ! wait_async_gates; then
    echo "[quality-gate] pre-push failed in coverage-core-gates phase" >&2
    exit 1
  fi

  if is_true "$EFFECTIVE_BACKEND_CHANGED"; then
    echo "[quality-gate] phase=mutation-gate (heartbeat=${HEARTBEAT_SECONDS}s)"
    if ! run_sync_gate_with_heartbeat "mutation_gate" "mutation gate" "run_mutation_gate"; then
      echo "[quality-gate] pre-push failed in mutation-gate phase" >&2
      exit 1
    fi
  else
    echo "[quality-gate] skip: mutation gate (effective_backend_changed=false)"
  fi

  echo "[quality-gate] all checks passed"
}

if [[ "$MODE" == "pre-commit" ]]; then
  resolve_changed_flags
  run_pre_commit_mode
else
  resolve_changed_flags
  run_pre_push_mode
fi
