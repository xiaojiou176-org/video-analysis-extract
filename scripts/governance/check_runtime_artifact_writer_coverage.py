#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, rel_path, repo_root

ROOT = repo_root()
HELPER_MARKERS = (
    "write_json_artifact(",
    "write_text_artifact(",
    "write_runtime_metadata(",
    "ensure_runtime_metadata(",
)
WRITE_TEXT_RE = re.compile(r"\.write_text\(")
WRITE_TARGET_RE = re.compile(r"(?P<var>[A-Za-z_][A-Za-z0-9_]*)\.write_text\(")
RUNTIME_ASSIGN_RE = re.compile(
    r"^(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*.*(?:\.runtime-cache/reports/|\.runtime-cache/evidence/)"
)


def _candidate_files() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "scripts").rglob("*.py")
        if path.is_file()
    )


def main() -> int:
    contract = load_governance_json("evidence-contract.json")
    target_patterns = tuple(
        f"{str(config.get('path')).rstrip('/')}/"
        for name, config in contract.get("buckets", {}).items()
        if name in {"reports", "evidence"} and str(config.get("path") or "").strip()
    )
    offenders: list[str] = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8")
        if not any(pattern in text for pattern in target_patterns):
            continue
        if not WRITE_TEXT_RE.search(text):
            continue
        if any(marker in text for marker in HELPER_MARKERS):
            continue
        runtime_write_vars: set[str] = set()
        for line in text.splitlines():
            match = RUNTIME_ASSIGN_RE.search(line)
            if match:
                runtime_write_vars.add(match.group("var"))
        if not runtime_write_vars:
            continue
        if not any(
            (match := WRITE_TARGET_RE.search(line)) and match.group("var") in runtime_write_vars
            for line in text.splitlines()
        ):
            continue
        offenders.append(rel_path(path))

    if offenders:
        print("[runtime-artifact-writer-coverage] FAIL")
        for item in offenders:
            print(
                f"  - {item}: writes runtime report/evidence artifacts without managed artifact helper or explicit metadata call"
            )
        return 1

    print("[runtime-artifact-writer-coverage] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
