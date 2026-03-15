#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import artifact_age_hours, load_governance_json, read_runtime_metadata, repo_root


def main() -> int:
    root = repo_root()
    matrix = load_governance_json("upstream-compat-matrix.json")
    errors: list[str] = []
    verified_rows = 0
    skipped_rows = 0

    for item in matrix.get("matrix", []):
        row_name = str(item.get("name") or "<unknown>")
        verification_status = str(item.get("verification_status") or "").strip().lower()
        if verification_status != "verified":
            skipped_rows += 1
            continue
        verified_rows += 1
        freshness_window_hours = item.get("freshness_window_hours")
        if not isinstance(freshness_window_hours, int) or freshness_window_hours <= 0:
            errors.append(f"{row_name}: invalid freshness_window_hours")
            continue
        verification_artifacts = item.get("verification_artifacts", [])
        if not isinstance(verification_artifacts, list) or not verification_artifacts:
            errors.append(f"{row_name}: missing verification_artifacts")
            continue
        for rel in verification_artifacts:
            artifact = root / str(rel)
            if not artifact.is_file():
                errors.append(f"{row_name}: missing verification artifact {rel}")
                continue
            metadata = read_runtime_metadata(artifact)
            if metadata is None:
                errors.append(f"{row_name}: verification artifact missing runtime metadata: {rel}")
                continue
            if not str(metadata.get("source_commit") or "").strip():
                errors.append(f"{row_name}: verification artifact metadata missing source_commit: {rel}")
            age_hours = artifact_age_hours(artifact, metadata)
            if age_hours > freshness_window_hours:
                errors.append(
                    f"{row_name}: verification artifact stale {rel} age={age_hours:.2f}h window={freshness_window_hours}h"
                )

    if errors:
        print("[upstream-compat-freshness] FAIL")
        for item in errors[:20]:
            print(f"  - {item}")
        return 1

    print(
        f"[upstream-compat-freshness] PASS (verified_rows={verified_rows} skipped_non_verified={skipped_rows})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
