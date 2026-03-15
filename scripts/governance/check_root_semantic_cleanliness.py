#!/usr/bin/env python3
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True

from common import load_governance_json

FORBIDDEN_SEGMENTS = {
    "backup",
    "bak",
    "tmp",
    "misc",
    "final-v2",
    "final_v2",
    "copy",
    "old",
    "legacy-dump",
}
ALLOWED_DOTFILES = {
    ".devcontainer",
    ".env",
    ".env.example",
    ".git",
    ".githooks",
    ".github",
    ".gitignore",
    ".gitleaks.toml",
    ".golangci.yml",
    ".markdownlint-cli2.jsonc",
    ".pre-commit-config.yaml",
    ".runtime-cache",
    ".secrets.baseline",
    ".stylelintignore",
    ".stylelintrc.json",
}
ALLOWED_ROOT_FILES = {
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "ENVIRONMENT.md",
    "README.md",
}


def _normalized_tokens(path: str) -> list[str]:
    tokens = re.split(r"[^A-Za-z0-9]+", path.lower())
    return [token for token in tokens if token]


def main() -> int:
    payload = load_governance_json("root-allowlist.json")
    entries = payload.get("entries", [])
    errors: list[str] = []

    for item in entries:
        path = str(item.get("path") or "")
        if not path:
            errors.append("root semantic cleanliness: empty allowlist path")
            continue
        if path.startswith(".") and path not in ALLOWED_DOTFILES:
            errors.append(f"root semantic cleanliness: undeclared dotfile style path `{path}` is not allowed")
        if "__" in path:
            errors.append(f"root semantic cleanliness: double-underscore top-level path is forbidden: {path}")
        if re.search(r"[A-Z]", path) and path not in ALLOWED_ROOT_FILES:
            errors.append(f"root semantic cleanliness: top-level path must be lowercase or conventional dotfile: {path}")
        tokens = set(_normalized_tokens(path))
        bad = sorted(tokens & FORBIDDEN_SEGMENTS)
        if bad:
            errors.append(
                f"root semantic cleanliness: top-level path `{path}` contains forbidden semantic token(s): "
                + ", ".join(bad)
            )

    if errors:
        print("[root-semantic-cleanliness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[root-semantic-cleanliness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
