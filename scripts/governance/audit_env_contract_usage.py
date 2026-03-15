#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_contract(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise ValueError(f"invalid contract (missing variables list): {path}")
    return variables


def _resolve_consumers(root: Path, pattern: str) -> list[Path]:
    if any(ch in pattern for ch in ("*", "?", "[")):
        return [Path(p) for p in glob.glob(str(root / pattern), recursive=False)]
    return [root / pattern]


def _file_contains_name(path: Path, name: str) -> bool:
    if not path.is_file():
        return False
    content = path.read_text(encoding="utf-8", errors="ignore")
    return re.search(rf"\b{re.escape(name)}\b", content) is not None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit env contract usage against declared consumers"
    )
    parser.add_argument(
        "--contract",
        default="infra/config/env.contract.json",
        help="Contract JSON path relative to repo root.",
    )
    args = parser.parse_args()

    root = _repo_root()
    contract_path = (root / args.contract).resolve()
    variables = _load_contract(contract_path)

    stale: list[dict[str, object]] = []
    for item in variables:
        name = item.get("name")
        consumers = item.get("consumer", [])
        if not isinstance(name, str) or not isinstance(consumers, list):
            continue
        found = False
        checked_paths: list[str] = []
        for consumer in consumers:
            if not isinstance(consumer, str):
                continue
            for path in _resolve_consumers(root, consumer):
                checked_paths.append(str(path.relative_to(root)) if path.exists() else str(path))
                if _file_contains_name(path, name):
                    found = True
                    break
            if found:
                break
        if not found:
            stale.append(
                {
                    "name": name,
                    "scope": item.get("scope"),
                    "consumers": consumers,
                    "checked_paths": checked_paths,
                }
            )

    print(f"[env-contract-audit] contract: {contract_path.relative_to(root)}")
    print(f"[env-contract-audit] variables: {len(variables)}")
    print(f"[env-contract-audit] stale-candidates: {len(stale)}")
    for row in stale:
        print(f"- {row['name']} (scope={row['scope']})")
        print(f"  consumers: {', '.join(row['consumers']) if row['consumers'] else '-'}")
        print(f"  checked: {', '.join(row['checked_paths']) if row['checked_paths'] else '-'}")

    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
