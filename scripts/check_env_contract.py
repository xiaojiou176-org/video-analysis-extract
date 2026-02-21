#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CONTRACT_FIELDS = {
    "name",
    "scope",
    "required",
    "secret",
    "default",
    "consumer",
    "description",
}

IGNORE_REFS = {
    "BASH_SOURCE",
    "HOME",
    "PATH",
    "PWD",
    "PYTHONPATH",
}

PY_GETENV_RE = re.compile(r'os\.getenv\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
PY_ENV_RE = re.compile(r'os\.environ\[\s*["\']([A-Z][A-Z0-9_]*)["\']\s*\]')
PY_ENV_GET_RE = re.compile(r'os\.environ\.get\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
TS_PROCESS_ENV_RE = re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)")
SH_DEFAULT_ENV_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)[:-][^}]*\}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("env contract must be a JSON object")
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise ValueError("env contract must contain a 'variables' list")
    for idx, item in enumerate(variables):
        if not isinstance(item, dict):
            raise ValueError(f"variables[{idx}] must be an object")
        missing = CONTRACT_FIELDS - item.keys()
        if missing:
            raise ValueError(f"variables[{idx}] missing fields: {sorted(missing)}")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ValueError(f"variables[{idx}] has invalid name: {name!r}")
    return payload


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for base in ("apps", "scripts"):
        base_dir = root / base
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "node_modules", ".next", "__pycache__"} for part in path.parts):
                continue
            if path.suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".sh"}:
                files.append(path)
    return files


def _collect_references(root: Path) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for file_path in _iter_files(root):
        content = file_path.read_text(encoding="utf-8")
        found: set[str] = set()
        if file_path.suffix == ".py":
            found.update(PY_GETENV_RE.findall(content))
            found.update(PY_ENV_RE.findall(content))
            found.update(PY_ENV_GET_RE.findall(content))
        if file_path.suffix in {".ts", ".tsx", ".js", ".mjs"}:
            found.update(TS_PROCESS_ENV_RE.findall(content))
        if file_path.suffix == ".sh":
            found.update(SH_DEFAULT_ENV_RE.findall(content))

        filtered = {item for item in found if item not in IGNORE_REFS}
        if filtered:
            refs[str(file_path.relative_to(root))] = filtered
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate env references against env.contract.json")
    parser.add_argument(
        "--contract",
        default="infra/config/env.contract.json",
        help="Path to env contract JSON file relative to repo root.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when unregistered references are found.",
    )
    args = parser.parse_args()

    root = _repo_root()
    contract_path = root / args.contract
    if not contract_path.is_file():
        print(f"[env-contract] contract not found: {contract_path}", file=sys.stderr)
        return 2

    try:
        contract = _load_contract(contract_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[env-contract] invalid contract: {exc}", file=sys.stderr)
        return 2

    registered = {item["name"] for item in contract["variables"]}
    refs_by_file = _collect_references(root)

    missing_by_file: dict[str, list[str]] = {}
    for file_path, refs in refs_by_file.items():
        missing = sorted(ref for ref in refs if ref not in registered)
        if missing:
            missing_by_file[file_path] = missing

    all_refs = sorted({item for refs in refs_by_file.values() for item in refs})
    missing_refs = sorted({item for refs in missing_by_file.values() for item in refs})

    print(f"[env-contract] registered vars: {len(registered)}")
    print(f"[env-contract] referenced vars: {len(all_refs)}")
    if missing_refs:
        print(f"[env-contract] unregistered refs: {len(missing_refs)}")
        for file_path, missing in sorted(missing_by_file.items()):
            print(f"  - {file_path}: {', '.join(missing)}")
    else:
        print("[env-contract] all references are registered")

    if args.strict and missing_refs:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
