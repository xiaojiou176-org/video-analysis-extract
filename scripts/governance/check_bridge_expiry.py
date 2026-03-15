#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "governance" / "bridges.json"
ALLOWED_STATUS = {"planned", "active-bridge", "completed", "abandoned"}
REQUIRED_FIELDS = {
    "name",
    "status",
    "owner",
    "introduced_at",
    "write_forbidden_after",
    "remove_after",
    "source_paths",
    "target_paths",
    "notes",
}


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def main() -> int:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"missing bridge registry: {CONFIG_PATH}")

    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    bridges = payload.get("bridges", [])
    if payload.get("version") != 1:
        errors.append("bridges.json must declare version=1")
    if not isinstance(bridges, list) or not bridges:
        errors.append("bridges.json must declare a non-empty bridges list")

    now = datetime.now().astimezone()
    seen: set[str] = set()
    for item in bridges:
        if not isinstance(item, dict):
            errors.append("bridge entry must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - set(item))
        if missing:
            errors.append(
                f"bridge {item.get('name', '<unknown>')} missing fields: {', '.join(missing)}"
            )
            continue

        name = str(item["name"])
        if name in seen:
            errors.append(f"duplicate bridge entry: {name}")
        seen.add(name)

        status = str(item["status"])
        if status not in ALLOWED_STATUS:
            errors.append(f"bridge {name} uses unsupported status `{status}`")

        for field_name in ("source_paths", "target_paths"):
            value = item[field_name]
            if not isinstance(value, list) or not value or not all(
                isinstance(entry, str) and entry.strip() for entry in value
            ):
                errors.append(f"bridge {name} must declare non-empty string list `{field_name}`")

        try:
            introduced_at = _parse_timestamp(str(item["introduced_at"]))
            write_forbidden_after = _parse_timestamp(str(item["write_forbidden_after"]))
            remove_after = _parse_timestamp(str(item["remove_after"]))
        except ValueError as exc:
            errors.append(f"bridge {name} contains invalid timestamp: {exc}")
            continue

        if introduced_at > write_forbidden_after:
            errors.append(f"bridge {name} has introduced_at after write_forbidden_after")
        if write_forbidden_after > remove_after:
            errors.append(f"bridge {name} has write_forbidden_after after remove_after")
        if status in {"planned", "active-bridge"} and now > remove_after:
            errors.append(
                f"bridge {name} exceeded remove_after without being marked completed or abandoned"
            )
        if status == "completed" and now < introduced_at:
            errors.append(f"bridge {name} cannot be completed before introduced_at")

    if errors:
        print("[bridge-expiry] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[bridge-expiry] PASS ({len(bridges)} bridges tracked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
