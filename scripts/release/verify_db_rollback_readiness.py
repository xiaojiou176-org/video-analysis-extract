#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _run_git(repo_root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


def _latest_tag(repo_root: Path) -> str | None:
    try:
        out = _run_git(repo_root, ["describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None
    return out or None


def _load_blockers(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    migrations = payload.get("migrations")
    if not isinstance(migrations, dict):
        return {}
    parsed: dict[str, dict[str, Any]] = {}
    for key, value in migrations.items():
        if isinstance(key, str) and isinstance(value, dict):
            parsed[key] = value
    return parsed


def _has_executable_sql(path: Path) -> bool:
    if not path.is_file():
        return False
    statements: list[str] = []
    current: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        current.append(line)
        if line.endswith(";"):
            merged = " ".join(current).strip()
            if merged:
                statements.append(merged)
            current = []
    if current:
        tail = " ".join(current).strip()
        if tail:
            statements.append(tail)
    return len(statements) > 0


def _validate_drill_evidence(path: Path) -> tuple[bool, list[str]]:
    if not path.is_file():
        return False, [f"missing file: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"invalid json: {exc}"]
    required_keys = {
        "release_tag",
        "executed_at",
        "executor",
        "strategy",
        "result",
        "migrations_checked",
    }
    missing = sorted(k for k in required_keys if k not in payload)
    if missing:
        return False, [f"missing keys: {', '.join(missing)}"]
    if not isinstance(payload.get("migrations_checked"), list):
        return False, ["migrations_checked must be a list"]
    return True, []


def _write_template_if_missing(path: Path, release_tag: str) -> None:
    if path.exists():
        return
    template = {
        "release_tag": release_tag,
        "executed_at": "",
        "executor": "",
        "strategy": "sql_down_or_n_minus_1_restore",
        "result": "pending",
        "migrations_checked": [],
        "notes": "Fill this file after rollback drill execution.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify DB rollback readiness: each up migration must have down SQL or explicit blocker policy."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--release-tag", default="")
    parser.add_argument("--write-drill-template", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output).resolve()

    migrations_dir = repo_root / "infra" / "migrations"
    down_dir = migrations_dir / "down"
    blockers_path = down_dir / "rollback-blockers.json"
    blockers = _load_blockers(blockers_path)

    up_migrations = sorted(p for p in migrations_dir.glob("*.sql") if p.is_file())
    rows: list[dict[str, Any]] = []
    with_down = 0
    with_blocker = 0
    missing_policy = 0
    invalid_down_sql = 0

    for up in up_migrations:
        down_name = f"{up.stem}.down.sql"
        down_path = down_dir / down_name
        blocker = blockers.get(up.name)
        status = "missing_policy"
        strategy = "unclassified"
        evidence: dict[str, Any] = {"up": str(up.relative_to(repo_root))}
        if down_path.is_file() and _has_executable_sql(down_path):
            status = "rehearsable"
            strategy = "down_sql"
            with_down += 1
            evidence["down"] = str(down_path.relative_to(repo_root))
        elif down_path.is_file():
            status = "invalid_down_sql"
            strategy = "down_sql_invalid"
            invalid_down_sql += 1
            evidence["down"] = str(down_path.relative_to(repo_root))
            evidence["hint"] = "Down migration exists but has no executable SQL statement."
        elif blocker:
            status = "blocked"
            strategy = "explicit_blocker"
            with_blocker += 1
            evidence["blocker"] = blocker
        else:
            missing_policy += 1
            evidence["hint"] = f"Add {down_path} or blockers entry in {blockers_path}"
        rows.append(
            {
                "migration": up.name,
                "status": status,
                "strategy": strategy,
                "evidence": evidence,
            }
        )

    latest_tag = _latest_tag(repo_root)
    release_tag = args.release_tag.strip() or latest_tag or "unversioned"
    release_dir = repo_root / "artifacts" / "releases" / release_tag / "rollback"
    release_dir.mkdir(parents=True, exist_ok=True)

    drill_path = release_dir / "drill.json"
    if args.write_drill_template:
        _write_template_if_missing(drill_path, release_tag)
    drill_ok, drill_errors = _validate_drill_evidence(drill_path)

    gate_status = "pass" if missing_policy == 0 and with_blocker == 0 and invalid_down_sql == 0 else "fail"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "release_tag": release_tag,
        "latest_tag": latest_tag,
        "summary": {
            "total_up_migrations": len(up_migrations),
            "with_down_sql": with_down,
            "blocked_without_down": with_blocker,
            "missing_policy": missing_policy,
            "invalid_down_sql": invalid_down_sql,
            "gate_status": gate_status,
        },
        "drill_evidence": {
            "path": str(drill_path.relative_to(repo_root)),
            "valid": drill_ok,
            "errors": drill_errors,
        },
        "migrations": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
