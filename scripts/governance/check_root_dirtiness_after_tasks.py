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


def _tolerated_local_private_entries() -> set[str]:
    payload = load_governance_json("root-allowlist.json")
    return {
        str(item["path"])
        for item in payload.get("local_private_root_tolerations", [])
        if isinstance(item, dict) and item.get("path")
    }


def _nested_boundary_notes() -> list[str]:
    payload = load_governance_json("root-allowlist.json")
    notes: list[str] = []
    for item in payload.get("tracked_root_allowlist", []):
        if not isinstance(item, dict):
            continue
        for hint in item.get("nested_boundary_hints", []):
            if not isinstance(hint, dict):
                continue
            path = str(hint.get("path") or "").strip()
            if not path:
                continue
            candidate = repo_root() / path
            if candidate.exists():
                notes.append(
                    f"{path} ({hint.get('current_tracking_state', 'unknown')} -> {hint.get('target_tracking_state', 'unknown')})"
                )
    return sorted(dict.fromkeys(notes))


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


def _runtime_root_unknown_children() -> list[str]:
    payload = load_governance_json("runtime-outputs.json")
    runtime_root = repo_root() / str(payload["runtime_root"])
    allowed_subdirs = set(payload.get("subdirectories", {}).keys())
    if not runtime_root.exists():
        return []
    return sorted(
        str(Path(".runtime-cache") / child.name)
        for child in runtime_root.iterdir()
        if child.name not in allowed_subdirs
    )


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
    tolerated_entries = _tolerated_local_private_entries()
    new_entries = sorted((after - before) - tolerated_entries)
    hygiene_violations = _hygiene_violations()
    runtime_root_unknown_children = _runtime_root_unknown_children()
    nested_boundary_notes = _nested_boundary_notes()
    if new_entries:
        print("[root-dirtiness] FAIL")
        print("  - new top-level entries after task: " + ", ".join(new_entries))
        return 1
    if hygiene_violations:
        print("[root-dirtiness] FAIL")
        print("  - forbidden hygiene residue present: " + ", ".join(hygiene_violations))
        return 1
    if runtime_root_unknown_children:
        print("[root-dirtiness] FAIL")
        print(
            "  - runtime root contains undeclared direct children: "
            + ", ".join(runtime_root_unknown_children)
        )
        return 1
    if nested_boundary_notes:
        print(
            "[root-dirtiness] note: nested boundary migration targets present="
            + ", ".join(nested_boundary_notes)
        )
    print("[root-dirtiness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
