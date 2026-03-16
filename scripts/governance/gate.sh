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
Usage: ./bin/governance-audit --mode pre-commit|pre-push|ci|audit

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
python3 scripts/runtime/clean_source_runtime_residue.py --apply
python3 scripts/governance/check_root_allowlist.py --strict-local-private
python3 scripts/governance/check_root_semantic_cleanliness.py
python3 scripts/governance/check_root_layout_budget.py
python3 scripts/governance/check_root_zero_unknowns.py
python3 scripts/governance/check_bridge_expiry.py
python3 scripts/governance/check_public_surface_policy.py
python3 scripts/governance/check_historical_release_examples.py
python3 scripts/governance/check_public_contact_points.py
python3 scripts/governance/check_public_entrypoint_manifests.py
python3 scripts/governance/check_public_entrypoint_references.py
python3 scripts/governance/check_root_policy_alignment.py
python3 scripts/governance/check_evidence_contract.py
python3 scripts/governance/check_external_lane_contract.py
python3 scripts/governance/check_current_proof_commit_alignment.py
python3 scripts/governance/check_runtime_outputs.py
python3 scripts/governance/check_runtime_artifact_writer_coverage.py
python3 scripts/governance/check_runtime_cache_retention.py
bash scripts/runtime/run_runtime_cache_maintenance.sh --normalize-only --subdir run --subdir logs --subdir reports --subdir evidence
python3 scripts/governance/check_runtime_metadata_completeness.py
python3 scripts/governance/check_runtime_cache_freshness.py
python3 scripts/governance/check_governance_language.py
python3 scripts/governance/check_dependency_boundaries.py
python3 scripts/governance/check_module_ownership.py
python3 scripts/governance/check_governance_schema_references_exist.py
python3 scripts/governance/check_contract_locality.py
python3 scripts/governance/check_no_cross_app_implementation_imports.py
python3 scripts/governance/check_logging_contract.py
python3 scripts/governance/check_log_correlation_completeness.py
python3 scripts/governance/check_log_retention.py
python3 scripts/governance/check_no_unindexed_evidence.py
python3 scripts/governance/check_run_manifest_completeness.py
python3 scripts/governance/check_contract_surfaces.py
python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py
python3 scripts/governance/check_eval_assets.py
python3 scripts/governance/check_eval_regression.py
python3 scripts/governance/render_newcomer_result_proof.py
python3 scripts/governance/check_newcomer_result_proof.py
python3 scripts/governance/check_upstream_governance.py
python3 scripts/governance/check_unregistered_upstream_usage.py
python3 scripts/governance/check_upstream_compat_freshness.py
python3 scripts/governance/check_upstream_same_run_cohesion.py
python3 scripts/governance/check_active_upstream_evidence_fresh.py
python3 scripts/governance/check_upstream_failure_classification.py
python3 scripts/governance/check_vendor_registry_integrity.py
python3 scripts/governance/render_third_party_notices.py --check

vd_log info complete "PASS"
