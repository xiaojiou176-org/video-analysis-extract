#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config" / "docs"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _check_paths_exist(paths: list[str], *, allow_missing: bool = False) -> list[str]:
    failures: list[str] = []
    for raw in paths:
        target = REPO_ROOT / raw
        if allow_missing:
            continue
        if not target.exists():
            failures.append(f"missing path: {raw}")
    return failures


def _check_control_plane() -> list[str]:
    failures: list[str] = []
    nav = _load_json(CONFIG_DIR / "nav-registry.json")
    manifest = _load_json(CONFIG_DIR / "render-manifest.json")
    boundary = _load_json(CONFIG_DIR / "boundary-policy.json")
    change_contract = _load_json(CONFIG_DIR / "change-contract.json")

    nav_docs = []
    for section in nav.get("sections", []):
        nav_docs.extend(section.get("docs", []))
    failures.extend(_check_paths_exist(nav_docs))

    render_paths = [entry["path"] for entry in manifest.get("generated_docs", [])]
    failures.extend(_check_paths_exist(render_paths))

    fragment_paths = [entry["path"] for entry in manifest.get("fragments", [])]
    failures.extend(_check_paths_exist(fragment_paths))

    manual_docs = boundary.get("manual_docs", {})
    for path, payload in manual_docs.items():
        target = REPO_ROOT / path
        if not target.exists():
            failures.append(f"manual boundary doc missing: {path}")
            continue
        text = target.read_text(encoding="utf-8")
        for marker in payload.get("generated_markers", []):
            start = f"<!-- docs:generated {marker} start -->"
            end = f"<!-- docs:generated {marker} end -->"
            if start not in text or end not in text:
                failures.append(f"manual doc missing generated marker `{marker}`: {path}")

    for rule in change_contract.get("rules", []):
        failures.extend(_check_paths_exist(rule.get("required_paths", [])))

    if not boundary.get("trust_boundary", {}).get("mode"):
        failures.append("boundary policy missing trust_boundary.mode")
    if "render_only_paths" in boundary:
        failures.append(
            "boundary-policy.json: render_only_paths has been retired; render-only docs must be declared only in config/docs/render-manifest.json"
        )

    return failures


def _check_render_freshness() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "governance" / "render_docs_governance.py"), "--check"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    lines = [line for line in result.stdout.splitlines() + result.stderr.splitlines() if line.strip()]
    return lines or ["docs governance render freshness failed"]


def _extract_workflow_job_runs_on(workflow_text: str, job_name: str) -> str | None:
    match = re.search(
        rf"^\s{{2}}{re.escape(job_name)}:\n(?P<body>(?:^\s{{4}}.*\n?)*)",
        workflow_text,
        flags=re.MULTILINE,
    )
    if not match:
        return None
    body = match.group("body")
    runner_match = re.search(r"^\s{4}runs-on:\s*(.+)$", body, flags=re.MULTILINE)
    if not runner_match:
        return None
    return runner_match.group(1).strip()


def _expected_ci_topology_standard_image_line() -> str:
    workflow_text = (REPO_ROOT / ".github" / "workflows" / "build-ci-standard-image.yml").read_text(
        encoding="utf-8"
    )
    runner = _extract_workflow_job_runs_on(workflow_text, "publish") or "unknown"
    buildx_index = workflow_text.find("Set up Docker Buildx")
    build_script_index = workflow_text.find("./scripts/ci/build_standard_image.sh")
    if buildx_index >= 0 and build_script_index >= 0 and buildx_index < build_script_index:
        return (
            "- GHCR image publish workflow runs on "
            f"`{runner}` and sets up Docker Buildx before calling `scripts/ci/build_standard_image.sh`"
        )
    if build_script_index >= 0:
        return (
            "- GHCR image publish workflow runs on "
            f"`{runner}` and calls `scripts/ci/build_standard_image.sh` in the `publish` job"
        )
    return f"- GHCR image publish workflow runs on `{runner}`"


def _check_generated_doc_semantics() -> list[str]:
    failures: list[str] = []
    runtime_outputs = _load_json(REPO_ROOT / "config" / "governance" / "runtime-outputs.json")
    root_allowlist = _load_json(REPO_ROOT / "config" / "governance" / "root-allowlist.json")
    compat = _load_json(REPO_ROOT / "config" / "governance" / "upstream-compat-matrix.json")

    ci_topology = (REPO_ROOT / "docs" / "generated" / "ci-topology.md").read_text(encoding="utf-8")
    expected_root_line = f"- root allowlist entries: `{len(root_allowlist.get('tracked_root_allowlist', []))}`"
    if expected_root_line not in ci_topology:
        failures.append("docs/generated/ci-topology.md: root allowlist count drifted from control plane")
    expected_runtime_root = f"- runtime root: `{runtime_outputs.get('runtime_root', '.runtime-cache')}`"
    if expected_runtime_root not in ci_topology:
        failures.append("docs/generated/ci-topology.md: runtime root drifted from control plane")
    if ".runtime-cache/reports/release/release-evidence-attest-readiness.json" not in ci_topology:
        failures.append(
            "docs/generated/ci-topology.md: missing release-evidence attestation readiness path"
        )
    if "- current-run readiness reports: `.runtime-cache/reports/release-readiness/`" in ci_topology:
        failures.append(
            "docs/generated/ci-topology.md: still uses ambiguous release-readiness wording"
        )
    expected_standard_image_line = _expected_ci_topology_standard_image_line()
    if expected_standard_image_line not in ci_topology:
        failures.append(
            "docs/generated/ci-topology.md: GHCR standard image workflow runner/buildx wording drifted from `.github/workflows/build-ci-standard-image.yml`"
        )
    if "GHCR image publish workflow primes Docker Buildx on self-hosted runners" in ci_topology:
        failures.append(
            "docs/generated/ci-topology.md: still claims GHCR standard image publish runs on self-hosted runners"
        )

    runner_baseline = (REPO_ROOT / "docs" / "generated" / "runner-baseline.md").read_text(
        encoding="utf-8"
    )
    if ".runtime-cache/reports/release/" not in runner_baseline:
        failures.append(
            "docs/generated/runner-baseline.md: missing release-evidence attestation readiness path"
        )
    if "- current-run release/readiness reports are emitted under `.runtime-cache/reports/release-readiness/`" in runner_baseline:
        failures.append(
            "docs/generated/runner-baseline.md: still uses old combined release/readiness wording"
        )

    release_reference = (REPO_ROOT / "docs" / "generated" / "release-evidence.md").read_text(
        encoding="utf-8"
    )
    expected_rows_line = f"- compatibility matrix rows tracked: `{len(compat.get('matrix', []))}`"
    if expected_rows_line not in release_reference:
        failures.append("docs/generated/release-evidence.md: compatibility row count drifted from control plane")
    if "docs/reference/done-model.md" not in release_reference:
        failures.append("docs/generated/release-evidence.md: missing done-model reference")
    if ".runtime-cache/reports/release/release-evidence-attest-readiness.json" not in release_reference:
        failures.append(
            "docs/generated/release-evidence.md: missing release-evidence attestation readiness path"
        )
    if "- current-run KPI and readiness summaries live under `.runtime-cache/reports/release-readiness/`" in release_reference:
        failures.append(
            "docs/generated/release-evidence.md: still mixes release readiness with release-evidence attestation"
        )

    governance_dashboard = (
        REPO_ROOT / "docs" / "generated" / "governance-dashboard.md"
    ).read_text(encoding="utf-8")
    if "docs/reference/done-model.md" not in governance_dashboard:
        failures.append("docs/generated/governance-dashboard.md: missing done-model reference")

    external_lane_status = (
        REPO_ROOT / "docs" / "reference" / "external-lane-status.md"
    ).read_text(encoding="utf-8")
    if "merge-relevant required-check integrity" not in external_lane_status:
        failures.append(
            "docs/reference/external-lane-status.md: missing merge-relevant required-check integrity wording"
        )
    if "`ci-final-gate`" not in external_lane_status or "`live-smoke`" not in external_lane_status:
        failures.append(
            "docs/reference/external-lane-status.md: missing terminal CI closure examples for remote-required-checks semantics"
        )
    if "`remote-required-checks=status=pass`" not in external_lane_status:
        failures.append(
            "docs/reference/external-lane-status.md: missing explicit remote-required-checks status reading rule"
        )

    done_model = (REPO_ROOT / "docs" / "reference" / "done-model.md").read_text(encoding="utf-8")
    if "aggregate-required-check integrity" not in done_model:
        failures.append("docs/reference/done-model.md: missing aggregate-required-check integrity wording")
    if "`remote-required-checks=status=pass`" not in done_model:
        failures.append("docs/reference/done-model.md: missing explicit remote-required-checks status rule")
    if "`nightly-flaky-*" not in done_model:
        failures.append("docs/reference/done-model.md: missing nightly terminal-lane example")

    newcomer_result_proof = (
        REPO_ROOT / "docs" / "reference" / "newcomer-result-proof.md"
    ).read_text(encoding="utf-8")
    if "`remote-required-checks=status=pass`" not in newcomer_result_proof:
        failures.append(
            "docs/reference/newcomer-result-proof.md: missing explicit remote-required-checks non-equivalence rule"
        )
    if "`ci-final-gate` / `live-smoke` / nightly terminal closure" not in newcomer_result_proof:
        failures.append(
            "docs/reference/newcomer-result-proof.md: missing explicit terminal-closure non-equivalence rule"
        )
    return failures


def main() -> int:
    failures = _check_control_plane()
    failures.extend(_check_render_freshness())
    failures.extend(_check_generated_doc_semantics())
    if failures:
        print("docs governance check failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("docs governance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
