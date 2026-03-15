#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import repo_root


HIGH_DRIFT_DOCS = (
    "README.md",
    "docs/start-here.md",
)

FORBIDDEN_MANUAL_MIRRORS = (
    "root-allowlist.json",
    "runtime-outputs.json",
    "logging-contract.json",
    "active-upstreams.json",
    "upstream-compat-matrix.json",
)


def main() -> int:
    root = repo_root()
    errors: list[str] = []

    dependency_doc = root / "docs" / "reference" / "dependency-governance.md"
    dependency_text = dependency_doc.read_text(encoding="utf-8")
    for required in (
        "config/governance/active-upstreams.json",
        "config/governance/upstream-templates.json",
        "config/governance/upstream-compat-matrix.json",
    ):
        if required not in dependency_text:
            errors.append(f"docs/reference/dependency-governance.md must cite `{required}` as contract truth source")

    for rel in HIGH_DRIFT_DOCS:
        text = (root / rel).read_text(encoding="utf-8")
        if "├" in text or "└" in text:
            errors.append(f"{rel} must not contain hand-maintained root tree mirrors")
        if sum(token in text for token in FORBIDDEN_MANUAL_MIRRORS) > 3:
            errors.append(f"{rel} appears to mirror too many governance truth-source filenames directly")

    if errors:
        print("[generated-vs-handwritten-contract-surfaces] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[generated-vs-handwritten-contract-surfaces] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
