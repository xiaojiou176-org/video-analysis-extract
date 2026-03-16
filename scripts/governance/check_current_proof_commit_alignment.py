#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

sys.dont_write_bytecode = True

from common import current_git_commit, load_governance_json, read_runtime_metadata, repo_root, write_json_artifact


def main() -> int:
    payload = load_governance_json("current-proof-contract.json")
    artifacts = payload.get("artifacts", [])
    root = repo_root()
    head_commit = current_git_commit()
    errors: list[str] = []
    rows: list[dict[str, object]] = []

    if not isinstance(artifacts, list) or not artifacts:
        print("[current-proof-commit-alignment] FAIL")
        print("  - contract must declare a non-empty artifacts list")
        return 1

    for item in artifacts:
        if not isinstance(item, dict):
            errors.append("artifact entry must be an object")
            continue
        name = str(item.get("name") or "<unknown>")
        rel = str(item.get("artifact") or "").strip()
        required = bool(item.get("required"))
        reason = str(item.get("reason") or "").strip()
        if not rel:
            errors.append(f"{name}: missing artifact path")
            continue

        path = root / rel
        row: dict[str, object] = {
            "name": name,
            "artifact": rel,
            "required": required,
            "reason": reason,
            "status": "missing",
            "source_commit": "",
        }
        if not path.is_file():
            if required:
                errors.append(f"{name}: required artifact missing: {rel}")
                row["status"] = "missing_required"
            rows.append(row)
            continue

        metadata = read_runtime_metadata(path)
        if metadata is None:
            errors.append(f"{name}: runtime metadata missing for {rel}")
            row["status"] = "missing_metadata"
            rows.append(row)
            continue

        source_commit = str(metadata.get("source_commit") or "").strip()
        row["source_commit"] = source_commit
        row["created_at"] = str(metadata.get("created_at") or "")
        if not source_commit:
            errors.append(f"{name}: metadata source_commit missing for {rel}")
            row["status"] = "missing_source_commit"
        elif source_commit != head_commit:
            errors.append(
                f"{name}: artifact source_commit {source_commit} does not match current HEAD {head_commit} for {rel}"
            )
            row["status"] = "stale_commit"
        else:
            row["status"] = "aligned"
            if name == "external-lane-workflows":
                try:
                    workflow_report = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    errors.append(f"{name}: unable to parse workflow report for nested current-proof checks: {exc}")
                else:
                    nested_errors: list[str] = []
                    for lane in workflow_report.get("lanes", []):
                        if not isinstance(lane, dict):
                            continue
                        lane_name = str(lane.get("name") or "<unknown>")
                        lane_state = str(lane.get("state") or "")
                        latest_run = lane.get("latest_run") or {}
                        latest_head = str(latest_run.get("headSha") or "").strip()
                        matches_current_head = lane.get("latest_run_matches_current_head")
                        if lane_state == "verified":
                            if not latest_head:
                                nested_errors.append(
                                    f"{lane_name}: verified lane is missing latest_run.headSha"
                                )
                            elif latest_head != head_commit:
                                nested_errors.append(
                                    f"{lane_name}: verified lane headSha {latest_head} does not match current HEAD {head_commit}"
                                )
                            if matches_current_head is not True:
                                nested_errors.append(
                                    f"{lane_name}: verified lane must set latest_run_matches_current_head=true"
                                )
                        if latest_head and latest_head != head_commit and lane_state in {"verified", "blocked", "queued", "in_progress"}:
                            nested_errors.append(
                                f"{lane_name}: non-current remote run must not be reported as `{lane_state}`; use historical semantics instead"
                            )
                    if nested_errors:
                        errors.extend(f"{name}: {item}" for item in nested_errors)
                    row["workflow_lane_states"] = [
                        {
                            "name": str(lane.get("name") or "<unknown>"),
                            "state": str(lane.get("state") or ""),
                            "latest_run_head": str((lane.get("latest_run") or {}).get("headSha") or ""),
                            "latest_run_matches_current_head": lane.get("latest_run_matches_current_head"),
                        }
                        for lane in workflow_report.get("lanes", [])
                        if isinstance(lane, dict)
                    ]
        rows.append(row)

    report = {
        "version": 1,
        "status": "pass" if not errors else "fail",
        "current_head": head_commit,
        "artifacts": rows,
        "errors": errors,
    }
    write_json_artifact(
        root / ".runtime-cache" / "reports" / "governance" / "current-proof-commit-alignment.json",
        report,
        source_entrypoint="scripts/governance/check_current_proof_commit_alignment.py",
        verification_scope="current-proof-commit-alignment",
        source_run_id="governance-current-proof-commit-alignment",
        freshness_window_hours=24,
        extra={"report_kind": "current-proof-commit-alignment"},
    )

    if errors:
        print("[current-proof-commit-alignment] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[current-proof-commit-alignment] PASS ({len(rows)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
