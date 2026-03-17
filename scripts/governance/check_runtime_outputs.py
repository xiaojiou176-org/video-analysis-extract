#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import find_forbidden_runtime_entries, load_governance_json, repo_root


_DIRECT_RUNTIME_REF = re.compile(r"\.runtime-cache/([A-Za-z0-9._-]+)")


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line:
            paths.append(root / line)
    return paths


def main() -> int:
    payload = load_governance_json("runtime-outputs.json")
    root = repo_root()
    runtime_root = root / str(payload["runtime_root"])
    forbidden = [root / item for item in payload.get("root_forbidden", [])]
    nested_forbidden = [str(item) for item in payload.get("nested_forbidden", [])]
    errors: list[str] = []

    for path in forbidden:
        if path.exists():
            errors.append(f"forbidden root runtime output present: {path.name}")

    allowed_subdirs = set(payload.get("subdirectories", {}).keys())
    required_subdir_fields = {
        "owner",
        "classification",
        "ttl_days",
        "max_total_size_mb",
        "max_file_count",
        "rebuild_entrypoint",
        "freshness_required",
        "description",
    }
    for name, config in payload.get("subdirectories", {}).items():
        missing = sorted(required_subdir_fields - set(config))
        if missing:
            errors.append(
                f"runtime subdirectory `{name}` missing required fields: {', '.join(missing)}"
            )
            continue
        if int(config["ttl_days"]) < 0:
            errors.append(f"runtime subdirectory `{name}` must declare non-negative ttl_days")
        if int(config["max_total_size_mb"]) <= 0:
            errors.append(f"runtime subdirectory `{name}` must declare positive max_total_size_mb")
        if int(config["max_file_count"]) <= 0:
            errors.append(f"runtime subdirectory `{name}` must declare positive max_file_count")
    if runtime_root.exists():
        for child in runtime_root.iterdir():
            if child.is_dir() and child.name in allowed_subdirs:
                continue
            errors.append(f"runtime root contains undeclared direct child: .runtime-cache/{child.name}")
    for entry in find_forbidden_runtime_entries(nested_forbidden):
        errors.append(f"forbidden source-tree runtime output present: {entry}")

    for path in _tracked_files(root):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in _DIRECT_RUNTIME_REF.finditer(content):
            direct_child = match.group(1)
            if direct_child in allowed_subdirs:
                continue
            errors.append(
                f"{path.relative_to(root).as_posix()}: references undeclared runtime child `.runtime-cache/{direct_child}`"
            )
            break

    if errors:
        print("[runtime-outputs] FAIL")
        for item in errors:
            print(f"  - {item}")
        print("  - remediation: run `./bin/workspace-hygiene --apply` to remove illegal repo-root/source-tree runtime residue")
        return 1

    print("[runtime-outputs] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
