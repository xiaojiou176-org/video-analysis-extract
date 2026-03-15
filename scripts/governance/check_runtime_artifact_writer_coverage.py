#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import rel_path, repo_root

ROOT = repo_root()
TARGET_PATTERNS = (
    ".runtime-cache/reports/",
    ".runtime-cache/evidence/",
)
HELPER_MARKERS = (
    "write_json_artifact(",
    "write_text_artifact(",
    "write_runtime_metadata(",
    "ensure_runtime_metadata(",
)
WRITE_TEXT_RE = re.compile(r"\.write_text\(")


def _candidate_files() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "scripts").rglob("*.py")
        if path.is_file()
    )


def main() -> int:
    offenders: list[str] = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8")
        if not any(pattern in text for pattern in TARGET_PATTERNS):
            continue
        if not WRITE_TEXT_RE.search(text):
            continue
        if any(marker in text for marker in HELPER_MARKERS):
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
