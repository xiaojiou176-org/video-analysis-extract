#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

CRITICAL_FILES = (
    "apps/api/app/security.py",
    "apps/api/app/services/ingest.py",
    "apps/api/app/services/videos.py",
    "apps/worker/worker/comments/bilibili.py",
    "apps/worker/worker/comments/youtube.py",
    "apps/worker/worker/temporal/activities_poll.py",
)

LOG_LEVELS = {"debug", "info", "warning", "error", "exception"}
ERROR_LEVELS = {"warning", "error", "exception"}


class StructuredLogChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, set[str]]] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "logger"
        ):
            level = func.attr
            if level in LOG_LEVELS:
                keys = self._extract_extra_keys(node)
                self.calls.append((level, node.lineno, keys))
        self.generic_visit(node)

    @staticmethod
    def _extract_extra_keys(node: ast.Call) -> set[str]:
        for kw in node.keywords:
            if kw.arg != "extra":
                continue
            value = kw.value
            if isinstance(value, ast.Dict):
                keys: set[str] = set()
                for key in value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
                return keys
        return set()


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"{path}: missing critical-path file"]

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    checker = StructuredLogChecker()
    checker.visit(tree)
    if not checker.calls:
        return [f"{path}: no logger.* calls found in critical path"]

    for level, lineno, keys in checker.calls:
        missing_common = {"trace_id", "user"} - keys
        if missing_common:
            errors.append(
                f"{path}:{lineno}: logger.{level} missing required extra keys: "
                + ", ".join(sorted(missing_common))
            )
        if level in ERROR_LEVELS and "error" not in keys:
            errors.append(f"{path}:{lineno}: logger.{level} missing required extra key: error")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    all_errors: list[str] = []
    for rel in CRITICAL_FILES:
        all_errors.extend(check_file(root / rel))
    if all_errors:
        print("[structured-logs] FAIL")
        for err in all_errors:
            print(f"  - {err}")
        return 1
    print("[structured-logs] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
