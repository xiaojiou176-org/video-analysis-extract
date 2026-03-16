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

    for pattern in payload.get("forbidden_tracked_globs", []):
        matches = sorted(
            path for path in tracked if fnmatch(path, str(pattern)) and (root / path).exists()
        )
        if matches:
            errors.append(f"forbidden tracked public artifacts for `{pattern}`: {', '.join(matches[:5])}")

    for rel in payload.get("required_public_samples", []):
        if not (root / str(rel)).is_file():
            errors.append(f"missing required sanitized public sample: {rel}")

    if errors:
        print("[public-surface-policy] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[public-surface-policy] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
