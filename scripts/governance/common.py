#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_governance_json(name: str) -> dict[str, Any]:
    path = repo_root() / "config" / "governance" / name
    return json.loads(path.read_text(encoding="utf-8"))


def rel_path(path: Path) -> str:
    return path.relative_to(repo_root()).as_posix()


def top_level_entries() -> list[Path]:
    return sorted(repo_root().iterdir(), key=lambda item: item.name)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def find_forbidden_runtime_entries(patterns: list[str]) -> list[str]:
    root = repo_root()
    allowed_runtime_root = root / ".runtime-cache"
    ignored_dir_names = {".git"}
    matches: set[str] = set()

    for path in root.rglob("*"):
        if any(part in ignored_dir_names for part in path.parts):
            continue
        if path == allowed_runtime_root or _is_within(path, allowed_runtime_root):
            continue
        if any(fnmatch(path.name, pattern) for pattern in patterns):
            matches.add(rel_path(path))

    return sorted(matches)
