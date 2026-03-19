from __future__ import annotations

import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_governance_module(module_name: str, relative_path: str):
    root = _repo_root()
    scripts_dir = root / "scripts" / "governance"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(module_name, root / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_meta(path: Path, *, source_commit: str, verification_scope: str) -> None:
    meta = {
        "version": 1,
        "artifact_path": path.as_posix(),
        "created_at": "2026-03-16T12:00:00Z",
        "source_entrypoint": "test-fixture",
        "source_run_id": "test-fixture",
        "source_commit": source_commit,
        "verification_scope": verification_scope,
        "freshness_window_hours": 24,
    }
    path.with_name(f"{path.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_current_proof_gate_rejects_stale_nested_external_verified(monkeypatch, tmp_path: Path) -> None:
    module = _load_governance_module(
        "check_current_proof_commit_alignment_test",
        "scripts/governance/check_current_proof_commit_alignment.py",
    )
    head = "1111111111111111111111111111111111111111"
    stale_head = "2222222222222222222222222222222222222222"

    workflow_artifact = tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json"
    _write_json(
        workflow_artifact,
        {
            "version": 1,
            "status": "pass",
            "source_commit": head,
            "lanes": [
                {
                    "name": "ghcr-standard-image",
                    "state": "historical",
                    "note": f"latest successful remote workflow targets old head `{stale_head}`; current HEAD `{head}` still not externally verified",
                    "latest_run_matches_current_head": False,
                    "latest_run": {
                        "databaseId": 42,
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": stale_head,
                    },
                }
            ],
        },
    )
    _write_meta(
        workflow_artifact,
        source_commit=head,
        verification_scope="external-lane-workflows",
    )

    ghcr_artifact = tmp_path / ".runtime-cache/reports/governance/standard-image-publish-readiness.json"
    _write_json(
        ghcr_artifact,
        {
            "version": 1,
            "status": "verified",
            "blocked_type": "ok",
            "source_commit": head,
        },
    )
    _write_meta(
        ghcr_artifact,
        source_commit=head,
        verification_scope="standard-image-publish-readiness",
    )

    monkeypatch.setattr(module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "current_git_commit", lambda: head)
    monkeypatch.setattr(module, "write_json_artifact", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        module,
        "load_governance_json",
        lambda _name: {
            "artifacts": [
                {
                    "name": "external-lane-workflows",
                    "artifact": ".runtime-cache/reports/governance/external-lane-workflows.json",
                    "required": True,
                    "reason": "workflow truth",
                },
                {
                    "name": "ghcr-standard-image-readiness",
                    "artifact": ".runtime-cache/reports/governance/standard-image-publish-readiness.json",
                    "required": True,
                    "reason": "current external proof",
                    "external_lane": "ghcr-standard-image",
                    "workflow_artifact": ".runtime-cache/reports/governance/external-lane-workflows.json",
                    "require_current_head_for_statuses": ["verified", "queued", "in_progress", "blocked"],
                },
            ]
        },
    )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = module.main()

    output = stdout.getvalue()
    assert exit_code == 1, output
    assert "ghcr-standard-image-readiness" in output
    assert "historical" in output
    assert "must not report `verified`" in output


def test_render_external_lane_snapshot_demotes_stale_verified_to_historical(monkeypatch, tmp_path: Path) -> None:
    module = _load_governance_module(
        "render_docs_governance_test",
        "scripts/governance/render_docs_governance.py",
    )
    head = "1111111111111111111111111111111111111111"
    stale_head = "2222222222222222222222222222222222222222"

    (tmp_path / "config" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".runtime-cache" / "reports" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".runtime-cache" / "reports" / "release").mkdir(parents=True, exist_ok=True)

    _write_json(
        tmp_path / "config/governance/external-lane-contract.json",
        {
            "version": 1,
            "lanes": [
                {
                    "name": "remote-platform-integrity",
                    "canonical_artifact": ".runtime-cache/reports/governance/remote-platform-truth.json",
                    "verification_scope": "remote-platform-truth",
                    "allowed_statuses": ["pass", "blocked"],
                    "blocked_types": ["repo-readability"],
                },
                {
                    "name": "ghcr-standard-image",
                    "canonical_artifact": ".runtime-cache/reports/governance/standard-image-publish-readiness.json",
                    "remote_workflow_artifact": ".runtime-cache/reports/governance/external-lane-workflows.json",
                    "verified_requires_current_head": True,
                    "verification_scope": "standard-image-publish-readiness",
                    "allowed_statuses": ["ready", "queued", "in_progress", "verified", "blocked", "historical"],
                    "blocked_types": ["registry-auth-failure"],
                },
                {
                    "name": "release-evidence-attestation",
                    "canonical_artifact": ".runtime-cache/reports/release/release-evidence-attest-readiness.json",
                    "remote_workflow_artifact": ".runtime-cache/reports/governance/external-lane-workflows.json",
                    "verified_requires_current_head": True,
                    "verification_scope": "release-evidence-attest-readiness",
                    "allowed_statuses": ["ready", "queued", "in_progress", "verified", "blocked", "historical"],
                    "blocked_types": ["attestation-failure"],
                },
            ],
        },
    )
    _write_json(
        tmp_path / "config/governance/upstream-compat-matrix.json",
        {
            "matrix": [
                {"name": "rsshub-youtube-ingest-chain", "verification_status": "verified", "verification_lane": "provider", "evidence_artifact": "rsshub.json"},
                {"name": "resend-digest-delivery-chain", "verification_status": "verified", "verification_lane": "provider", "evidence_artifact": "resend.json"},
                {"name": "strict-ci-compose-image-set", "verification_status": "pending", "verification_lane": "external", "evidence_artifact": "compose.json"},
            ]
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/standard-image-publish-readiness.json",
        {
            "version": 1,
            "status": "verified",
            "blocked_type": "ok",
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json",
        {
            "version": 1,
            "source_commit": head,
            "lanes": [
                {
                    "name": "ghcr-standard-image",
                    "state": "historical",
                    "note": f"latest successful remote workflow targets old head `{stale_head}`; current HEAD `{head}` still not externally verified",
                    "latest_run_matches_current_head": False,
                    "latest_run": {
                        "databaseId": 42,
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": stale_head,
                    },
                }
            ],
        },
    )

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    rendered = module._render_external_lane_snapshot()

    assert "# External Lane Truth Entry" in rendered
    assert "tracked page is a machine-rendered pointer only" in rendered
    assert ".runtime-cache/reports/governance/standard-image-publish-readiness.json" in rendered
    assert "must not carry current verdict payload" in rendered
    assert "| `ghcr-standard-image` | `verified` |" not in rendered


def test_render_current_state_summary_distinguishes_local_readiness_from_remote_push_failure(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "render_current_state_summary_test",
        "scripts/governance/render_current_state_summary.py",
    )
    head = "1111111111111111111111111111111111111111"

    (tmp_path / ".runtime-cache" / "reports" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".runtime-cache" / "reports" / "release").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "governance").mkdir(parents=True, exist_ok=True)

    _write_json(
        tmp_path / ".runtime-cache/reports/governance/standard-image-publish-readiness.json",
        {
            "version": 1,
            "status": "blocked",
            "blocker_type": "registry-auth-failure",
            "token_mode": "gh-cli",
            "token_scope_ok": False,
            "blob_upload_scope_ok": False,
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json",
        {
            "version": 1,
            "source_commit": head,
            "lanes": [
                {
                    "name": "ghcr-standard-image",
                    "state": "blocked",
                    "note": "remote workflow for current HEAD concluded `failure`; preflight passed",
                    "latest_run_matches_current_head": True,
                    "latest_run": {
                        "databaseId": 42,
                        "status": "completed",
                        "conclusion": "failure",
                        "headSha": head,
                    },
                    "failure_details": {
                        "failed_step_name": "Build and push strict CI standard image",
                        "failure_signature": "blob-head-403-forbidden",
                    },
                }
            ],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-platform-truth.json",
        {"version": 1, "status": "pass", "blocker_type": ""},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-required-checks.json",
        {
            "version": 1,
            "status": "pass",
            "expected_required_checks": ["a"],
            "actual_required_checks": ["a"],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/open-source-audit-freshness.json",
        {"version": 1, "status": "pass"},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/newcomer-result-proof.json",
        {
            "version": 1,
            "status": "partial",
            "repo_side_strict_receipt": {"status": "pass"},
        },
    )
    _write_json(tmp_path / "config/governance/upstream-compat-matrix.json", {"matrix": []})

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_current_head", lambda: head)
    monkeypatch.setattr(module, "_worktree_changes", lambda: [" M apps/worker/worker/comments/youtube.py"])

    rendered = module.render()

    assert "local readiness artifact=blocked:registry-auth-failure" in rendered
    assert "latest remote current-head workflow preflight passed" in rendered
    assert "GHCR blob HEAD returned 403 Forbidden" in rendered


def test_render_current_state_summary_keeps_release_lane_as_readiness_when_remote_workflow_is_historical(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "render_current_state_summary_release_historical_test",
        "scripts/governance/render_current_state_summary.py",
    )
    head = "1111111111111111111111111111111111111111"
    stale_head = "2222222222222222222222222222222222222222"

    (tmp_path / ".runtime-cache" / "reports" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".runtime-cache" / "reports" / "release").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "governance").mkdir(parents=True, exist_ok=True)

    _write_json(
        tmp_path / ".runtime-cache/reports/release/release-evidence-attest-readiness.json",
        {
            "version": 1,
            "status": "ready",
            "blocker_type": "",
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json",
        {
            "version": 1,
            "source_commit": head,
            "lanes": [
                {
                    "name": "release-evidence-attestation",
                    "state": "historical",
                    "note": f"latest successful remote workflow targets old head `{stale_head}`; current HEAD `{head}` still not externally verified",
                    "latest_run_matches_current_head": False,
                    "latest_run": {
                        "databaseId": 41,
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": stale_head,
                    },
                }
            ],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-platform-truth.json",
        {"version": 1, "status": "pass", "blocker_type": ""},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-required-checks.json",
        {
            "version": 1,
            "status": "pass",
            "expected_required_checks": ["a"],
            "actual_required_checks": ["a"],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/open-source-audit-freshness.json",
        {"version": 1, "status": "pass"},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/newcomer-result-proof.json",
        {
            "version": 1,
            "status": "pass",
            "repo_side_strict_receipt": {"status": "pass"},
        },
    )
    _write_json(tmp_path / "config/governance/upstream-compat-matrix.json", {"matrix": []})

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_current_head", lambda: head)
    monkeypatch.setattr(module, "_worktree_changes", list)

    rendered = module.render()

    assert "| `release-evidence-attestation` | `verified` |" not in rendered
    assert "| `release-evidence-attestation` | `ready` |" in rendered
    assert "remote workflow is historical for current HEAD and does not count as current external verification" in rendered


def test_current_state_summary_check_rejects_stale_summary_and_historical_greenwash(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "check_current_state_summary_test",
        "scripts/governance/check_current_state_summary.py",
    )
    head = "1111111111111111111111111111111111111111"
    stale_head = "2222222222222222222222222222222222222222"

    summary_path = tmp_path / ".runtime-cache/reports/governance/current-state-summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        "\n".join(
            [
                "# Current State Summary",
                "",
                f"- current HEAD: `{stale_head}`",
                "",
                "| Lane | Current State | Evidence / Note | Canonical Artifact |",
                "| --- | --- | --- | --- |",
                "| `release-evidence-attestation` | `verified` | stale | `x` |",
                "| `workflow:release-evidence-attestation` | `historical` | stale workflow | `y` |",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_meta(
        summary_path,
        source_commit=stale_head,
        verification_scope="current-state-summary",
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json",
        {
            "version": 1,
            "source_commit": head,
            "lanes": [
                {
                    "name": "release-evidence-attestation",
                    "state": "historical",
                    "note": "historical run",
                    "latest_run_matches_current_head": False,
                    "latest_run": {
                        "databaseId": 51,
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": stale_head,
                    },
                }
            ],
        },
    )

    monkeypatch.setattr(module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "current_git_commit", lambda: head)

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = module.main()

    output = stdout.getvalue()
    assert exit_code == 1, output
    assert "source_commit does not match current HEAD" in output
    assert "must not be rendered as `verified`" in output


def test_current_proof_contract_requires_critical_external_current_artifacts() -> None:
    payload = json.loads(
        (_repo_root() / "config" / "governance" / "current-proof-contract.json").read_text(
            encoding="utf-8"
        )
    )

    artifacts = {
        item["name"]: item
        for item in payload["artifacts"]
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    for name in (
        "remote-platform-truth",
        "remote-required-checks",
        "ghcr-standard-image-readiness",
        "external-lane-workflows",
        "release-evidence-attestation",
    ):
        assert artifacts[name]["required"] is True

    assert artifacts["remote-required-checks"]["reason"].startswith("fail-close:")


def test_probe_remote_platform_truth_uses_dedicated_pvr_endpoint_when_repo_field_missing(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "probe_remote_platform_truth_test",
        "scripts/governance/probe_remote_platform_truth.py",
    )
    head = "1111111111111111111111111111111111111111"

    def _fake_json_or_none(command: list[str]):
        cmd = " ".join(command)
        if cmd == "gh api user":
            return {"login": "tester"}, None
        if cmd.startswith("gh repo view "):
            return {
                "name": "video-analysis-extract",
                "owner": {"login": "xiaojiou176-org"},
                "visibility": "PUBLIC",
                "defaultBranchRef": {"name": "main"},
                "isPrivate": False,
            }, None
        if cmd == "gh api repos/xiaojiou176-org/video-analysis-extract":
            return {
                "private_vulnerability_reporting": None,
                "security_and_analysis": {},
            }, None
        if cmd == "gh api repos/xiaojiou176-org/video-analysis-extract/private-vulnerability-reporting":
            return {"enabled": True}, None
        if cmd == "gh api repos/xiaojiou176-org/video-analysis-extract/actions/permissions":
            return {"enabled": True}, None
        if cmd == "gh api repos/xiaojiou176-org/video-analysis-extract/branches/main/protection":
            return {
                "required_status_checks": {
                    "contexts": [],
                }
            }, None
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_repo_slug", lambda: "xiaojiou176-org/video-analysis-extract")
    monkeypatch.setattr(module, "_current_actor", lambda: "tester")
    monkeypatch.setattr(module, "_run", lambda *args, check=True: type("R", (), {"returncode": 0, "stdout": '{"login":"tester"}', "stderr": ""})())
    monkeypatch.setattr(module, "_json_or_none", _fake_json_or_none)
    monkeypatch.setattr(module, "_load_required_checks", list)
    monkeypatch.setattr(module, "_actual_required_checks", lambda payload: [])
    monkeypatch.setattr(module, "current_git_commit", lambda: head)

    captured = {}

    def _capture_artifact(path, report, **kwargs):
        captured["report"] = report

    monkeypatch.setattr(module, "write_json_artifact", _capture_artifact)
    monkeypatch.setattr(sys, "argv", ["probe_remote_platform_truth.py", "--repo", "xiaojiou176-org/video-analysis-extract"])

    exit_code = module.main()

    assert exit_code == 0
    assert captured["report"]["private_vulnerability_reporting"]["status"] == "enabled"
    assert captured["report"]["private_vulnerability_reporting"]["reason"].startswith("dedicated private-vulnerability-reporting endpoint")


def test_newcomer_workspace_verdict_dirty_worktree_forces_partial() -> None:
    module = _load_governance_module(
        "render_newcomer_result_proof_dirty_verdict_test",
        "scripts/governance/render_newcomer_result_proof.py",
    )

    status, blockers, note = module._workspace_verdict(
        newcomer_preflight_status="pass",
        governance_status="pass",
        repo_side_strict_status="pass",
        current_proof={"exists": True, "current_commit_aligned": True},
        worktree_dirty=True,
    )

    assert status == "partial"
    assert blockers == ["dirty_worktree"]
    assert "last committed snapshot" in note


def test_newcomer_workspace_verdict_missing_preflight_stays_missing_even_when_dirty() -> None:
    module = _load_governance_module(
        "render_newcomer_result_proof_missing_preflight_test",
        "scripts/governance/render_newcomer_result_proof.py",
    )

    status, blockers, note = module._workspace_verdict(
        newcomer_preflight_status="missing",
        governance_status="pass",
        repo_side_strict_status="pass",
        current_proof={"exists": True, "current_commit_aligned": True},
        worktree_dirty=True,
    )

    assert status == "missing"
    assert "newcomer_preflight_missing" in blockers
    assert "dirty_worktree" in blockers
    assert "missing" in note


def test_newcomer_result_proof_check_rejects_dirty_partial_without_explicit_blocker(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "check_newcomer_result_proof_dirty_blocker_test",
        "scripts/governance/check_newcomer_result_proof.py",
    )
    head = "1111111111111111111111111111111111111111"

    report_path = tmp_path / ".runtime-cache/reports/governance/newcomer-result-proof.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        report_path,
        {
            "version": 1,
            "status": "partial",
            "source_commit": head,
            "current_workspace_verdict": {
                "status": "partial",
                "blocking_conditions": [],
                "note": "incorrect fixture",
            },
            "newcomer_preflight": {
                "status": "pass",
                "resolved_env_exists": True,
            },
            "governance_audit_receipt": {"status": "pass"},
            "repo_side_strict_receipt": {"status": "pass"},
            "worktree_state": {
                "dirty": True,
            },
            "current_proof_alignment": {
                "exists": True,
                "current_commit_aligned": True,
            },
            "eval_regression": {"status": "passed"},
        },
    )
    _write_meta(
        report_path,
        source_commit=head,
        verification_scope="newcomer-result-proof",
    )

    monkeypatch.setattr(module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "current_git_commit", lambda: head)

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = module.main()

    output = stdout.getvalue()
    assert exit_code == 1, output
    assert "dirty worktree must be listed" in output


def test_render_current_state_summary_explains_pending_strict_ci_compose_row_via_ghcr_blocker(
    monkeypatch, tmp_path: Path
) -> None:
    module = _load_governance_module(
        "render_current_state_summary_pending_compose_row_test",
        "scripts/governance/render_current_state_summary.py",
    )
    head = "1111111111111111111111111111111111111111"

    (tmp_path / ".runtime-cache" / "reports" / "governance").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".runtime-cache" / "reports" / "release").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "governance").mkdir(parents=True, exist_ok=True)

    _write_json(
        tmp_path / ".runtime-cache/reports/governance/standard-image-publish-readiness.json",
        {
            "version": 1,
            "status": "blocked",
            "blocker_type": "registry-auth-failure",
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/external-lane-workflows.json",
        {
            "version": 1,
            "source_commit": head,
            "lanes": [
                {
                    "name": "ghcr-standard-image",
                    "state": "blocked",
                    "note": "remote workflow for current HEAD concluded `failure`",
                    "latest_run_matches_current_head": True,
                    "latest_run": {
                        "databaseId": 42,
                        "status": "completed",
                        "conclusion": "failure",
                        "headSha": head,
                    },
                    "failure_details": {
                        "failed_step_name": "Standard image publish preflight",
                    },
                }
            ],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-platform-truth.json",
        {"version": 1, "status": "pass", "blocker_type": ""},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/remote-required-checks.json",
        {
            "version": 1,
            "status": "pass",
            "expected_required_checks": ["a"],
            "actual_required_checks": ["a"],
        },
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/open-source-audit-freshness.json",
        {"version": 1, "status": "pass"},
    )
    _write_json(
        tmp_path / ".runtime-cache/reports/governance/newcomer-result-proof.json",
        {
            "version": 1,
            "status": "pass",
            "current_workspace_verdict": {"status": "pass", "blocking_conditions": []},
            "repo_side_strict_receipt": {"status": "pass"},
        },
    )
    _write_json(
        tmp_path / "config/governance/upstream-compat-matrix.json",
        {
            "matrix": [
                {
                    "name": "strict-ci-compose-image-set",
                    "verification_status": "pending",
                    "verification_lane": "external",
                    "evidence_artifact": ".runtime-cache/reports/governance/upstream-compat-report.json",
                }
            ]
        },
    )

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "_current_head", lambda: head)
    monkeypatch.setattr(module, "_worktree_changes", list)

    rendered = module.render()

    assert "| `strict-ci-compose-image-set` | `pending` | external; blocked on `ghcr-standard-image` (registry-auth-failure) |" in rendered
