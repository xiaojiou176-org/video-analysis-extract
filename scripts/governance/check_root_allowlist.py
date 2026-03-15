#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import load_governance_json, top_level_entries


def main() -> int:
    payload = load_governance_json("root-allowlist.json")
    entries = payload.get("entries", [])
    required_fields = {"path", "kind", "reason", "owner", "mutable"}
    allowed = set()
    errors: list[str] = []

    for item in entries:
        if not required_fields.issubset(item):
            missing = sorted(required_fields - set(item))
            errors.append(
                f"root allowlist entry missing fields for {item.get('path', '<unknown>')}: "
                + ", ".join(missing)
            )
            continue
        allowed.add(str(item["path"]))

    current = {path.name for path in top_level_entries()}
    unknown = sorted(current - allowed)
    if unknown:
        errors.append("unknown top-level entries: " + ", ".join(unknown))

    missing_declared = sorted(name for name in allowed if name not in current and not name.startswith(".git"))
    if missing_declared:
        print(
            "[root-allowlist] note: declared but currently absent entries="
            + ", ".join(missing_declared)
        )

    if errors:
        print("[root-allowlist] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[root-allowlist] PASS ({len(current)} entries declared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
