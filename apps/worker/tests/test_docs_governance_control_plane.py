from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_docs_control_plane_files_exist_and_reference_real_paths() -> None:
    root = _repo_root()
    for relative in (
        "config/docs/nav-registry.json",
        "config/docs/render-manifest.json",
        "config/docs/boundary-policy.json",
        "config/docs/change-contract.json",
    ):
        assert (root / relative).is_file(), relative

    nav = json.loads((root / "config/docs/nav-registry.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "config/docs/render-manifest.json").read_text(encoding="utf-8"))
    boundary = json.loads((root / "config/docs/boundary-policy.json").read_text(encoding="utf-8"))

    nav_paths = {item for section in nav["sections"] for item in section["docs"]}
    generated_paths = {entry["path"] for entry in manifest["generated_docs"]}
    fragment_paths = {entry["path"] for entry in manifest["fragments"]}

    for relative in nav_paths | generated_paths | fragment_paths | set(boundary["manual_docs"].keys()):
        assert (root / relative).exists(), relative


def test_render_docs_governance_check_passes_for_repo_snapshot() -> None:
    root = _repo_root()
    result = subprocess.run(
        [sys.executable, str(root / "scripts/governance/render_docs_governance.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_docs_governance_blocking_check_passes_for_repo_snapshot() -> None:
    root = _repo_root()
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "governance" / "check_docs_governance.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_docs_reference_done_model_and_semantic_counts() -> None:
    root = _repo_root()
    ci_topology = (root / "docs/generated/ci-topology.md").read_text(encoding="utf-8")
    release_evidence = (root / "docs/generated/release-evidence.md").read_text(encoding="utf-8")
    dashboard = (root / "docs/generated/governance-dashboard.md").read_text(encoding="utf-8")
    root_allowlist = json.loads(
        (root / "config/governance/root-allowlist.json").read_text(encoding="utf-8")
    )
    compat = json.loads(
        (root / "config/governance/upstream-compat-matrix.json").read_text(encoding="utf-8")
    )

    assert f"- root allowlist entries: `{len(root_allowlist['tracked_root_allowlist'])}`" in ci_topology
    assert "docs/reference/done-model.md" in release_evidence
    assert f"- compatibility matrix rows tracked: `{len(compat['matrix'])}`" in release_evidence
    assert "docs/reference/done-model.md" in dashboard


def test_doc_drift_script_uses_control_plane_contract() -> None:
    script = (_repo_root() / "scripts/governance/ci_or_local_gate_doc_drift.sh").read_text(encoding="utf-8")

    assert "config/docs/change-contract.json" in script
    assert "PIPELINE_STEPS_CHANGED" in script
    assert "[doc-drift] missing required doc update for" in script


def test_generated_governance_dashboard_and_required_checks_exist() -> None:
    root = _repo_root()
    for relative in (
        "docs/generated/governance-dashboard.md",
        "docs/generated/required-checks.md",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        assert "generated: docs governance control plane" in text


def test_render_docs_governance_uses_runtime_release_readiness_inputs() -> None:
    script = (_repo_root() / "scripts" / "governance" / "render_docs_governance.py").read_text(
        encoding="utf-8"
    )

    assert 'REPO_ROOT / ".runtime-cache" / "reports" / "release-readiness" / "ci-kpi-summary.json"' in script
    assert 'REPO_ROOT / "artifacts" / "release-readiness" / "ci-kpi-summary.json"' not in script


def test_reference_docs_fail_close_remote_required_checks_semantics() -> None:
    root = _repo_root()
    external_lane_status = (root / "docs" / "reference" / "external-lane-status.md").read_text(
        encoding="utf-8"
    )
    done_model = (root / "docs" / "reference" / "done-model.md").read_text(encoding="utf-8")
    newcomer_result = (
        root / "docs" / "reference" / "newcomer-result-proof.md"
    ).read_text(encoding="utf-8")

    assert "`remote-required-checks=status=pass`" in external_lane_status
    assert "aggregate-required-check integrity" in external_lane_status
    assert "`ci-final-gate`" in external_lane_status
    assert "`live-smoke`" in external_lane_status

    assert "`remote-required-checks=status=pass`" in done_model
    assert "aggregate-required-check integrity" in done_model
    assert "`nightly-flaky-*`" in done_model

    assert "`remote-required-checks=status=pass`" in newcomer_result
    assert "`ci-final-gate` / `live-smoke` / nightly terminal closure" in newcomer_result
