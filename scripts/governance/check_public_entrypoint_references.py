#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def main() -> int:
    root = repo_root()
    config = load_governance_json("public-entrypoints.json")
    errors: list[str] = []

    for entry in config.get("required_public_entrypoints", []):
        path = root / str(entry)
        if not path.is_file():
            errors.append(f"public-entrypoints: missing required public entrypoint `{entry}`")

    legacy_paths = [str(item) for item in config.get("legacy_public_paths", [])]
    for surface in config.get("surfaces", []):
        path = root / str(surface)
        if not path.is_file():
            errors.append(f"public-entrypoints: declared surface missing `{surface}`")
            continue
        content = path.read_text(encoding="utf-8")
        for legacy in legacy_paths:
            if legacy in content:
                errors.append(
                    f"public-entrypoints: legacy public path `{legacy}` still referenced from `{surface}`"
                )

    if errors:
        print("[public-entrypoint-references] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[public-entrypoint-references] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
