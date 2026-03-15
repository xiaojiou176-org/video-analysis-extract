#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Prevent accidental focused/todo tests from landing in CI.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("it.only(", re.compile(r"\bit\.only\s*\(")),
    ("test.only(", re.compile(r"\btest\.only\s*\(")),
    ("describe.only(", re.compile(r"\bdescribe\.only\s*\(")),
    ("fit(", re.compile(r"\bfit\s*\(")),
    ("fdescribe(", re.compile(r"\bfdescribe\s*\(")),
    ("it.todo(", re.compile(r"\bit\.todo\s*\(")),
    ("test.todo(", re.compile(r"\btest\.todo\s*\(")),
)

ALLOW_MARKER = "allow-test-focus-marker"
SCAN_SUFFIXES = (".js", ".jsx", ".ts", ".tsx")
TEST_PATH_HINTS = ("__tests__", "/tests/", ".test.", ".spec.")


def _is_candidate(path: Path) -> bool:
    if path.suffix not in SCAN_SUFFIXES:
        return False
    normalized = path.as_posix()
    if "node_modules/" in normalized or ".next/" in normalized:
        return False
    return any(hint in normalized for hint in TEST_PATH_HINTS)


def main() -> int:
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not _is_candidate(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ALLOW_MARKER in line:
                continue
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{lineno}: forbidden marker `{label}`"
                    )

    if violations:
        print("test focus/todo marker gate failed:")
        for item in violations:
            print(f"- {item}")
        print(f"Add `{ALLOW_MARKER}` on the same line only when strictly justified.")
        return 1

    print("test focus/todo marker gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
