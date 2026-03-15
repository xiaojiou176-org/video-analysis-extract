#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import find_forbidden_runtime_entries, load_governance_json, repo_root, top_level_entries


def _snapshot() -> list[str]:
    return [path.name for path in top_level_entries()]


def _hygiene_violations() -> list[str]:
    payload = load_governance_json("runtime-outputs.json")
    violations: list[str] = []
    for item in payload.get("root_forbidden", []):
        candidate = repo_root() / str(item)
        if candidate.exists():
            violations.append(str(item))
    violations.extend(
        find_forbidden_runtime_entries([str(item) for item in payload.get("nested_forbidden", [])])
    )
    return sorted(dict.fromkeys(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture or compare root-level top directory state.")
    parser.add_argument("--write-snapshot", type=Path, help="Write the current root snapshot JSON to this path.")
    parser.add_argument("--compare-snapshot", type=Path, help="Compare current root state against a saved snapshot.")
    args = parser.parse_args()

    if bool(args.write_snapshot) == bool(args.compare_snapshot):
        raise SystemExit("must pass exactly one of --write-snapshot or --compare-snapshot")

    if args.write_snapshot:
        target = args.write_snapshot
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(_snapshot(), indent=2) + "\n", encoding="utf-8")
        try:
            rendered_target = target.relative_to(repo_root()).as_posix()
        except ValueError:
            rendered_target = str(target)
        print(f"[root-dirtiness] wrote snapshot to {rendered_target}")
        return 0

    saved = json.loads(args.compare_snapshot.read_text(encoding="utf-8"))
    before = set(saved)
    after = set(_snapshot())
    new_entries = sorted(after - before)
    hygiene_violations = _hygiene_violations()
    if new_entries:
        print("[root-dirtiness] FAIL")
        print("  - new top-level entries after task: " + ", ".join(new_entries))
        return 1
    if hygiene_violations:
        print("[root-dirtiness] FAIL")
        print("  - forbidden hygiene residue present: " + ", ".join(hygiene_violations))
        return 1
    print("[root-dirtiness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
