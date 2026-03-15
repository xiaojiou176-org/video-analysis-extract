#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, rel_path, repo_root


def _python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
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
    config = load_governance_json("dependency-boundaries.json")
    root = repo_root()
    errors: list[str] = []
    internal_roots = tuple(config.get("internal_roots", []))

    for rule in config.get("python_rules", []):
        scope = root / str(rule["scope"])
        allow_internal_prefixes = tuple(rule.get("allow_internal_prefixes", []))
        for path in scope.rglob("*.py"):
            if "/tests/" in path.as_posix():
                continue
            imports = _python_imports(path)
            offenders = sorted(
                item
                for item in imports
                if item.startswith(internal_roots) and not item.startswith(allow_internal_prefixes)
            )
            if offenders:
                errors.append(
                    f"{rel_path(path)} imports internal modules outside allowlist: {', '.join(offenders)}"
                )

    for rule in config.get("frontend_rules", []):
        scope = root / str(rule["scope"])
        allow_import_prefixes = tuple(rule.get("allow_import_prefixes", []))
        for path in scope.rglob("*"):
            if "node_modules" in path.parts or not path.is_file():
                continue
            if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            imports = _frontend_imports(path)
            unexpected_aliases = sorted(
                item
                for item in imports
                if (item.startswith("@/") or item.startswith("./") or item.startswith("../"))
                and not item.startswith(allow_import_prefixes)
            )
            if unexpected_aliases:
                errors.append(
                    f"{rel_path(path)} imports frontend modules outside allowlist: "
                    + ", ".join(unexpected_aliases)
                )
            for substring in rule.get("forbid_substrings", []):
                offenders = sorted(item for item in imports if substring in item)
                if offenders:
                    errors.append(
                        f"{rel_path(path)} imports forbidden frontend targets containing {substring}: "
                        + ", ".join(offenders)
                    )

    for rule in config.get("package_purity_rules", []):
        scope = root / str(rule["scope"])
        for path in scope.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".md", ".txt"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for substring in rule.get("forbid_substrings", []):
                if substring in content:
                    errors.append(
                        f"{rel_path(path)} violates package purity by referencing `{substring}`"
                    )

    if errors:
        print("[dependency-boundaries] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[dependency-boundaries] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
