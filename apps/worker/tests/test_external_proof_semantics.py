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

    assert "| `ghcr-standard-image` | `historical` |" in rendered
    assert stale_head in rendered
    assert "| `ghcr-standard-image` | `verified` |" not in rendered
