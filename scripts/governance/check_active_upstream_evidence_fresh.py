#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import artifact_age_hours, load_governance_json, read_runtime_metadata, repo_root

RISK_CLASS_TO_FRESHNESS = {
    "critical": 24,
    "high": 72,
    "medium": 168,
    "low": 336,
}


def main() -> int:
    root = repo_root()
    upstreams = load_governance_json("active-upstreams.json")
    errors: list[str] = []

    for entry in upstreams.get("entries", []):
        name = str(entry.get("name") or "<unknown>")
        risk_class = str(entry.get("risk_class") or "medium")
        freshness_window_hours = RISK_CLASS_TO_FRESHNESS.get(risk_class, 168)
        artifact = root / str(entry.get("evidence_artifact") or "")
        if not artifact.is_file():
            errors.append(f"{name}: missing evidence_artifact {entry.get('evidence_artifact')}")
            continue
        metadata = read_runtime_metadata(artifact)
        if metadata is None:
            errors.append(f"{name}: evidence_artifact missing runtime metadata")
            continue
        age_hours = artifact_age_hours(artifact, metadata)
        if age_hours > freshness_window_hours:
            errors.append(
                f"{name}: evidence_artifact stale age={age_hours:.2f}h window={freshness_window_hours}h"
            )

    if errors:
        print("[active-upstream-evidence-fresh] FAIL")
        for item in errors[:20]:
            print(f"  - {item}")
        return 1

    print("[active-upstream-evidence-fresh] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
