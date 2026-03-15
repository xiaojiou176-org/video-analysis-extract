#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import rel_path, repo_root


def _python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _frontend_imports(path: Path) -> set[str]:
    pattern = re.compile(r"""from\s+['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)""")
    content = path.read_text(encoding="utf-8")
    results: set[str] = set()
    for match in pattern.finditer(content):
        value = match.group(1) or match.group(2)
        if value:
            results.add(value)
    return results


def main() -> int:
    root = repo_root()
    errors: list[str] = []

    mcp_root = root / "apps" / "mcp"
    for path in mcp_root.rglob("*.py"):
        if "/tests/" in path.as_posix():
            continue
        offenders = sorted(
            item
            for item in _python_imports(path)
            if item.startswith("apps.api.") or item.startswith("apps.worker.")
        )
        if offenders:
            errors.append(
                f"{rel_path(path)} imports forbidden cross-app implementation modules: {', '.join(offenders)}"
            )

    web_root = root / "apps" / "web"
    for path in web_root.rglob("*"):
        if not path.is_file() or path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        offenders = sorted(
            item
            for item in _frontend_imports(path)
            if "apps/api/" in item or "apps/worker/" in item or "apps/mcp/" in item
        )
        if offenders:
            errors.append(
                f"{rel_path(path)} imports forbidden sibling app implementation paths: {', '.join(offenders)}"
            )

    if errors:
        print("[no-cross-app-implementation-imports] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[no-cross-app-implementation-imports] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
