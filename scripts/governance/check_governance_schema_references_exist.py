#!/usr/bin/env python3
from __future__ import annotations

import sys
import shlex
from pathlib import Path

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def _prefix_to_path(prefix: str) -> Path | None:
    normalized = prefix.strip().rstrip(".")
    if not normalized:
        return None
    if normalized.startswith("@/"):
        return repo_root() / "apps" / "web" / normalized[2:].replace("/", "/")
    if normalized.startswith("apps.") or normalized.startswith("integrations.") or normalized.startswith("contracts."):
        return repo_root() / normalized.replace(".", "/")
    return None


def _check_dependency_boundaries(errors: list[str]) -> None:
    payload = load_governance_json("dependency-boundaries.json")
    root = repo_root()

    for rule in payload.get("python_rules", []):
        scope = root / str(rule.get("scope", ""))
        if not scope.exists():
            errors.append(f"dependency-boundaries: scope missing `{scope.relative_to(root).as_posix()}`")
        for prefix in rule.get("allow_internal_prefixes", []):
            target = _prefix_to_path(str(prefix))
            if target is not None and not target.exists():
                errors.append(
                    "dependency-boundaries: allow_internal_prefix points to missing path "
                    f"`{prefix}` -> `{target.relative_to(root).as_posix()}`"
                )

    for rule in payload.get("frontend_rules", []):
        scope = root / str(rule.get("scope", ""))
        if not scope.exists():
            errors.append(f"dependency-boundaries: frontend scope missing `{scope.relative_to(root).as_posix()}`")


def _check_module_ownership(errors: list[str]) -> None:
    payload = load_governance_json("module-ownership.json")
    root = repo_root()
    for module in payload.get("modules", []):
        module_path = root / str(module.get("path", ""))
        if not module_path.exists():
            errors.append(f"module-ownership: module path missing `{module_path.relative_to(root).as_posix()}`")
        for prefix in module.get("allowed_internal_prefixes", []):
            target = _prefix_to_path(str(prefix))
            if target is not None and not target.exists():
                errors.append(
                    "module-ownership: allowed_internal_prefix points to missing path "
                    f"`{prefix}` -> `{target.relative_to(root).as_posix()}`"
                )


def _check_bridges(errors: list[str]) -> None:
    payload = load_governance_json("bridges.json")
    root = repo_root()
    active_statuses = {"active-bridge", "planned"}
    for bridge in payload.get("bridges", []):
        status = str(bridge.get("status", "")).strip()
        if status not in active_statuses:
            continue
        for key in ("source_paths", "target_paths"):
            for raw in bridge.get(key, []):
                rendered = str(raw).strip()
                if " " in rendered and not rendered.startswith("./") and not rendered.startswith(".runtime-cache/"):
                    parts = shlex.split(rendered)
                    if len(parts) >= 2 and not parts[1].startswith("-"):
                        rendered = parts[1]
                if rendered.startswith("./"):
                    candidate = root / rendered[2:]
                else:
                    candidate = root / rendered
                if rendered.startswith(".runtime-cache/"):
                    candidate_parent = candidate.parent
                    if not candidate_parent.exists():
                        errors.append(
                            f"bridges: active bridge path parent missing for `{rendered}` under `{key}`"
                        )
                    continue
                if not candidate.exists():
                    errors.append(f"bridges: active bridge path missing `{rendered}` under `{key}`")


def main() -> int:
    errors: list[str] = []
    _check_dependency_boundaries(errors)
    _check_module_ownership(errors)
    _check_bridges(errors)

    if errors:
        print("[governance-schema-references] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[governance-schema-references] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
