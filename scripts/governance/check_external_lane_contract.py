#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_governance_json


def main() -> int:
    payload = load_governance_json("external-lane-contract.json")
    lanes = payload.get("lanes", [])
    errors: list[str] = []
    if not isinstance(lanes, list) or not lanes:
        errors.append("lanes must be a non-empty list")
    else:
        for lane in lanes:
            if not isinstance(lane, dict):
                errors.append("lane entry must be an object")
                continue
            for field in ("name", "canonical_artifact", "verification_scope", "allowed_statuses", "blocked_types"):
                value = lane.get(field)
                if value in (None, "", []):
                    errors.append(f"lane `{lane.get('name', '<unknown>')}` missing field `{field}`")
            artifact = str(lane.get("canonical_artifact") or "")
            if artifact and not artifact.startswith(".runtime-cache/"):
                errors.append(f"lane `{lane.get('name', '<unknown>')}` canonical_artifact must live under .runtime-cache/")

    if errors:
        print("[external-lane-contract] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[external-lane-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
