from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_governance_control_plane_files_exist_and_are_populated() -> None:
    root = _repo_root()
    config_dir = root / "config" / "governance"
    required = [
        "root-allowlist.json",
        "runtime-outputs.json",
        "logging-contract.json",
        "dependency-boundaries.json",
        "active-upstreams.json",
        "upstream-templates.json",
        "upstream-compat-matrix.json",
    ]

    for name in required:
        path = config_dir / name
        assert path.is_file(), f"missing governance config: {name}"
        payload = json.loads(path.read_text(encoding="utf-8"))
        version = payload.get("version")
        assert isinstance(version, int) and version >= 1

    runtime_outputs = json.loads((config_dir / "runtime-outputs.json").read_text(encoding="utf-8"))
    assert set(runtime_outputs["subdirectories"]) == {
        "run",
        "logs",
        "reports",
        "evidence",
        "tmp",
        "temp",
    }

    logging_contract = json.loads((config_dir / "logging-contract.json").read_text(encoding="utf-8"))
    assert set(logging_contract["channels"]) == {
        "app",
        "components",
        "tests",
        "governance",
        "infra",
        "upstreams",
    }

    dependency_boundaries = json.loads(
        (config_dir / "dependency-boundaries.json").read_text(encoding="utf-8")
    )
    assert dependency_boundaries["internal_roots"] == ["apps.", "integrations."]
    for entry in dependency_boundaries["python_rules"]:
        assert "allow_internal_prefixes" in entry
    for entry in dependency_boundaries["frontend_rules"]:
        assert "allow_import_prefixes" in entry
    assert dependency_boundaries["package_purity_rules"]

    upstreams = json.loads((config_dir / "active-upstreams.json").read_text(encoding="utf-8"))
    for entry in upstreams["entries"]:
        assert "evidence_artifact" in entry
        assert "license" in entry
        assert "risk_class" in entry
        assert "integration_surface" in entry
        assert "private_coupling_risk" in entry
        assert "security_posture" in entry

    templates = json.loads((config_dir / "upstream-templates.json").read_text(encoding="utf-8"))
    for entry in templates["entries"]:
        assert entry["kind"] in {"vendor", "fork", "patch"}

    matrix = json.loads((config_dir / "upstream-compat-matrix.json").read_text(encoding="utf-8"))
    for row in matrix["matrix"]:
        assert "verification_entrypoint" in row
        assert "evidence_artifact" in row
        assert "verification_status" in row
        assert "verification_artifacts" in row


def test_governance_gate_script_wires_all_terminal_checks() -> None:
    script = (_repo_root() / "scripts" / "governance" / "gate.sh").read_text(encoding="utf-8")

    assert "--mode pre-commit|pre-push|ci|audit" in script
    assert "python3 scripts/governance/check_root_allowlist.py" in script
    assert "python3 scripts/governance/check_public_entrypoint_manifests.py" in script
    assert "python3 scripts/governance/check_runtime_outputs.py" in script
    assert "python3 scripts/governance/check_runtime_artifact_writer_coverage.py" in script
    assert "python3 scripts/governance/check_governance_language.py" in script
    assert "python3 scripts/governance/check_dependency_boundaries.py" in script
    assert "python3 scripts/governance/check_logging_contract.py" in script
    assert "python3 scripts/governance/check_run_manifest_completeness.py" in script
    assert "python3 scripts/governance/check_upstream_governance.py" in script


def test_vendor_governance_workflow_uses_governance_gate_inventory_check() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "vendor-governance.yml").read_text(
        encoding="utf-8"
    )

    assert "config/governance/active-upstreams.json" in workflow
    assert "config/governance/upstream-templates.json" in workflow
    assert "config/governance/upstream-compat-matrix.json" in workflow
    assert "./bin/governance-audit --mode ci" in workflow


def test_monthly_governance_workflow_exists() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "monthly-governance-audit.yml")
    content = workflow.read_text(encoding="utf-8")

    assert workflow.is_file()
    assert 'cron: "0 10 1 * *"' in content
    assert "./bin/governance-audit --mode audit" in content
    assert "check_root_dirtiness_after_tasks.py --write-snapshot" in content
    assert "check_root_dirtiness_after_tasks.py --compare-snapshot .runtime-cache/reports/governance/root-before.json" in content


def test_runtime_and_logging_contracts_reference_runtime_cache_root() -> None:
    runtime_outputs = (_repo_root() / "config" / "governance" / "runtime-outputs.json").read_text(
        encoding="utf-8"
    )
    logging_contract = (_repo_root() / "config" / "governance" / "logging-contract.json").read_text(
        encoding="utf-8"
    )
    readme = (_repo_root() / "README.md").read_text(encoding="utf-8")
    full_stack = (_repo_root() / "scripts" / "runtime" / "full_stack.sh").read_text(encoding="utf-8")

    assert '".runtime-cache"' in runtime_outputs
    assert '".runtime-cache/logs/' in logging_contract
    assert ".runtime-cache/logs/components/full-stack" in readme
    assert 'LOG_DIR="$ROOT_DIR/.runtime-cache/logs/components/full-stack"' in full_stack
    assert "legacy_runtime_patterns" not in runtime_outputs


def test_shell_logging_helper_contract_exists_and_is_wired() -> None:
    root = _repo_root()
    helper = (root / "scripts" / "runtime" / "logging.sh").read_text(encoding="utf-8")
    governance_gate = (root / "scripts" / "governance" / "gate.sh").read_text(encoding="utf-8")
    full_stack = (root / "scripts" / "runtime" / "full_stack.sh").read_text(encoding="utf-8")
    api_real_smoke = (root / "scripts" / "ci" / "api_real_smoke_local.sh").read_text(encoding="utf-8")
    smoke_llm_real = (root / "scripts" / "ci" / "smoke_llm_real_local.sh").read_text(encoding="utf-8")
    external_smoke = (root / "scripts" / "ci" / "external_playwright_smoke.sh").read_text(encoding="utf-8")

    assert "vd_log_init()" in helper
    assert "scripts/runtime/log_jsonl_event.py" in helper
    assert 'source "$ROOT_DIR/scripts/runtime/logging.sh"' in governance_gate
    assert 'vd_log_init "governance"' in governance_gate
    assert 'vd_log_init "components" "$SCRIPT_NAME"' in full_stack
    assert 'vd_log_init "tests" "$SCRIPT_NAME"' in api_real_smoke
    assert 'vd_log_init "tests" "$SCRIPT_NAME"' in smoke_llm_real
    assert 'vd_log_init "tests" "$SCRIPT_NAME"' in external_smoke


def test_runtime_jsonl_logging_script_emits_required_fields(tmp_path: Path) -> None:
    root = _repo_root()
    output_path = tmp_path / "governance.jsonl"

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime" / "log_jsonl_event.py"),
            "--path",
            str(output_path),
            "--run-id",
            "run-123",
            "--trace-id",
            "trace-123",
            "--request-id",
            "req-123",
            "--component",
            "governance-gate",
            "--channel",
            "governance",
            "--event",
            "start",
            "--severity",
            "info",
            "--message",
            "hello",
        ],
        check=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8").strip())
    assert payload["run_id"] == "run-123"
    assert payload["trace_id"] == "trace-123"
    assert payload["request_id"] == "req-123"
    assert payload["component"] == "governance-gate"
    assert payload["channel"] == "governance"
    assert payload["event"] == "start"
    assert payload["severity"] == "info"
    assert payload["ts"]


def test_runtime_outputs_contract_has_no_legacy_ui_audit_children() -> None:
    runtime_outputs = json.loads(
        (_repo_root() / "config" / "governance" / "runtime-outputs.json").read_text(
            encoding="utf-8"
        )
    )
    serialized = json.dumps(runtime_outputs, ensure_ascii=False)

    assert '"ui-audit"' not in serialized
    assert '"ui-audit-runs"' not in serialized


def test_logging_sample_generator_and_contract_checker_pass() -> None:
    root = _repo_root()

    subprocess.run(
        [sys.executable, str(root / "scripts" / "governance" / "generate_logging_samples.py")],
        cwd=root,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(root / "scripts" / "governance" / "check_logging_contract.py")],
        cwd=root,
        check=True,
    )
