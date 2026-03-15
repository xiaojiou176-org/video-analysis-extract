#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def main() -> int:
    config = load_governance_json("module-ownership.json")
    root = repo_root()
    errors: list[str] = []

    for module in config.get("modules", []):
        path = root / str(module["path"])
        if not path.exists():
            errors.append(f"owned module missing from repo: {module['path']}")
            continue
        for doc_name in module.get("required_docs", []):
            doc_path = path / str(doc_name)
            if not doc_path.is_file():
                errors.append(f"{module['path']}: missing required ownership doc {doc_name}")
        if not str(module.get("owner") or "").strip():
            errors.append(f"{module['path']}: owner must be non-empty")
        if not str(module.get("responsibility") or "").strip():
            errors.append(f"{module['path']}: responsibility must be non-empty")

    if errors:
        print("[module-ownership] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[module-ownership] PASS ({len(config.get('modules', []))} modules declared)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
