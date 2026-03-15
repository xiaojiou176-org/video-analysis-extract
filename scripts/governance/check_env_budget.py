#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_contract(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise ValueError(f"invalid contract format: {path}")
    return variables


def _count_unique_names(items: list[dict]) -> int:
    return len({item.get("name") for item in items if isinstance(item.get("name"), str)})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce environment-variable budget ceilings to prevent config bloat."
    )
    parser.add_argument("--max-core", type=int, default=20)
    parser.add_argument("--max-runtime", type=int, default=100)
    parser.add_argument("--max-scripts", type=int, default=120)
    parser.add_argument("--max-universe", type=int, default=216)
    args = parser.parse_args()

    root = _repo_root()
    core_contract = root / "infra/config/env/contract.core.json"
    runtime_contract = root / "infra/config/env/contract.runtime.json"
    scripts_contract = root / "infra/config/env/contract.scripts.json"
    universe_contract = root / "infra/config/env.contract.json"

    core = _count_unique_names(_load_contract(core_contract))
    runtime = _count_unique_names(_load_contract(runtime_contract))
    scripts = _count_unique_names(_load_contract(scripts_contract))
    universe = _count_unique_names(_load_contract(universe_contract))

    print(
        "[env-budget] counts: "
        f"core={core}/{args.max_core}, "
        f"runtime={runtime}/{args.max_runtime}, "
        f"scripts={scripts}/{args.max_scripts}, "
        f"universe={universe}/{args.max_universe}"
    )

    violations: list[str] = []
    if core > args.max_core:
        violations.append(f"core({core}) > max_core({args.max_core})")
    if runtime > args.max_runtime:
        violations.append(f"runtime({runtime}) > max_runtime({args.max_runtime})")
    if scripts > args.max_scripts:
        violations.append(f"scripts({scripts}) > max_scripts({args.max_scripts})")
    if universe > args.max_universe:
        violations.append(f"universe({universe}) > max_universe({args.max_universe})")

    if violations:
        print("[env-budget] FAIL:", "; ".join(violations), file=sys.stderr)
        print(
            "[env-budget] hint: remove/merge env vars or explicitly raise budget with rationale.",
            file=sys.stderr,
        )
        return 1

    print("[env-budget] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
