#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root

_HARDCUT_REQUIRED_PATTERNS = {
    "yt-dlp": "yt-dlp-binary",
    "ffmpeg": "ffmpeg-binary",
    "bbdown": "bbdown-binary",
    "BBDown": "bbdown-binary",
    "https://api.resend.com/": "resend-api",
    "https://rsshub.app": "rsshub",
    "https://github.com/temporalio/cli/releases": "temporal-cli",
    "gitleaks detect": "gitleaks-cli",
    "google.genai": "gemini-api",
}
_IGNORED_DIRS = {
    ".git",
    ".runtime-cache",
    "__pycache__",
    "node_modules",
}
_TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".sh",
    ".toml",
}


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        path = root / line
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in _TEXT_SUFFIXES:
            files.append(path)
    return files


def _load_patterns(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    patterns: dict[str, list[str]] = {}
    for entry in entries:
        name = str(entry.get("name") or "")
        usage_patterns = entry.get("usage_patterns", [])
        if not name:
            continue
        if usage_patterns and isinstance(usage_patterns, list):
            patterns[name] = [str(item) for item in usage_patterns if str(item).strip()]
    return patterns


def _collect_matches(root: Path, patterns: dict[str, list[str]]) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    files = _tracked_files(root)
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rendered = str(path.relative_to(root).as_posix())
        for entry_name, entry_patterns in patterns.items():
            if any(pattern in content for pattern in entry_patterns):
                matches.setdefault(entry_name, []).append(rendered)
    return matches


def main() -> int:
    root = repo_root()
    upstreams = load_governance_json("active-upstreams.json")
    entries = upstreams.get("entries", [])
    errors: list[str] = []

    declared_names = {str(entry.get("name") or "") for entry in entries}
    declared_patterns = _load_patterns(entries)

    for pattern, expected_name in _HARDCUT_REQUIRED_PATTERNS.items():
        if expected_name not in declared_names:
            errors.append(
                f"required upstream `{expected_name}` is missing from active-upstreams.json; "
                f"needed for pattern `{pattern}`"
            )

    for expected_name in _HARDCUT_REQUIRED_PATTERNS.values():
        if expected_name in declared_names and expected_name not in declared_patterns:
            errors.append(
                f"active upstream `{expected_name}` must declare non-empty usage_patterns for hard-cut upstream scanning"
            )

    matches = _collect_matches(root, declared_patterns)
    for pattern, expected_name in _HARDCUT_REQUIRED_PATTERNS.items():
        if expected_name not in declared_names:
            continue
        if expected_name not in matches:
            errors.append(
                f"active upstream `{expected_name}` declares hard-cut coverage but no tracked usage matched its usage_patterns"
            )

    report_path = root / ".runtime-cache" / "reports" / "governance" / "upstream-usage-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 1,
        "declared_names": sorted(name for name in declared_names if name),
        "matched_entries": {key: sorted(value) for key, value in sorted(matches.items())},
        "status": "fail" if errors else "pass",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if errors:
        print("[unregistered-upstream-usage] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[unregistered-upstream-usage] PASS ({len(matches)} upstream usage surfaces matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
