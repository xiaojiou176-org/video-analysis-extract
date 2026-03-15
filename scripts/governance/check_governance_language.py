#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common import repo_root


CHECK_PATHS = [
    "README.md",
    "docs/start-here.md",
    "docs/runbook-local.md",
    "docs/testing.md",
    "docs/state-machine.md",
    "docs/reference/cache.md",
    "docs/reference/logging.md",
    "docs/reference/dependency-governance.md",
    "docs/reference/env-script-overrides.md",
    "docs/deploy/full-stack-gce.md",
]

FORBIDDEN_SNIPPETS = [
    "兼容旧行为",
    "兼容历史",
    "迁移期保留",
    "过渡期",
    "legacy env 仅兼容",
]


def main() -> int:
    root = repo_root()
    errors: list[str] = []
    for rel in CHECK_PATHS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing governance language check target")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in content:
                errors.append(f"{rel}: contains forbidden governance legacy phrase `{snippet}`")

    if errors:
        print("[governance-language] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[governance-language] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
