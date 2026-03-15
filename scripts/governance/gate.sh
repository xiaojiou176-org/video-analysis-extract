#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="pre-push"
SCRIPT_NAME="governance_gate"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"

# shellcheck source=./scripts/runtime/logging.sh
source "$ROOT_DIR/scripts/runtime/logging.sh"
vd_log_init "governance" "$SCRIPT_NAME" "$ROOT_DIR/.runtime-cache/logs/governance/governance-gate.jsonl"

usage() {
  cat <<'EOF'
Usage: ./scripts/governance_gate.sh --mode pre-commit|pre-push|ci|audit

Runs repository governance control-plane checks:
  - root allowlist
  - runtime output policy
  - dependency boundaries
  - logging contract
  - upstream governance
EOF
}

while (($# > 0)); do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      vd_log error invalid_argument "unknown argument: $1"
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$MODE" != "pre-commit" && "$MODE" != "pre-push" && "$MODE" != "ci" && "$MODE" != "audit" ]]; then
  vd_log error invalid_mode "invalid mode: $MODE"
  exit 2
fi

cd "$ROOT_DIR"

vd_log info start "mode=$MODE"
python3 scripts/governance/check_root_allowlist.py
python3 scripts/governance/check_root_semantic_cleanliness.py
python3 scripts/governance/check_runtime_outputs.py
python3 scripts/governance/check_governance_language.py
python3 scripts/governance/check_dependency_boundaries.py
python3 scripts/governance/check_logging_contract.py
python3 scripts/governance/check_contract_surfaces.py
python3 scripts/governance/check_upstream_governance.py
python3 scripts/governance/check_unregistered_upstream_usage.py

vd_log info complete "PASS"
