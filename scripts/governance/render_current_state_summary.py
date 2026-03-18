#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "governance"))

from common import write_text_artifact
OUTPUT_PATH = REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "current-state-summary.md"
GENERATED_HEADER = "<!-- runtime-generated: current-state-summary; do not edit directly -->\n"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _maybe_load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return _load_json(path)


def _current_head() -> str:
    head_path = REPO_ROOT / ".git" / "HEAD"
    if not head_path.exists():
        return ""
    ref = head_path.read_text(encoding="utf-8").strip()
    if ref.startswith("ref: "):
        target = REPO_ROOT / ".git" / ref[5:]
        return target.read_text(encoding="utf-8").strip() if target.exists() else ""
    return ref


def _worktree_changes() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.rstrip() for line in result.stdout.splitlines() if line.strip()]


def _lane_row(name: str, state: str, note: str, artifact: str) -> str:
    return f"| `{name}` | `{state}` | {note} | `{artifact}` |"


def _workflow_lane_map(workflow_report: dict | None) -> dict[str, dict]:
    if not workflow_report:
        return {}
    return {
        str(lane.get("name") or ""): lane
        for lane in workflow_report.get("lanes", [])
        if isinstance(lane, dict)
    }


def render() -> str:
    newcomer_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "newcomer-result-proof.json"
    )
    remote_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "remote-platform-truth.json"
    )
    required_checks = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "remote-required-checks.json"
    )
    ghcr_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "standard-image-publish-readiness.json"
    )
    release_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "release" / "release-evidence-attest-readiness.json"
    )
    workflow_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "external-lane-workflows.json"
    )
    alignment_report = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "current-proof-commit-alignment.json"
    )
    compat = _maybe_load_json(REPO_ROOT / "config" / "governance" / "upstream-compat-matrix.json") or {}
    workflow_lanes = _workflow_lane_map(workflow_report)

    head_commit = _current_head()
    worktree_changes = _worktree_changes()
    worktree_dirty = bool(worktree_changes)
    lines = [
        GENERATED_HEADER.rstrip(),
        "# Current State Summary",
        "",
        "这是 runtime-owned 的当前状态页。它不是 tracked docs 的一部分，目的是避免 commit-sensitive current truth 再次卡在 checked-in 文档里。",
        "",
        f"- current HEAD: `{head_commit or 'unknown'}`",
    ]
    if alignment_report:
        lines.append(f"- current-proof alignment: `{alignment_report.get('status', 'unknown')}`")
    lines.append(f"- worktree dirty: `{str(worktree_dirty).lower()}`")
    if worktree_dirty:
        lines.append("- dirty-worktree note: current runtime receipts are commit-aligned, but they do not fully prove the uncommitted workspace state")
    lines.extend(
        [
            "- reading rule: `docs/generated/external-lane-snapshot.md` 只负责解释如何读，当前状态以本文件和底层 runtime reports 为准",
            "",
            "## Repo-side Signals",
            "",
        ]
    )
    if newcomer_report:
        lines.append(f"- newcomer-result-proof artifact: `{newcomer_report.get('status', 'unknown')}`")
        strict_receipt = newcomer_report.get("repo_side_strict_receipt") or {}
        if isinstance(strict_receipt, dict):
            strict_status = str(strict_receipt.get("status") or "unknown")
            lines.append(
                f"- repo-side-strict receipt: `{strict_status}` "
                f"(path=`.runtime-cache/reports/governance/newcomer-result-proof.json`)"
            )
    if remote_report:
        lines.append(f"- remote-platform-integrity artifact: `{remote_report.get('status', 'unknown')}`")
    if required_checks:
        lines.append(
            f"- remote-required-checks artifact: `{required_checks.get('status', 'unknown')}` "
            f"(expected={len(required_checks.get('expected_required_checks', []))}, actual={len(required_checks.get('actual_required_checks', []))})"
        )
    open_source_audit_freshness = _maybe_load_json(
        REPO_ROOT / ".runtime-cache" / "reports" / "governance" / "open-source-audit-freshness.json"
    )
    if open_source_audit_freshness:
        lines.append(
            f"- open-source-audit-freshness artifact: `{open_source_audit_freshness.get('status', 'unknown')}`"
        )
    lines.extend(
        [
            "",
            "## External Lane Summary",
            "",
            "| Lane | Current State | Evidence / Note | Canonical Artifact |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.append(
        _lane_row(
            "remote-platform-integrity",
            str((remote_report or {}).get("status") or "missing"),
            str((remote_report or {}).get("blocker_type") or "ok"),
            ".runtime-cache/reports/governance/remote-platform-truth.json",
        )
    )
    lines.append(
        _lane_row(
            "remote-required-checks",
            str((required_checks or {}).get("status") or "missing"),
            f"expected={len((required_checks or {}).get('expected_required_checks', []))}, actual={len((required_checks or {}).get('actual_required_checks', []))}",
            ".runtime-cache/reports/governance/remote-required-checks.json",
        )
    )
    ghcr_state = str((ghcr_report or {}).get("status") or "missing")
    ghcr_note = str((ghcr_report or {}).get("blocker_type") or "ok")
    ghcr_workflow = workflow_lanes.get("ghcr-standard-image") or {}
    ghcr_workflow_state = str(ghcr_workflow.get("state") or "")
    ghcr_workflow_note = str(ghcr_workflow.get("note") or "")
    ghcr_failure_details = ghcr_workflow.get("failure_details") or {}
    if not isinstance(ghcr_failure_details, dict):
        ghcr_failure_details = {}
    if ghcr_workflow_state in {"in_progress", "queued", "verified"}:
        ghcr_state = ghcr_workflow_state
        ghcr_note = (
            f"{ghcr_workflow_note}; local readiness artifact="
            f"{str((ghcr_report or {}).get('status') or 'missing')}:{str((ghcr_report or {}).get('blocker_type') or 'ok')}"
        )
    elif ghcr_workflow_state == "blocked" and ghcr_failure_details:
        failed_step = str(ghcr_failure_details.get("failed_step_name") or "")
        failure_signature = str(ghcr_failure_details.get("failure_signature") or "")
        if failed_step and failure_signature == "blob-head-403-forbidden":
            local_readiness = (
                f"local readiness artifact={str((ghcr_report or {}).get('status') or 'missing')}:"
                f"{str((ghcr_report or {}).get('blocker_type') or 'ok')}"
            )
            ghcr_note = (
                f"{local_readiness}; latest remote current-head workflow preflight passed; "
                "blocked at `Build and push strict CI standard image`; GHCR blob HEAD returned 403 Forbidden"
            )
        elif failed_step:
            ghcr_note = f"{ghcr_workflow_note}; failed_step={failed_step}"
    lines.append(
        _lane_row(
            "ghcr-standard-image",
            ghcr_state,
            ghcr_note,
            ".runtime-cache/reports/governance/standard-image-publish-readiness.json + .runtime-cache/reports/governance/external-lane-workflows.json",
        )
    )

    release_state = str((release_report or {}).get("status") or "missing")
    release_note = str((release_report or {}).get("blocker_type") or "ok")
    release_workflow = workflow_lanes.get("release-evidence-attestation") or {}
    release_workflow_state = str(release_workflow.get("state") or "")
    release_workflow_note = str(release_workflow.get("note") or "")
    if release_workflow_state == "verified" and release_state == "ready":
        release_state = "verified"
        release_note = f"{release_workflow_note}; readiness artifact=ready"
    elif release_workflow_state in {"in_progress", "queued"}:
        release_state = release_workflow_state
        release_note = f"{release_workflow_note}; readiness artifact={release_state if not release_report else str((release_report or {}).get('status') or 'missing')}"
    lines.append(
        _lane_row(
            "release-evidence-attestation",
            release_state,
            release_note,
            ".runtime-cache/reports/release/release-evidence-attest-readiness.json + .runtime-cache/reports/governance/external-lane-workflows.json",
        )
    )
    if workflow_report:
        for lane in workflow_report.get("lanes", []):
            if not isinstance(lane, dict):
                continue
            lines.append(
                _lane_row(
                    f"workflow:{lane.get('name', 'unknown')}",
                    str(lane.get("state") or "unknown"),
                    str(lane.get("note") or "missing"),
                    ".runtime-cache/reports/governance/external-lane-workflows.json",
                )
            )
    compat_rows = {
        str(row.get("name") or ""): row
        for row in compat.get("matrix", [])
        if isinstance(row, dict)
    }
    for lane_name in ("rsshub-youtube-ingest-chain", "resend-digest-delivery-chain", "strict-ci-compose-image-set"):
        row = compat_rows.get(lane_name, {})
        lines.append(
            _lane_row(
                lane_name,
                str(row.get("verification_status") or "missing"),
                str(row.get("verification_lane") or "unknown"),
                str(row.get("evidence_artifact") or "n/a"),
            )
        )
    lines.extend(
        [
            "",
            "## Public Capability Reminder",
            "",
            "- `ready` 不等于 `verified`。",
            "- remote workflow 指向旧 head 时，只能算 historical，不算 current closure。",
            "- GHCR lane 若显示 `preflight passed` 但后续仍 `blocked`，说明失败已经进入 build/push 或 registry write 边界，而不是卡在 readiness preflight。",
            "- platform capability claim 必须用 live probe 或 current runtime artifact 支撑，不能只凭 tracked docs 声明。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    content = render()
    write_text_artifact(
        OUTPUT_PATH,
        content,
        source_entrypoint="scripts/governance/render_current_state_summary.py",
        verification_scope="current-state-summary",
        source_run_id="current-state-summary",
        source_commit=_current_head(),
        freshness_window_hours=24,
        extra={"report_kind": "current-state-summary"},
    )
    print(OUTPUT_PATH.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
