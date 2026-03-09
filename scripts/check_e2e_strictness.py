#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
from pathlib import Path

E2E_ROOT = Path("apps/web/tests/e2e")
TEST_GLOB = "test_*.py"
ALLOW_HARD_WAIT_MARKER = "e2e-strictness: allow-hard-wait"
RISKY_TERMS = (
    "error",
    "failed",
    "failure",
    "exception",
    "not found",
    "错误",
    "失败",
    "异常",
)
RISKY_TEST_NAME_PATTERNS = (
    re.compile(r"_or_error(?:_|$)"),
    re.compile(r"_or_fail(?:_|$)"),
    re.compile(r"_or_failure(?:_|$)"),
    re.compile(r"_success_or_(?:error|fail|failure)"),
)


def _iter_test_files() -> list[Path]:
    if not E2E_ROOT.is_dir():
        return []
    return sorted(E2E_ROOT.rglob(TEST_GLOB))


def _check_hard_waits(path: Path, text: str) -> list[str]:
    violations: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if ALLOW_HARD_WAIT_MARKER in stripped:
            continue
        if "wait_for_timeout(" in stripped or re.search(r"\bsleep\(", stripped):
            violations.append(
                f"{path}:{line_no}: hard wait detected (`wait_for_timeout`/`sleep`) without explicit allow marker"
            )
    return violations


def _contains_risky_term(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in RISKY_TERMS)


def _check_test_names(path: Path, tree: ast.AST) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        for pattern in RISKY_TEST_NAME_PATTERNS:
            if pattern.search(node.name):
                violations.append(
                    f"{path}:{node.lineno}: permissive test name `{node.name}` suggests success/failure dual-path acceptance"
                )
                break
    return violations


def _check_permissive_regex_assertions(path: Path, tree: ast.AST) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"to_contain_text", "to_have_text", "to_have_url"}:
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if not isinstance(first_arg, ast.Call):
            continue
        if not isinstance(first_arg.func, ast.Attribute):
            continue
        if not isinstance(first_arg.func.value, ast.Name):
            continue
        if first_arg.func.value.id != "re" or first_arg.func.attr != "compile":
            continue
        if not first_arg.args:
            continue
        pattern_arg = first_arg.args[0]
        if not isinstance(pattern_arg, ast.Constant) or not isinstance(pattern_arg.value, str):
            continue
        pattern_text = pattern_arg.value
        if "|" in pattern_text and _contains_risky_term(pattern_text):
            violations.append(
                f"{path}:{node.lineno}: permissive regex mixes alternatives with risky error terms in text assertion: {pattern_text!r}"
            )
    return violations


def main() -> int:
    files = _iter_test_files()
    if not files:
        print("e2e strictness guard: no e2e tests found, skipping")
        return 0

    violations: list[str] = []
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        violations.extend(_check_hard_waits(file_path, text))
        try:
            tree = ast.parse(text, filename=str(file_path))
        except SyntaxError as exc:
            violations.append(
                f"{file_path}:{exc.lineno or 1}: unable to parse file for strictness checks: {exc.msg}"
            )
            continue
        violations.extend(_check_test_names(file_path, tree))
        violations.extend(_check_permissive_regex_assertions(file_path, tree))

    if violations:
        print("e2e strictness guard failed:")
        for item in violations:
            print(f"- {item}")
        return 1

    print("e2e strictness guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
