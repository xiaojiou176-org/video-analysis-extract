#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HEARTBEAT_SECONDS="25"
MUTATION_MIN_SCORE="0.64"
SKIP_PREPUSH="0"

usage() {
  cat <<'USAGE'
Usage:
  scripts/env/final_governance_check.sh [--skip-prepush] [--heartbeat-seconds N] [--mutation-min-score N]

Flow:
  1) Profile governance checks
  2) pre-commit quality gate
  3) pre-push quality gate (optional; skipped with --skip-prepush)
USAGE
}

while (($# > 0)); do
  case "$1" in
    --skip-prepush)
      SKIP_PREPUSH="1"
      shift
      ;;
    --heartbeat-seconds)
      HEARTBEAT_SECONDS="${2:-}"
      shift 2
      ;;
    --mutation-min-score)
      MUTATION_MIN_SCORE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[final-governance] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$HEARTBEAT_SECONDS" =~ ^[0-9]+$ ]] || ((HEARTBEAT_SECONDS < 5)); then
  echo "[final-governance] invalid --heartbeat-seconds: $HEARTBEAT_SECONDS" >&2
  exit 2
fi

if ! [[ "$MUTATION_MIN_SCORE" =~ ^0(\.[0-9]+)?$|^1(\.0+)?$ ]]; then
  echo "[final-governance] invalid --mutation-min-score: $MUTATION_MIN_SCORE (expected 0.0..1.0)" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

run_phase_with_heartbeat() {
  local phase_key="$1"
  local phase_name="$2"
  shift 2
  local log_file="$TMP_DIR/${phase_key}.log"
  local pid

  echo "[final-governance] start: ${phase_name}"
  (
    cd "$ROOT_DIR"
    "$@"
  ) >"$log_file" 2>&1 &
  pid="$!"

  while kill -0 "$pid" >/dev/null 2>&1; do
    echo "[final-governance][heartbeat] phase=${phase_key} running"
    sleep "$HEARTBEAT_SECONDS"
  done

  if ! wait "$pid"; then
    echo "[final-governance] FAIL: ${phase_name}" >&2
    echo "[final-governance] ----- ${phase_name} log (tail -n 80) -----" >&2
    tail -n 80 "$log_file" >&2 || true
    echo "[final-governance] -----------------------------------------" >&2
    return 1
  fi

  echo "[final-governance] pass: ${phase_name}"
}

run_phase_with_heartbeat \
  "profile-validation" \
  "profile governance checks (local + ci + live-smoke)" \
  bash scripts/quality_gate.sh \
    --mode pre-push \
    --profile local \
    --profile ci \
    --profile live-smoke \
    --profile-only \
    --heartbeat-seconds "$HEARTBEAT_SECONDS" \
    --mutation-min-score "$MUTATION_MIN_SCORE"

run_phase_with_heartbeat \
  "pre-commit" \
  "quality gate pre-commit" \
  bash scripts/quality_gate.sh \
    --mode pre-commit \
    --heartbeat-seconds "$HEARTBEAT_SECONDS" \
    --mutation-min-score "$MUTATION_MIN_SCORE"

if [[ "$SKIP_PREPUSH" == "1" ]]; then
  echo "[final-governance] skip: pre-push phase (--skip-prepush)"
  echo "[final-governance] done"
  exit 0
fi

run_phase_with_heartbeat \
  "pre-push" \
  "strict ci entry pre-push" \
  bash scripts/strict_ci_entry.sh \
    --mode pre-push \
    --strict-full-run 1 \
    --ci-dedupe 0 \
    --heartbeat-seconds "$HEARTBEAT_SECONDS" \
    --mutation-min-score "$MUTATION_MIN_SCORE"

echo "[final-governance] done"
