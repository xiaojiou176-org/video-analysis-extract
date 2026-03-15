#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import load_governance_json, top_level_entries


def main() -> int:
    payload = load_governance_json("root-allowlist.json")
    tracked_allowed = {
        str(item["path"])
        for item in payload.get("tracked_root_allowlist", [])
        if isinstance(item, dict) and item.get("path")
    }
    tolerated_allowed = {
        str(item["path"])
        for item in payload.get("local_private_root_tolerations", [])
        if isinstance(item, dict) and item.get("path")
    }
    current = {path.name for path in top_level_entries()}
    unknown = sorted(current - tracked_allowed - tolerated_allowed)
    if unknown:
        print("[root-zero-unknowns] FAIL")
        print("  - unknown top-level entries present: " + ", ".join(unknown))
        return 1

    print("[root-zero-unknowns] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
