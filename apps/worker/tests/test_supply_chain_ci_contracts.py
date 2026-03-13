from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_build_ci_standard_image_workflow_emits_sbom_and_attestations() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "build-ci-standard-image.yml").read_text(
        encoding="utf-8"
    )

    assert "attestations: write" in workflow
    assert "id-token: write" in workflow
    assert "artifact-metadata: write" in workflow
    assert "anchore/sbom-action@da167eac915b4e86f08b264dbdbc867b61be6f0c" in workflow
    assert "actions/attest-build-provenance@b3e506e8c389afc651c5bacf2b8f2a1ea0557215" in workflow
    assert "actions/attest@59d89421af93a897026c735860bf21b6eb4f7b26" in workflow
    assert "strict-ci-image.spdx.json" in workflow


def test_release_evidence_attestation_workflow_exists() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "release-evidence-attest.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch" in workflow
    assert "release_tag" in workflow
    assert "capture_release_manifest.sh" in workflow
    assert "actions/attest-build-provenance@b3e506e8c389afc651c5bacf2b8f2a1ea0557215" in workflow
    assert "release-evidence-" in workflow


def test_devcontainer_and_reader_stack_follow_strict_contract() -> None:
    devcontainer = (_repo_root() / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    post_create = (_repo_root() / ".devcontainer" / "post-create.sh").read_text(encoding="utf-8")
    compose = (_repo_root() / "infra" / "compose" / "miniflux-nextflux.compose.yml").read_text(
        encoding="utf-8"
    )

    assert '"workspaceFolder": "/workspace"' in devcontainer
    assert '"workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=cached"' in devcontainer
    assert '"CI_CACHE_ROOT": "/tmp/ci-cache"' in devcontainer
    assert 'eval "$(python3 scripts/ci_contract.py shell-exports)"' in post_create
    assert "STRICT_CI_DEVCONTAINER_WORKSPACE_FOLDER" in post_create
    assert "STRICT_CI_UV_VERSION" in post_create
    assert "STRICT_CI_NODE_MAJOR" in post_create
    assert "${STRICT_CI_SERVICE_IMAGE_MINIFLUX" in compose
    assert "${STRICT_CI_SERVICE_IMAGE_POSTGRES_MINIFLUX" in compose
    assert "${STRICT_CI_SERVICE_IMAGE_NEXTFLUX" in compose


def test_collect_ci_kpi_reports_artifact_and_topology_metrics(tmp_path: Path) -> None:
    junit = tmp_path / "sample-junit.xml"
    junit.write_text(
        '<testsuite tests="2" failures="1" errors="0" skipped="0" time="3.5"></testsuite>',
        encoding="utf-8",
    )
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(
        '<coverage lines-covered="90" lines-valid="100" branches-covered="45" branches-valid="50"></coverage>',
        encoding="utf-8",
    )
    coverage_summary = tmp_path / "coverage-summary.json"
    coverage_summary.write_text(
        json.dumps(
            {
                "total": {
                    "lines": {"total": 100, "covered": 95},
                    "branches": {"total": 50, "covered": 48},
                    "functions": {"total": 40, "covered": 39},
                    "statements": {"total": 100, "covered": 96},
                }
            }
        ),
        encoding="utf-8",
    )
    mutation = tmp_path / "mutmut-cicd-stats.json"
    mutation.write_text(json.dumps({"killed": 8, "survived": 2, "total": 12}), encoding="utf-8")
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"hello-world")
    workflow = tmp_path / "ci.yml"
    workflow.write_text(
        "jobs:\n  one:\n    steps:\n      - uses: ./.github/actions/normalize-self-hosted-workspace\n      - uses: ./.github/actions/setup-python-uv\n",
        encoding="utf-8",
    )
    json_out = tmp_path / "kpi.json"
    md_out = tmp_path / "kpi.md"

    result = subprocess.run(
        [
            sys.executable,
            str(_repo_root() / "scripts" / "collect_ci_kpi.py"),
            "--junit-glob",
            str(junit),
            "--coverage-xml-glob",
            str(coverage_xml),
            "--coverage-summary-glob",
            str(coverage_summary),
            "--mutation-glob",
            str(mutation),
            "--artifact-glob",
            str(artifact),
            "--workflow-glob",
            str(workflow),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["kpi"]["artifacts"]["total_bytes"] == len(b"hello-world")
    assert payload["kpi"]["topology"]["normalize_steps"] == 1
    assert payload["kpi"]["topology"]["setup_python_steps"] == 1
    assert "CI KPI Summary" in md_out.read_text(encoding="utf-8")
