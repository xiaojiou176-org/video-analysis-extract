#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import current_git_commit, read_runtime_metadata, repo_root, write_json_artifact


def _check_artifact(
    root: Path,
    current_head: str,
    rel_path: str,
    errors: list[str],
) -> dict[str, object]:
    path = root / rel_path
    result: dict[str, object] = {
        "path": rel_path,
        "artifact_exists": path.is_file(),
        "meta_exists": False,
        "source_commit": "",
        "status": "pass",
    }
    if not path.is_file():
        errors.append(f"missing artifact: {rel_path}")
        result["status"] = "fail"
        return result

    metadata = read_runtime_metadata(path)
    if metadata is None:
        errors.append(f"missing runtime metadata: {rel_path}.meta.json")
        result["status"] = "fail"
        return result

    result["meta_exists"] = True
    source_commit = str(metadata.get("source_commit") or "")
    result["source_commit"] = source_commit
    if source_commit != current_head:
        errors.append(
            f"{rel_path}.meta.json source_commit mismatch: current_head={current_head} source_commit={source_commit or '<missing>'}"
        )
        result["status"] = "fail"
    return result


def main() -> int:
    root = repo_root()
    current_head = current_git_commit()
    targets = [
        ".runtime-cache/reports/open-source-audit/gitleaks-history.json",
        ".runtime-cache/reports/open-source-audit/gitleaks-working-tree.json",
    ]
    errors: list[str] = []
    checks = [_check_artifact(root, current_head, rel_path, errors) for rel_path in targets]

    report = {
        "version": 1,
        "status": "fail" if errors else "pass",
        "current_head": current_head,
        "checks": checks,
        "errors": errors,
    }
    write_json_artifact(
        root / ".runtime-cache/reports/governance/open-source-audit-freshness.json",
        report,
        source_entrypoint="scripts/governance/check_open_source_audit_freshness.py",
        verification_scope="open-source-audit-freshness",
        source_run_id="governance-open-source-audit-freshness",
        freshness_window_hours=24,
        extra={"report_kind": "open-source-audit-freshness"},
    )

    if errors:
        print("[open-source-audit-freshness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[open-source-audit-freshness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
