#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def main() -> int:
    root = repo_root()
    registry = load_governance_json("upstream-registry.json")
    active = load_governance_json("active-upstreams.json")
    errors: list[str] = []

    active_vendor_names = {
        str(entry["name"])
        for entry in active.get("entries", [])
        if str(entry.get("kind")) in {"vendor", "fork", "patch"}
    }

    vendor_root = root / "vendor"
    if vendor_root.exists():
        lock_files = sorted(vendor_root.rglob("UPSTREAM.lock"))
        if not lock_files:
            errors.append("vendor directory exists but no UPSTREAM.lock files were found")
        for lock_file in lock_files:
            vendor_dir = lock_file.parent
            for required in ("README.md", "PATCHES.md"):
                if not (vendor_dir / required).is_file():
                    errors.append(f"{vendor_dir.relative_to(root).as_posix()}: missing required vendor file {required}")

    registry_active = {str(item) for item in registry.get("active", [])}
    for name in sorted(active_vendor_names):
        if name not in registry_active:
            errors.append(f"active vendor/fork/patch `{name}` missing from upstream-registry active list")

    if errors:
        print("[vendor-registry-integrity] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[vendor-registry-integrity] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
