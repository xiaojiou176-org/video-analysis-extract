#!/usr/bin/env python3
"""Minimal CI docs parity check for testing governance keywords.

Checks whether docs/testing.md contains key strategy signals agreed in Phase0:
- PR-enforced live-smoke
- mutation baseline >=0.60 (current policy uses 0.62)
- web coverage 85/95
- no skip for key gates
- E2E real API
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)


def _match_all(text: str, patterns: list[str]) -> bool:
    return all(re.search(p, text, flags=re.IGNORECASE | re.DOTALL) for p in patterns)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "docs" / "testing.md"

    if not target.exists():
        print(f"[ERROR] Target file not found: {target}")
        return 2

    content = target.read_text(encoding="utf-8")

    rules = [
        {
            "id": "D1",
            "name": "PR强制live-smoke",
            "mode": "any",
            "patterns": [
                r"(?:PR|pull[_ -]?request).{0,120}(?:强制|必须|必跑).{0,60}live[-_ ]?smoke",
                r"live[-_ ]?smoke.{0,120}(?:PR|pull[_ -]?request).{0,60}(?:强制|必须|必跑)",
                r"live[-_ ]?smoke.{0,120}(?:not\s+skipped|不得\s*skipped|不允许\s*skipped)",
            ],
        },
        {
            "id": "D2",
            "name": "mutation>=0.60",
            "mode": "any",
            "patterns": [
                r"mutation[^\n]{0,80}(?:>=\s*0\.(?:6[0-9]|[7-9][0-9])|0\.(?:6[0-9]|[7-9][0-9])|60\s*%|61\s*%|62\s*%|63\s*%|64\s*%|65\s*%)",
                r"mutmut[^\n]{0,80}(?:>=\s*0\.(?:6[0-9]|[7-9][0-9])|0\.(?:6[0-9]|[7-9][0-9])|60\s*%|61\s*%|62\s*%|63\s*%|64\s*%|65\s*%)",
            ],
        },
        {
            "id": "D3",
            "name": "web覆盖85/95",
            "mode": "all",
            "patterns": [
                r"(?:web|前端)[^\n]{0,80}(?:>=\s*85\s*%|85\s*%)",
                r"(?:web|前端)[^\n]{0,120}(?:核心|关键|core)[^\n]{0,80}(?:>=\s*95\s*%|95\s*%)",
            ],
        },
        {
            "id": "D4",
            "name": "禁skip",
            "mode": "any",
            "patterns": [
                r"(?:禁止|不允许|不得)[^\n]{0,40}skip(?:ped)?",
                r"skip(?:ped)?[^\n]{0,40}(?:禁止|不允许|不得|not\s+allowed|forbidden)",
            ],
        },
        {
            "id": "D5",
            "name": "E2E real API",
            "mode": "any",
            "patterns": [
                r"(?:E2E|端到端)[^\n]{0,120}(?:real\s*API|真实\s*API)",
                r"(?:real\s*API|真实\s*API)[^\n]{0,120}(?:E2E|端到端)",
            ],
        },
    ]

    print("CI Docs Parity Check")
    print(f"Target: {target}")
    print("Rules:")

    failed = []
    for rule in rules:
        matcher = _match_all if rule["mode"] == "all" else _match_any
        ok = matcher(content, rule["patterns"])
        status = "PASS" if ok else "FAIL"
        print(f"- [{status}] {rule['id']} {rule['name']}")
        if not ok:
            failed.append(f"{rule['id']} {rule['name']}")

    if failed:
        print("\nResult: FAILED")
        print("Missing strategy keywords:")
        for item in failed:
            print(f"- {item}")
        return 1

    print("\nResult: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
