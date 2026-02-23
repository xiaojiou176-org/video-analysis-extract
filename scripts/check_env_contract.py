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
    "GITHUB_ACTOR",
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
ENV_EXAMPLE_EXPORT_RE = re.compile(r"^\s*(?:#\s*)?export\s+([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)
ENV_FILE_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


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
        if not isinstance(item.get("required"), bool):
            raise ValueError(f"variables[{idx}] required must be boolean")
        if not isinstance(item.get("secret"), bool):
            raise ValueError(f"variables[{idx}] secret must be boolean")
        consumers = item.get("consumer")
        if not isinstance(consumers, list) or any(not isinstance(c, str) for c in consumers):
            raise ValueError(f"variables[{idx}] consumer must be list[str]")

    required_default_violations = sorted(
        item["name"] for item in variables if item["required"] and item["default"] is not None
    )
    if required_default_violations:
        raise ValueError(
            "required variables must use default=null: "
            + ", ".join(required_default_violations)
        )
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
            if any(
                part in {".git", "node_modules", "__pycache__"} or part.startswith(".next")
                for part in path.parts
            ):
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


def _load_env_example_vars(path: Path) -> set[str]:
    if not path.is_file():
        raise ValueError(f".env example not found: {path}")
    content = path.read_text(encoding="utf-8")
    return set(ENV_EXAMPLE_EXPORT_RE.findall(content))


def _required_contract_vars(contract: dict) -> set[str]:
    return {item["name"] for item in contract["variables"] if item["required"]}


def _web_e2e_critical_vars(contract: dict) -> set[str]:
    names: set[str] = set()
    for item in contract["variables"]:
        consumers = item.get("consumer", [])
        if any("apps/web/tests/e2e/" in ref for ref in consumers):
            names.add(item["name"])
    return names


def _load_env_file_vars(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    content = path.read_text(encoding="utf-8")
    return set(ENV_FILE_KEY_RE.findall(content))


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
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file path (relative to repo root) to check for unregistered keys. Use empty value to disable.",
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
    required_vars = _required_contract_vars(contract)
    web_e2e_critical_vars = _web_e2e_critical_vars(contract)
    expected_in_example = required_vars | web_e2e_critical_vars

    try:
        env_example_vars = _load_env_example_vars(root / ".env.example")
    except Exception as exc:  # noqa: BLE001
        print(f"[env-contract] invalid .env.example: {exc}", file=sys.stderr)
        return 2

    missing_in_example = sorted(var for var in expected_in_example if var not in env_example_vars)

    print(f"[env-contract] registered vars: {len(registered)}")
    print(f"[env-contract] referenced vars: {len(all_refs)}")
    if missing_refs:
        print(f"[env-contract] unregistered refs: {len(missing_refs)}")
        for file_path, missing in sorted(missing_by_file.items()):
            print(f"  - {file_path}: {', '.join(missing)}")
    else:
        print("[env-contract] all references are registered")
    print(f"[env-contract] required vars in contract: {len(required_vars)}")
    print(f"[env-contract] web e2e critical vars: {len(web_e2e_critical_vars)}")
    if missing_in_example:
        print(f"[env-contract] missing in .env.example: {len(missing_in_example)}")
        print(f"  - vars: {', '.join(missing_in_example)}")
    else:
        print("[env-contract] .env.example covers required + web e2e critical vars")

    unregistered_env_keys: list[str] = []
    if args.env_file.strip():
        env_file_path = root / args.env_file
        if env_file_path.is_file():
            env_file_vars = _load_env_file_vars(env_file_path)
            unregistered_env_keys = sorted(var for var in env_file_vars if var not in registered)
            print(f"[env-contract] vars in {args.env_file}: {len(env_file_vars)}")
            if unregistered_env_keys:
                print(
                    f"[env-contract] unregistered vars in {args.env_file}: "
                    f"{len(unregistered_env_keys)}"
                )
                print(f"  - vars: {', '.join(unregistered_env_keys)}")
            else:
                print(f"[env-contract] {args.env_file} has no unregistered vars")
        else:
            print(f"[env-contract] {args.env_file} not found; skip env-file key check")

    if args.strict and (missing_refs or missing_in_example or unregistered_env_keys):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
