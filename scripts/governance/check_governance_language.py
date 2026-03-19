#!/usr/bin/env python3
from __future__ import annotations

import re
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

STRICT_ENGLISH_PATHS = [
    "scripts/governance/render_current_state_summary.py",
    "scripts/governance/render_docs_governance.py",
    "docs/reference/done-model.md",
    "docs/reference/external-lane-status.md",
    "docs/reference/runner-baseline.md",
    "docs/reference/root-governance.md",
    "docs/reference/upstream-compatibility-policy.md",
    "docs/reference/mcp-tool-routing.md",
]

HAN_RE = re.compile(r"[\u4e00-\u9fff]")


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

    for rel in STRICT_ENGLISH_PATHS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: missing strict English governance target")
            continue
        content = path.read_text(encoding="utf-8")
        if HAN_RE.search(content):
            errors.append(f"{rel}: contains non-English governance/runtime text on a strict-English surface")

    if errors:
        print("[governance-language] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[governance-language] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
