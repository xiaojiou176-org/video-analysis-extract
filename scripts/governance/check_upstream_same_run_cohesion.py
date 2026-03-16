#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, read_runtime_metadata, repo_root, write_json_artifact

SHARED_GOVERNANCE_ARTIFACTS = {
    ".runtime-cache/reports/governance/upstream-compat-report.json",
}


def main() -> int:
    root = repo_root()
    matrix = load_governance_json("upstream-compat-matrix.json")
    errors: list[str] = []
    row_reports: list[dict[str, object]] = []
    verified_blocker_rows = 0
    pending_blocker_rows = 0

    for item in matrix.get("matrix", []):
        row_name = str(item.get("name") or "<unknown>")
        blocking_level = str(item.get("blocking_level") or "").strip().lower()
        verification_status = str(item.get("verification_status") or "").strip().lower()
        if blocking_level != "blocker":
            continue

        if verification_status == "verified":
            verified_blocker_rows += 1
        else:
            pending_blocker_rows += 1

        last_verified_run_id = str(item.get("last_verified_run_id") or "").strip()
        verification_artifacts = [str(rel) for rel in item.get("verification_artifacts", [])]
        row_specific_artifacts = [
            rel for rel in verification_artifacts if rel not in SHARED_GOVERNANCE_ARTIFACTS
        ]
        missing_artifacts: list[str] = []
        missing_metadata: list[str] = []
        missing_source_commit: list[str] = []
        mismatched_run_ids: list[str] = []
        observed_run_ids: dict[str, str] = {}

        for rel in verification_artifacts:
            artifact = root / rel
            if not artifact.is_file():
                missing_artifacts.append(rel)
                continue
            metadata = read_runtime_metadata(artifact)
            if metadata is None:
                missing_metadata.append(rel)
                continue
            source_run_id = str(metadata.get("source_run_id") or "").strip()
            observed_run_ids[rel] = source_run_id
            if not str(metadata.get("source_commit") or "").strip():
                missing_source_commit.append(rel)
            if (
                verification_status == "verified"
                and rel in row_specific_artifacts
                and source_run_id != last_verified_run_id
            ):
                mismatched_run_ids.append(f"{rel} -> {source_run_id or '<missing>'}")

        row_errors: list[str] = []
        if verification_status == "verified":
            if not last_verified_run_id:
                row_errors.append("verified blocker row missing last_verified_run_id")
            if not row_specific_artifacts:
                row_errors.append("verified blocker row must declare at least one row-specific artifact")
            if missing_artifacts:
                row_errors.append("missing artifacts: " + ", ".join(missing_artifacts))
            if missing_metadata:
                row_errors.append("artifacts missing runtime metadata: " + ", ".join(missing_metadata))
            if missing_source_commit:
                row_errors.append("artifacts missing source_commit: " + ", ".join(missing_source_commit))
            if mismatched_run_ids:
                row_errors.append(
                    "row-specific artifacts do not match last_verified_run_id: "
                    + ", ".join(mismatched_run_ids)
                )

        if row_errors:
            errors.extend(f"{row_name}: {msg}" for msg in row_errors)

        row_reports.append(
            {
                "name": row_name,
                "blocking_level": blocking_level,
                "verification_status": verification_status,
                "verification_lane": str(item.get("verification_lane") or ""),
                "last_verified_run_id": last_verified_run_id,
                "verification_artifacts": verification_artifacts,
                "row_specific_artifacts": row_specific_artifacts,
                "missing_artifacts": missing_artifacts,
                "missing_metadata": missing_metadata,
                "missing_source_commit": missing_source_commit,
                "observed_run_ids": observed_run_ids,
                "status": "fail" if row_errors else "pass",
                "notes": row_errors
                if row_errors
                else (
                    ["pending blocker row is not yet required to prove same-run cohesion"]
                    if verification_status != "verified"
                    else ["verified blocker row has a coherent same-run bundle"]
                ),
            }
        )

    report_path = root / ".runtime-cache" / "reports" / "governance" / "upstream-same-run-cohesion.json"
    write_json_artifact(
        report_path,
        {
            "version": 1,
            "status": "fail" if errors else "pass",
            "verified_blocker_rows": verified_blocker_rows,
            "pending_blocker_rows": pending_blocker_rows,
            "rows": row_reports,
        },
        source_entrypoint="scripts/governance/check_upstream_same_run_cohesion.py",
        verification_scope="upstream-same-run-cohesion",
        source_run_id="governance-upstream-same-run-cohesion",
        freshness_window_hours=24,
        extra={"report_kind": "upstream-same-run-cohesion"},
    )

    if errors:
        print("[upstream-same-run-cohesion] FAIL")
        for item in errors[:20]:
            print(f"  - {item}")
        return 1

    print(
        "[upstream-same-run-cohesion] PASS "
        f"(verified_blocker_rows={verified_blocker_rows} pending_blocker_rows={pending_blocker_rows})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
