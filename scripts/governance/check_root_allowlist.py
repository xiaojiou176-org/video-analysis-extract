#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

sys.dont_write_bytecode = True

from common import git_is_tracked, git_tracked_paths, load_governance_json, top_level_entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tracked public root entries and tolerated local-private root items.")
    parser.add_argument(
        "--strict-local-private",
        action="store_true",
        help="Fail when any local-private tolerated entry is tracked by Git.",
    )
    args = parser.parse_args()

    payload = load_governance_json("root-allowlist.json")
    tracked_entries = payload.get("tracked_root_allowlist", [])
    tolerated_entries = payload.get("local_private_root_tolerations", [])
    tracked_required_fields = {"path", "kind", "reason", "owner", "mutable"}
    nested_hint_required_fields = {
        "path",
        "boundary",
        "current_tracking_state",
        "target_tracking_state",
        "reason",
    }
    tolerated_required_fields = {"path", "kind", "reason", "owner", "must_be_untracked"}
    tracked_allowed = set()
    tolerated_allowed = set()
    nested_hint_notes: list[str] = []
    errors: list[str] = []
    tracked_paths = git_tracked_paths()

    for item in tracked_entries:
        if not tracked_required_fields.issubset(item):
            missing = sorted(tracked_required_fields - set(item))
            errors.append(
                f"tracked root allowlist entry missing fields for {item.get('path', '<unknown>')}: "
                + ", ".join(missing)
            )
            continue
        tracked_allowed.add(str(item["path"]))
        parent_path = str(item["path"]).rstrip("/")
        nested_hints = item.get("nested_boundary_hints", [])
        if nested_hints and not isinstance(nested_hints, list):
            errors.append(f"tracked root allowlist entry `{parent_path}` has non-list nested_boundary_hints")
            continue
        for hint in nested_hints:
            if not isinstance(hint, dict):
                errors.append(f"tracked root allowlist entry `{parent_path}` has invalid nested boundary hint")
                continue
            if not nested_hint_required_fields.issubset(hint):
                missing = sorted(nested_hint_required_fields - set(hint))
                errors.append(
                    f"nested boundary hint missing fields for {hint.get('path', '<unknown>')}: "
                    + ", ".join(missing)
                )
                continue
            hint_path = str(hint["path"]).rstrip("/")
            if not hint_path.startswith(parent_path + "/"):
                errors.append(
                    f"nested boundary hint `{hint_path}` must stay under declared root entry `{parent_path}`"
                )
                continue
            nested_hint_notes.append(
                f"{hint_path} ({hint['boundary']} -> {hint['target_tracking_state']})"
            )

    for item in tolerated_entries:
        if not tolerated_required_fields.issubset(item):
            missing = sorted(tolerated_required_fields - set(item))
            errors.append(
                f"local-private root tolerance missing fields for {item.get('path', '<unknown>')}: "
                + ", ".join(missing)
            )
            continue
        tolerated_allowed.add(str(item["path"]))
        if args.strict_local_private and bool(item.get("must_be_untracked")) and git_is_tracked(
            str(item["path"]), tracked_paths=tracked_paths
        ):
            errors.append(f"local-private tolerated root entry must stay untracked: {item['path']}")

    current = {path.name for path in top_level_entries()}
    allowed = tracked_allowed | tolerated_allowed
    unknown = sorted(current - allowed)
    if unknown:
        errors.append("unknown top-level entries: " + ", ".join(unknown))

    missing_declared = sorted(name for name in tracked_allowed if name not in current and not name.startswith(".git"))
    if missing_declared:
        print(
            "[root-allowlist] note: declared public entries currently absent="
            + ", ".join(missing_declared)
        )

    tolerated_present = sorted(name for name in tolerated_allowed if name in current)
    if tolerated_present:
        print(
            "[root-allowlist] note: local-private tolerated entries present="
            + ", ".join(tolerated_present)
        )
    if nested_hint_notes:
        print(
            "[root-allowlist] note: nested boundary migration targets="
            + ", ".join(sorted(nested_hint_notes))
        )

    if errors:
        print("[root-allowlist] FAIL")
        for item in errors:
            print(f"  - {item}")
        print("  - remediation: run `./bin/workspace-hygiene --apply` to clear repo-root/source-tree runtime residue before rerunning the gate")
        return 1

    print(
        f"[root-allowlist] PASS (public={len(tracked_allowed)} tolerated={len(tolerated_allowed)} current={len(current)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
