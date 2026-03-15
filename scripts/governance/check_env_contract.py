#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

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
    "ENV_PROFILE",
    "GITHUB_ACTOR",
    "HOME",
    "PATH",
    "PWD",
    "PYTEST_CURRENT_TEST",
    "PYTHONPATH",
}

PY_GETENV_RE = re.compile(r'os\.getenv\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
PY_ENV_RE = re.compile(r'os\.environ\[\s*["\']([A-Z][A-Z0-9_]*)["\']\s*\]')
PY_ENV_GET_RE = re.compile(r'os\.environ\.get\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
TS_PROCESS_ENV_RE = re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)")
SH_DEFAULT_ENV_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)[:-][^}]*\}")
ENV_EXAMPLE_EXPORT_RE = re.compile(r"^\s*(?:#\s*)?export\s+([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)
ENV_FILE_KEY_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)
ENV_FILE_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)\s*$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_contract_paths(raw_contracts: list[str], root: Path) -> list[Path]:
    if not raw_contracts:
        return [root / "infra/config/env.contract.json"]
    output: list[Path] = []
    seen: set[Path] = set()
    for item in raw_contracts:
        for token in item.split(","):
            token = token.strip()
            if not token:
                continue
            path = (
                (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
            )
            if path in seen:
                continue
            seen.add(path)
            output.append(path)
    return output


def _load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"env contract must be a JSON object: {path}")
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise ValueError(f"env contract must contain a 'variables' list: {path}")
    for idx, item in enumerate(variables):
        if not isinstance(item, dict):
            raise ValueError(f"variables[{idx}] must be an object: {path}")
        missing = CONTRACT_FIELDS - item.keys()
        if missing:
            raise ValueError(f"variables[{idx}] missing fields {sorted(missing)}: {path}")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ValueError(f"variables[{idx}] has invalid name: {name!r} ({path})")
        if not isinstance(item.get("required"), bool):
            raise ValueError(f"variables[{idx}] required must be boolean ({path})")
        if not isinstance(item.get("secret"), bool):
            raise ValueError(f"variables[{idx}] secret must be boolean ({path})")
        consumers = item.get("consumer")
        if not isinstance(consumers, list) or any(not isinstance(c, str) for c in consumers):
            raise ValueError(f"variables[{idx}] consumer must be list[str] ({path})")

    required_default_violations = sorted(
        item["name"] for item in variables if item["required"] and item["default"] is not None
    )
    if required_default_violations:
        raise ValueError(
            "required variables must use default=null: " + ", ".join(required_default_violations)
        )
    return payload


def _load_contract_map(contract_paths: list[Path]) -> dict[Path, dict]:
    loaded: dict[Path, dict] = {}
    for path in contract_paths:
        if not path.is_file():
            raise FileNotFoundError(f"contract not found: {path}")
        loaded[path] = _load_contract(path)
    return loaded


def _discover_universe_contract_paths(root: Path, selected_paths: list[Path]) -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_file():
            return
        seen.add(resolved)
        candidates.append(resolved)

    for path in selected_paths:
        add(path)

    add(root / "infra/config/env.contract.json")

    split_dir = root / "infra/config/env"
    if split_dir.is_dir():
        for path in sorted(split_dir.glob("contract*.json")):
            add(path)

    return candidates


def _iter_files(root: Path, include_paths: list[str] | None = None) -> list[Path]:
    files: list[Path] = []
    bases = include_paths[:] if include_paths else ["apps", "scripts"]
    for base in bases:
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


def _collect_references(root: Path, include_paths: list[str] | None = None) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for file_path in _iter_files(root, include_paths=include_paths):
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


def _required_contract_vars(contract_payloads: dict[Path, dict]) -> set[str]:
    return {
        item["name"]
        for payload in contract_payloads.values()
        for item in payload["variables"]
        if item["required"]
    }


def _web_e2e_critical_vars(contract_payloads: dict[Path, dict]) -> set[str]:
    names: set[str] = set()
    for payload in contract_payloads.values():
        for item in payload["variables"]:
            consumers = item.get("consumer", [])
            if any("apps/web/tests/e2e/" in ref for ref in consumers):
                names.add(item["name"])
    return names


def _load_env_file_vars(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    content = path.read_text(encoding="utf-8")
    return set(ENV_FILE_KEY_RE.findall(content))


def _parse_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def _load_env_file_items(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    items: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        matched = ENV_FILE_LINE_RE.match(line)
        if not matched:
            continue
        key, raw_value = matched.group(1), matched.group(2)
        items[key] = _parse_env_value(raw_value)
    return items


def _load_profile_matrix(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), dict):
        raise ValueError("profile matrix must contain an object field 'profiles'")
    return payload


def _resolve_profile(
    root: Path,
    profile: str,
    profile_matrix_path: Path,
) -> tuple[list[Path], set[str], list[str]]:
    matrix = _load_profile_matrix(profile_matrix_path)
    profiles = matrix["profiles"]
    profile_item = profiles.get(profile)
    if not isinstance(profile_item, dict):
        raise ValueError(f"profile not found: {profile}")

    contract_entries = profile_item.get("contracts", [])
    if not isinstance(contract_entries, list) or any(
        not isinstance(x, str) for x in contract_entries
    ):
        raise ValueError(f"profile '{profile}' contracts must be list[str]")

    allowed_vars = profile_item.get("allowed_vars", [])
    if not isinstance(allowed_vars, list) or any(not isinstance(x, str) for x in allowed_vars):
        raise ValueError(f"profile '{profile}' allowed_vars must be list[str]")

    include_paths = profile_item.get("include_paths", [])
    if not isinstance(include_paths, list) or any(not isinstance(x, str) for x in include_paths):
        raise ValueError(f"profile '{profile}' include_paths must be list[str]")

    resolved_contracts = _normalize_contract_paths(contract_entries, root)
    return resolved_contracts, set(allowed_vars), include_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate env references against env contracts")
    parser.add_argument(
        "--contract",
        action="append",
        default=[],
        help=(
            "Contract JSON path relative to repo root. "
            "Can be repeated or use comma-separated paths. "
            "Default: infra/config/env.contract.json"
        ),
    )
    parser.add_argument(
        "--profile",
        default="",
        help="Profile name in profile matrix. Enables allowed variable set validation.",
    )
    parser.add_argument(
        "--profile-matrix",
        default="infra/config/env/profile-matrix.json",
        help="Path to profile matrix JSON file relative to repo root.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status when contract violations are found.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file path (relative to repo root) to check for unregistered keys. Use empty value to disable.",
    )
    args = parser.parse_args()

    root = _repo_root()
    include_paths: list[str] | None = None

    try:
        selected_contract_paths = _normalize_contract_paths(args.contract, root)
        profile_allowed_vars: set[str] = set()
        if args.profile.strip():
            profile_paths, explicit_allowed_vars, profile_include_paths = _resolve_profile(
                root=root,
                profile=args.profile.strip(),
                profile_matrix_path=root / args.profile_matrix,
            )
            if not args.contract:
                selected_contract_paths = profile_paths
            profile_allowed_vars = explicit_allowed_vars
            if profile_include_paths:
                include_paths = profile_include_paths

        selected_contracts = _load_contract_map(selected_contract_paths)

        universe_paths = _discover_universe_contract_paths(root, selected_contract_paths)
        universe_contracts = _load_contract_map(universe_paths)
    except Exception as exc:
        print(f"[env-contract] invalid configuration: {exc}", file=sys.stderr)
        return 2

    registered = {
        item["name"] for payload in selected_contracts.values() for item in payload["variables"]
    }
    universe = {
        item["name"] for payload in universe_contracts.values() for item in payload["variables"]
    }
    allowed_vars = set(registered)
    if args.profile.strip():
        allowed_vars |= profile_allowed_vars

    refs_by_file = _collect_references(root, include_paths=include_paths)

    missing_by_file: dict[str, list[str]] = {}
    disallowed_by_file: dict[str, list[str]] = {}
    for file_path, refs in refs_by_file.items():
        missing = sorted(ref for ref in refs if ref not in universe)
        if missing:
            missing_by_file[file_path] = missing

        if args.profile.strip():
            disallowed = sorted(ref for ref in refs if ref in universe and ref not in allowed_vars)
            if disallowed:
                disallowed_by_file[file_path] = disallowed

    all_refs = sorted({item for refs in refs_by_file.values() for item in refs})
    missing_refs = sorted({item for refs in missing_by_file.values() for item in refs})
    disallowed_refs = sorted({item for refs in disallowed_by_file.values() for item in refs})

    required_vars = _required_contract_vars(selected_contracts)
    web_e2e_critical_vars = _web_e2e_critical_vars(selected_contracts)
    expected_in_example = required_vars | web_e2e_critical_vars

    try:
        env_example_vars = _load_env_example_vars(root / ".env.example")
    except Exception as exc:
        print(f"[env-contract] invalid .env.example: {exc}", file=sys.stderr)
        return 2

    missing_in_example = sorted(var for var in expected_in_example if var not in env_example_vars)

    print(f"[env-contract] selected contracts: {len(selected_contract_paths)}")
    for path in selected_contract_paths:
        print(f"  - {path.relative_to(root)}")
    print(f"[env-contract] registered vars (selected): {len(registered)}")
    print(f"[env-contract] known vars (universe): {len(universe)}")
    print(f"[env-contract] referenced vars: {len(all_refs)}")

    if missing_refs:
        print(f"[env-contract] unregistered refs: {len(missing_refs)}")
        for file_path, missing in sorted(missing_by_file.items()):
            print(f"  - {file_path}: {', '.join(missing)}")
    else:
        print("[env-contract] all references are registered in known contracts")

    if args.profile.strip():
        print(f"[env-contract] profile: {args.profile.strip()}")
        print(f"[env-contract] allowed vars by profile: {len(allowed_vars)}")
        if disallowed_refs:
            print(f"[env-contract] disallowed refs by profile: {len(disallowed_refs)}")
            for file_path, refs in sorted(disallowed_by_file.items()):
                print(f"  - {file_path}: {', '.join(refs)}")
        else:
            print("[env-contract] profile allow-list check passed")

    print(f"[env-contract] required vars in selected contracts: {len(required_vars)}")
    print(
        f"[env-contract] web e2e critical vars in selected contracts: {len(web_e2e_critical_vars)}"
    )
    if missing_in_example:
        print(f"[env-contract] missing in .env.example: {len(missing_in_example)}")
        print(f"  - vars: {', '.join(missing_in_example)}")
    else:
        print("[env-contract] .env.example covers required + web e2e critical vars")

    unregistered_env_keys: list[str] = []
    missing_required_in_env: list[str] = []
    empty_required_in_env: list[str] = []
    if args.env_file.strip():
        env_file_path = root / args.env_file
        if env_file_path.is_file():
            env_file_items = _load_env_file_items(env_file_path)
            env_file_vars = set(env_file_items.keys())
            unregistered_env_keys = sorted(var for var in env_file_vars if var not in universe)
            print(f"[env-contract] vars in {args.env_file}: {len(env_file_vars)}")
            if unregistered_env_keys:
                print(
                    f"[env-contract] unregistered vars in {args.env_file}: "
                    f"{len(unregistered_env_keys)}"
                )
                print(f"  - vars: {', '.join(unregistered_env_keys)}")
            else:
                print(f"[env-contract] {args.env_file} has no unregistered vars")

            missing_required_in_env = sorted(
                var for var in required_vars if var not in env_file_items
            )
            empty_required_in_env = sorted(
                var for var in required_vars if var in env_file_items and env_file_items[var] == ""
            )
            if missing_required_in_env or empty_required_in_env:
                print(
                    f"[env-contract] required vars missing/empty in {args.env_file}: "
                    f"{len(missing_required_in_env) + len(empty_required_in_env)}"
                )
                if missing_required_in_env:
                    print(f"  - missing: {', '.join(missing_required_in_env)}")
                if empty_required_in_env:
                    print(f"  - empty: {', '.join(empty_required_in_env)}")
            else:
                print(f"[env-contract] required vars in {args.env_file} are present and non-empty")
        else:
            print(f"[env-contract] {args.env_file} not found; skip env-file key check")

    if args.strict and (
        missing_refs
        or missing_in_example
        or unregistered_env_keys
        or disallowed_refs
        or missing_required_in_env
        or empty_required_in_env
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
