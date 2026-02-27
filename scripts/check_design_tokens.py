#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
RGB_HSL = re.compile(r"\b(?:rgb|rgba|hsl|hsla)\s*\(")
ALLOW_PATTERNS = (
    "var(--",
    "tokens.",
    "theme.",
    "colors.",
    "# noqa",
    "/* noqa",
)
ALLOW_FILE_HINTS = ("token", "theme", "palette")
VALID_SUFFIXES = {".css", ".scss", ".tsx", ".jsx"}
SKIP_PATH_HINTS = (
    "/node_modules/",
    "\\node_modules\\",
    "/.next",
    "\\.next",
    "/.next/",
    "\\.next\\",
    "/dist/",
    "\\dist\\",
    "/build/",
    "\\build\\",
)


def _is_allowed_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("--") and ":" in stripped:
        return True
    return any(pattern in line for pattern in ALLOW_PATTERNS)


def _should_skip_file(path: Path) -> bool:
    lower = str(path).lower()
    if any(hint in lower for hint in SKIP_PATH_HINTS):
        return True
    return any(hint in lower for hint in ALLOW_FILE_HINTS)


def _collect_paths(inputs: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for raw in inputs:
        candidate = Path(raw)
        if not candidate.exists():
            continue
        if candidate.is_dir():
            for path in candidate.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in VALID_SUFFIXES:
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                result.append(resolved)
            continue
        if candidate.is_file() and candidate.suffix.lower() in VALID_SUFFIXES:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(resolved)
    return sorted(result)


def _parse_added_lines(diff_text: str) -> set[int]:
    added: set[int] = set()
    current_target_line = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw in diff_text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("@@"):
            match = hunk_re.match(line)
            if match:
                current_target_line = int(match.group(1))
            continue
        if line.startswith(("+++ ", "--- ")):
            continue
        if line.startswith("+"):
            added.add(current_target_line)
            current_target_line += 1
            continue
        if line.startswith("-"):
            continue
        if line.startswith("\\"):
            continue
        current_target_line += 1
    return added


def _git_added_lines(
    path: Path, *, staged_only: bool, from_ref: str | None, to_ref: str | None
) -> set[int] | None:
    rel = path.as_posix()
    if staged_only:
        cmd = ["git", "diff", "--cached", "--unified=0", "--", rel]
    elif from_ref and to_ref:
        cmd = ["git", "diff", "--unified=0", f"{from_ref}..{to_ref}", "--", rel]
    else:
        return None

    try:
        diff = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    return _parse_added_lines(diff)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Block hardcoded color literals outside token-based styling."
    )
    parser.add_argument("paths", nargs="*", help="Files or directories to scan")
    parser.add_argument(
        "--staged-only", action="store_true", help="Check only added lines in staged diff"
    )
    parser.add_argument("--from-ref", help="Git base ref for diff scanning")
    parser.add_argument("--to-ref", help="Git head ref for diff scanning")
    parser.add_argument("--all-lines", action="store_true", help="Force full-file scan")
    args = parser.parse_args()

    if args.all_lines and (args.staged_only or args.from_ref or args.to_ref):
        print(
            "design-token-guard: --all-lines cannot be combined with diff options", file=sys.stderr
        )
        return 2
    if (args.from_ref and not args.to_ref) or (args.to_ref and not args.from_ref):
        print(
            "design-token-guard: --from-ref and --to-ref must be provided together", file=sys.stderr
        )
        return 2

    scan_paths = _collect_paths(args.paths or ["apps/web"])
    violations: list[str] = []
    scanned_lines = 0
    for path in scan_paths:
        if _should_skip_file(path):
            continue
        target_lines = (
            None
            if args.all_lines
            else _git_added_lines(
                path,
                staged_only=args.staged_only,
                from_ref=args.from_ref,
                to_ref=args.to_ref,
            )
        )
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for idx, line in enumerate(content.splitlines(), start=1):
            if target_lines is not None and idx not in target_lines:
                continue
            scanned_lines += 1
            if _is_allowed_line(line):
                continue
            if HEX_COLOR.search(line) or RGB_HSL.search(line):
                violations.append(f"{path}:{idx}: hardcoded color literal found")

    if scanned_lines == 0:
        print("design-token-guard passed (no target lines to scan)")
        return 0

    if violations:
        print("design-token-guard failed:")
        for item in violations:
            print(f"  - {item}")
        print("hint: use CSS variables (var(--...)) or token helpers")
        return 1

    print("design-token-guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
