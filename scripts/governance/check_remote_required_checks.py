#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import current_git_commit, read_runtime_metadata, write_json_artifact


def _load_required_checks(path: Path) -> list[str]:
    pattern = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*required\s*\|$")
    checks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if match:
            checks.append(match.group("name"))
    return checks


def _actual_contexts(branch_protection: dict[str, Any] | None) -> list[str]:
    if not isinstance(branch_protection, dict):
        return []
    required = branch_protection.get("required_status_checks")
    if not isinstance(required, dict):
        return []
    contexts = required.get("contexts")
    if isinstance(contexts, list):
        return [str(item) for item in contexts if str(item).strip()]
    checks = required.get("checks")
    if isinstance(checks, list):
        results: list[str] = []
        for item in checks:
            if isinstance(item, dict) and str(item.get("context") or "").strip():
                results.append(str(item["context"]))
        return results
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate remote required checks against the generated repo-side contract.")
    parser.add_argument(
        "--probe-report",
        default=".runtime-cache/reports/governance/remote-platform-truth.json",
        help="Remote platform probe report path.",
    )
    parser.add_argument(
        "--required-checks",
        default="docs/generated/required-checks.md",
        help="Generated required checks reference.",
    )
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/remote-required-checks.json",
        help="Validation report output path.",
    )
    args = parser.parse_args()

    probe_path = ROOT / args.probe_report
    required_path = ROOT / args.required_checks
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    expected = _load_required_checks(required_path)
    actual = sorted(set(_actual_contexts(probe.get("branch_protection"))))
    expected_set = set(expected)
    actual_set = set(actual)
    missing = sorted(expected_set - actual_set)
    extra = sorted(actual_set - expected_set)
    visibility = str((probe.get("repo_view") or {}).get("visibility") or "")

    status = "pass"
    blocker_type = ""
    errors: list[str] = []
    if probe.get("status") != "pass":
        status = "blocked"
        blocker_type = str(probe.get("blocker_type") or "repo-readability")
        errors.append("remote-platform probe did not reach a pass state")
    if visibility != "PUBLIC":
        status = "blocked"
        blocker_type = blocker_type or "branch-protection-platform-boundary"
        errors.append(f"remote repo visibility must be PUBLIC, got {visibility or '<unknown>'}")
    if not actual:
        status = "blocked"
        blocker_type = blocker_type or "branch-protection-platform-boundary"
        errors.append("branch protection required checks are unreadable or empty")
    if missing or extra:
        status = "blocked"
        blocker_type = "required-check-integrity-mismatch"
        if missing:
            errors.append("missing required checks: " + ", ".join(missing))
        if extra:
            errors.append("unexpected extra checks: " + ", ".join(extra))

    probe_metadata = read_runtime_metadata(probe_path)
    report = {
        "version": 1,
        "status": status,
        "blocker_type": blocker_type,
        "repo": probe.get("repo", ""),
        "actor": probe.get("actor", ""),
        "repo_visibility": visibility,
        "source_commit": current_git_commit(),
        "expected_required_checks": expected,
        "actual_required_checks": actual,
        "missing_required_checks": missing,
        "extra_required_checks": extra,
        "errors": errors,
        "probe_report": str(Path(args.probe_report).as_posix()),
        "probe_report_created_at": (probe_metadata or {}).get("created_at", ""),
    }
    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/governance/check_remote_required_checks.py",
        verification_scope="remote-required-checks",
        source_run_id="remote-required-checks",
        freshness_window_hours=24,
        extra={"report_kind": "remote-required-checks"},
    )

    if status != "pass":
        print("[remote-required-checks] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[remote-required-checks] PASS ({len(expected)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
