#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import current_git_commit, read_runtime_metadata, repo_root


def main() -> int:
    root = repo_root()
    path = root / ".runtime-cache" / "reports" / "governance" / "newcomer-result-proof.json"
    errors: list[str] = []
    if not path.is_file():
        print("[newcomer-result-proof-check] FAIL")
        print("  - newcomer result proof report missing")
        return 1

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print("[newcomer-result-proof-check] FAIL")
        print(f"  - invalid JSON: {exc}")
        return 1

    metadata = read_runtime_metadata(path)
    if metadata is None:
        errors.append("report missing runtime metadata")
    else:
        if str(metadata.get("source_commit") or "") != current_git_commit():
            errors.append("report runtime metadata source_commit does not match current HEAD")

    if str(payload.get("source_commit") or "") != current_git_commit():
        errors.append("report source_commit does not match current HEAD")

    newcomer = payload.get("newcomer_preflight") or {}
    if newcomer.get("status") != "pass":
        errors.append("newcomer preflight must be pass for the current report")
    if newcomer.get("resolved_env_exists") is not True:
        errors.append("newcomer preflight must point to an existing resolved env receipt")

    governance = payload.get("governance_audit_receipt") or {}
    if governance.get("status") not in {"pass", "in_progress"}:
        errors.append("governance audit receipt must be `pass` or `in_progress` in newcomer result proof")

    worktree_state = payload.get("worktree_state") or {}
    if not isinstance(worktree_state.get("dirty"), bool):
        errors.append("worktree_state.dirty must be present and boolean")

    strict_receipt = payload.get("repo_side_strict_receipt") or {}
    allowed = {"pass", "missing_current_receipt"}
    if strict_receipt.get("status") not in allowed:
        errors.append("repo_side_strict_receipt must be `pass` or `missing_current_receipt`")
    overall_status = str(payload.get("status") or "")
    worktree_dirty = bool(worktree_state.get("dirty"))
    current_workspace_verdict = payload.get("current_workspace_verdict") or {}
    if str(current_workspace_verdict.get("status") or "") != overall_status:
        errors.append("current_workspace_verdict.status must mirror top-level report status")

    blocking_conditions = current_workspace_verdict.get("blocking_conditions")
    if not isinstance(blocking_conditions, list) or not all(isinstance(item, str) for item in blocking_conditions):
        errors.append("current_workspace_verdict.blocking_conditions must be a string list")
        blocking_conditions = []

    current_proof_alignment = payload.get("current_proof_alignment") or {}
    current_proof_exists = current_proof_alignment.get("exists") is True
    current_proof_aligned = current_proof_alignment.get("current_commit_aligned") is True

    if worktree_dirty:
        if overall_status != "partial":
            errors.append("dirty worktree must force newcomer result proof to `partial`")
        if "dirty_worktree" not in blocking_conditions:
            errors.append("dirty worktree must be listed in current_workspace_verdict.blocking_conditions")

    if not current_proof_exists:
        if overall_status == "pass":
            errors.append("missing current_proof_alignment artifact must block `pass`")
        if "current_proof_alignment_missing" not in blocking_conditions:
            errors.append("missing current proof alignment must be listed as a blocker")
    elif not current_proof_aligned:
        if overall_status == "pass":
            errors.append("stale current_proof_alignment artifact must block `pass`")
        if "current_proof_alignment_stale" not in blocking_conditions:
            errors.append("stale current proof alignment must be listed as a blocker")

    if strict_receipt.get("status") != "pass" and "repo_side_strict_missing_current_receipt" not in blocking_conditions:
        errors.append("missing current strict receipt must be listed as a blocker")

    if newcomer.get("status") == "pass" and governance.get("status") == "pass" and strict_receipt.get("status") == "pass":
        expected_status = "partial" if worktree_dirty else ("pass" if current_proof_aligned else "partial")
        if overall_status != expected_status:
            errors.append(
                f"newcomer result proof must be `{expected_status}` when newcomer/governance/strict receipts are pass"
            )
    elif newcomer.get("status") == "pass" and governance.get("status") in {"pass", "in_progress"}:
        if overall_status not in {"partial", "missing"}:
            errors.append("newcomer result proof must be `partial` or `missing` when only partial repo-side receipts exist")

    eval_regression = payload.get("eval_regression") or {}
    if not eval_regression:
        errors.append("eval regression summary missing")

    if errors:
        print("[newcomer-result-proof-check] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[newcomer-result-proof-check] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
