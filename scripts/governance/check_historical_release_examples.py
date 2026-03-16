#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import git_output, repo_root


def main() -> int:
    root = repo_root()
    tracked = [
        line.strip()
        for line in git_output("ls-files", "artifacts/releases/**/manifest.json", check=False).splitlines()
        if line.strip()
    ]
    errors: list[str] = []

    for rel in tracked:
        path = root / rel
        if not path.is_file():
            errors.append(f"tracked historical release manifest missing: {rel}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: invalid JSON: {exc}")
            continue

        if payload.get("historical_example") is not True:
            errors.append(f"{rel}: tracked release manifest must set historical_example=true")
        if str(payload.get("evidence_scope") or "") != "historical-example":
            errors.append(f"{rel}: tracked release manifest must set evidence_scope=historical-example")

        git_block = payload.get("git")
        if not isinstance(git_block, dict):
            errors.append(f"{rel}: missing git block")
            continue
        if git_block.get("dirty") is not True:
            errors.append(f"{rel}: tracked historical example must keep git.dirty=true to avoid current-proof confusion")

    readme = root / "artifacts" / "releases" / "README.md"
    if not readme.is_file():
        errors.append("artifacts/releases/README.md missing")
    else:
        text = readme.read_text(encoding="utf-8")
        required_snippets = [
            "historical examples",
            "not release verdict proof",
            "Only the **current run** bundle",
        ]
        for snippet in required_snippets:
            if snippet not in text:
                errors.append(f"artifacts/releases/README.md missing historical-boundary text `{snippet}`")

    if errors:
        print("[historical-release-examples] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[historical-release-examples] PASS ({len(tracked)} tracked manifests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
