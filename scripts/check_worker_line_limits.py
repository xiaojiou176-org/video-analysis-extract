#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

MAX_LINES = 750
TARGET_GLOBS = (
    "apps/worker/worker/pipeline/steps/*.py",
    "apps/worker/worker/temporal/*.py",
)


def main() -> int:
    root = Path.cwd()
    violations: list[tuple[str, int]] = []

    for pattern in TARGET_GLOBS:
        for file_path in sorted(root.glob(pattern)):
            if not file_path.is_file():
                continue
            line_count = len(file_path.read_text(encoding="utf-8").splitlines())
            if line_count > MAX_LINES:
                violations.append((str(file_path), line_count))

    if not violations:
        print(f"worker line limit check passed (max={MAX_LINES})")
        return 0

    print(f"worker line limit check failed (max={MAX_LINES})")
    for file_path, line_count in violations:
        print(f"- {file_path}: {line_count} lines")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
