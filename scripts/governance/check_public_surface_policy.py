#!/usr/bin/env python3
from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import Path

sys.dont_write_bytecode = True

from common import git_tracked_paths, load_governance_json, repo_root


def main() -> int:
    payload = load_governance_json("public-surface-policy.json")
    tracked = git_tracked_paths()
    root = repo_root()
    errors: list[str] = []
    allowed_paths = {str(item).strip() for item in payload.get("allowed_tracked_paths", []) if str(item).strip()}

    for pattern in payload.get("forbidden_tracked_globs", []):
        matches = sorted(
            path
            for path in tracked
            if fnmatch(path, str(pattern)) and (root / path).exists() and path not in allowed_paths
        )
        if matches:
            errors.append(f"forbidden tracked public artifacts for `{pattern}`: {', '.join(matches[:5])}")

    for rel in payload.get("required_public_samples", []):
        if not (root / str(rel)).is_file():
            errors.append(f"missing required sanitized public sample: {rel}")
        elif str(rel) not in tracked:
            errors.append(f"required sanitized public sample must be tracked: {rel}")

    for rel in allowed_paths:
        path = root / rel
        if not path.is_file():
            errors.append(f"allowed tracked public path must exist as a file: {rel}")
        elif rel not in tracked:
            errors.append(f"allowed tracked public path must be git-tracked: {rel}")

    for rel in payload.get("required_public_samples", []):
        rel_text = str(rel)
        matching_forbidden = [
            str(pattern)
            for pattern in payload.get("forbidden_tracked_globs", [])
            if fnmatch(rel_text, str(pattern))
        ]
        if matching_forbidden and rel_text not in allowed_paths:
            errors.append(
                "required public sample matches forbidden tracked glob without explicit allowlist: "
                f"{rel_text} -> {', '.join(matching_forbidden)}"
            )

    if errors:
        print("[public-surface-policy] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[public-surface-policy] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
