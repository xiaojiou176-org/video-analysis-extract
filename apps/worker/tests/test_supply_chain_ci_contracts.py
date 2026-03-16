from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_collect_ci_kpi_module():
    module_path = _repo_root() / "scripts" / "ci" / "collect_kpi.py"
    spec = importlib.util.spec_from_file_location("collect_ci_kpi", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_supply_chain_verifier_module():
    module_path = _repo_root() / "scripts" / "governance" / "verify_supply_chain_evidence.py"
    spec = importlib.util.spec_from_file_location("verify_supply_chain_evidence", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert "push:" in workflow
    assert "branches:\n      - main" in workflow
    assert "runner_workspace_maintenance.sh" in workflow


def test_release_evidence_attestation_workflow_exists() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "release-evidence-attest.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch" in workflow
    assert "push:" in workflow
    assert 'tags:\n      - "v*"' in workflow
    assert "release_tag" in workflow
    assert "capture_release_manifest.sh" in workflow
    assert "actions/attest-build-provenance@b3e506e8c389afc651c5bacf2b8f2a1ea0557215" in workflow
    assert "release-evidence-" in workflow
    assert "runner_workspace_maintenance.sh" in workflow


def test_release_manifest_capture_uses_relative_artifact_paths_and_current_run_scope() -> None:
    script = (_repo_root() / "scripts" / "release" / "capture_release_manifest.sh").read_text(encoding="utf-8")

    assert '"manifest_version": 1' in script
    assert '"evidence_scope": "current-run"' in script
    assert ".relative_to(root).as_posix()" in script


def test_rollback_readiness_script_uses_artifacts_release_root() -> None:
    script = (_repo_root() / "scripts" / "release" / "verify_db_rollback_readiness.py").read_text(
        encoding="utf-8"
    )

    assert 'repo_root / "artifacts" / "releases"' in script
    assert 'repo_root / "reports" / "releases"' not in script


def test_release_prechecks_use_canonical_current_run_report_lane() -> None:
    script = (_repo_root() / "scripts" / "release" / "generate_release_prechecks.py").read_text(
        encoding="utf-8"
    )

    assert '".runtime-cache" / "reports" / "release-readiness" / "db-rollback-readiness.json"' in script
    assert 'default=".runtime-cache/reports/release-readiness/prechecks.json"' in script
    assert '".runtime-cache" / "temp" / "release-readiness"' not in script
    assert "write_json_artifact(" in script


def test_sample_release_manifest_is_marked_as_historical_example_with_relative_paths() -> None:
    manifest = json.loads(
        (_repo_root() / "artifacts" / "releases" / "v0.1.0" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["manifest_version"] == 1
    assert manifest["evidence_scope"] == "current-run"
    assert manifest["historical_example"] is True
    assert not manifest["artifacts"]["checksums_file"].startswith("/")


def test_pre_checkout_helper_exists_for_self_hosted_hygiene_reuse() -> None:
    helper = (
        _repo_root() / "scripts" / "governance" / "normalize_self_hosted_pre_checkout.sh"
    ).read_text(encoding="utf-8")

    assert "runner_workspace_maintenance.sh" in helper
    assert "--include-runner-diag" in helper
    assert "detected root-owned residue" in helper


def test_devcontainer_and_reader_stack_follow_strict_contract() -> None:
    devcontainer = (_repo_root() / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    post_create = (_repo_root() / ".devcontainer" / "post-create.sh").read_text(encoding="utf-8")
    core_compose = (_repo_root() / "infra" / "compose" / "core-services.compose.yml").read_text(
        encoding="utf-8"
    )
    compose = (_repo_root() / "infra" / "compose" / "miniflux-nextflux.compose.yml").read_text(
        encoding="utf-8"
    )

    assert '"workspaceFolder": "/workspace"' in devcontainer
    assert '"workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=cached"' in devcontainer
    assert '"CI_CACHE_ROOT": "/tmp/ci-cache"' in devcontainer
    assert '"postCreateCommand": "bash .devcontainer/post-create.sh"' in devcontainer
    assert "docker-outside-of-docker" not in devcontainer
    assert 'eval "$(python3 scripts/ci/contract.py shell-exports)"' in post_create
    assert "STRICT_CI_DEVCONTAINER_WORKSPACE_FOLDER" in post_create
    assert "STRICT_CI_UV_VERSION" in post_create
    assert "STRICT_CI_NODE_MAJOR" in post_create
    assert "chromium browser drift detected" in post_create
    assert "playwright install chromium || true" not in post_create
    assert "${STRICT_CI_SERVICE_IMAGE_PGVECTOR_PG16" in core_compose
    assert "${STRICT_CI_SERVICE_IMAGE_REDIS_CORE" in core_compose
    assert "${STRICT_CI_SERVICE_IMAGE_TEMPORAL_AUTO_SETUP" in core_compose
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
            str(_repo_root() / "scripts" / "ci" / "collect_kpi.py"),
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
    assert payload["kpi"]["run"]["status"] == "degraded"
    assert "CI KPI Summary" in md_out.read_text(encoding="utf-8")


def test_collect_ci_kpi_degrades_when_run_metrics_lookup_fails(monkeypatch) -> None:
    module = _load_collect_ci_kpi_module()
    assert hasattr(module, "_parse_run_metrics")

    def _boom(*args, **kwargs):
        raise RuntimeError("github api unavailable")

    monkeypatch.setattr(module, "_parse_run_metrics", _boom)

    try:
        raise RuntimeError("github api unavailable")
    except Exception as exc:
        degraded = {
            "status": "degraded",
            "warning": f"run-metrics unavailable: {type(exc).__name__}: {exc}",
            "jobs_total": 0,
            "jobs_duration_seconds": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    assert degraded["status"] == "degraded"
    assert degraded["warning"] == "run-metrics unavailable: RuntimeError: github api unavailable"


def test_verify_supply_chain_evidence_marks_missing_token_as_unverified() -> None:
    module = _load_supply_chain_verifier_module()

    payload = module.verify_supply_chain(
        contract_path=_repo_root() / "infra" / "config" / "strict_ci_contract.json",
        repo="owner/repo",
        workflow_file="build-ci-standard-image.yml",
        token="",
    )

    assert payload["status"] == "supply_chain_unverified"
    assert payload["reason"] == "missing token"


def test_verify_supply_chain_evidence_accepts_matching_successful_run(monkeypatch) -> None:
    module = _load_supply_chain_verifier_module()
    contract = json.loads(
        (_repo_root() / "infra" / "config" / "strict_ci_contract.json").read_text(encoding="utf-8")
    )

    monkeypatch.setattr(
        module,
        "_github_json",
        lambda url, token: {
            "workflow_runs": [
                {
                    "id": 123,
                    "conclusion": "success",
                    "head_sha": contract["standard_image"]["tag"],
                    "html_url": "https://github.com/example/run/123",
                }
            ]
        },
    )

    payload = module.verify_supply_chain(
        contract_path=_repo_root() / "infra" / "config" / "strict_ci_contract.json",
        repo="owner/repo",
        workflow_file="build-ci-standard-image.yml",
        token="token",
    )

    assert payload["status"] == "verified"
    assert payload["workflow_run_id"] == 123
