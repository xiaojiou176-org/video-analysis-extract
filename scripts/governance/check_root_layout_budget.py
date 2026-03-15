#!/usr/bin/env python3
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from common import load_governance_json, top_level_entries


def main() -> int:
    budget = load_governance_json("root-layout-budget.json")
    root_allowlist = load_governance_json("root-allowlist.json")
    tolerated = {
        str(item["path"])
        for item in root_allowlist.get("local_private_root_tolerations", [])
        if isinstance(item, dict) and item.get("path")
    }
    docs_allowlist = set(budget.get("root_doc_allowlist", []))
    entries = [item for item in top_level_entries() if item.name != ".git" and item.name not in tolerated]
    files = [item for item in entries if item.is_file()]
    directories = [item for item in entries if item.is_dir()]
    root_docs = [item.name for item in files if item.name in docs_allowlist]
    errors: list[str] = []

    if len(files) > int(budget["max_public_top_level_files"]):
        errors.append(
            f"public top-level file budget exceeded: {len(files)} > {budget['max_public_top_level_files']}"
        )
    if len(directories) > int(budget["max_public_top_level_directories"]):
        errors.append(
            "public top-level directory budget exceeded: "
            f"{len(directories)} > {budget['max_public_top_level_directories']}"
        )
    if len(root_docs) > int(budget["max_root_docs"]):
        errors.append(f"root doc budget exceeded: {len(root_docs)} > {budget['max_root_docs']}")

    tolerated_present = [item for item in top_level_entries() if item.name in tolerated]
    if len(tolerated_present) > int(budget["max_local_private_tolerations_present"]):
        errors.append(
            "local-private tolerated entry budget exceeded: "
            f"{len(tolerated_present)} > {budget['max_local_private_tolerations_present']}"
        )

    if errors:
        print("[root-layout-budget] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(
        "[root-layout-budget] PASS "
        f"(files={len(files)} dirs={len(directories)} root_docs={len(root_docs)} local_private={len(tolerated_present)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
