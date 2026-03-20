#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import load_governance_json

ADDITIONAL_APP_CORRELATION_TARGETS = [
    ".runtime-cache/logs/app/worker-commands.jsonl",
    ".runtime-cache/logs/app/mcp-api.jsonl",
]


def _validate_jsonl_target(
    path: Path,
    *,
    channel: str,
    minimum_fields: list[str],
    per_channel: dict[str, list[str]],
    errors: list[str],
) -> None:
    if not path.is_file():
        errors.append(f"{path}: missing sample target")
        return

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        errors.append(f"{path}: empty sample target")
        return

    payload = json.loads(lines[-1])
    for field in minimum_fields:
        if payload.get(field) in (None, ""):
            errors.append(f"{path}: missing minimum correlation field `{field}`")
    if str(channel) == "app" and payload.get("trace_id") == "missing_trace":
        errors.append(f"{path}: app logs must carry a real trace_id")
    for field in per_channel.get(str(channel), []):
        if payload.get(field) in (None, ""):
            errors.append(f"{path}: channel `{channel}` missing required field `{field}`")


def main() -> int:
    evidence_contract = load_governance_json("evidence-contract.json")
    config = load_governance_json("logging-contract.json")
    minimum_fields = [str(field) for field in config.get("minimum_common_fields", [])]
    per_channel = {
        str(channel): [str(field) for field in fields]
        for channel, fields in config.get("channel_required_fields", {}).items()
    }
    errors: list[str] = []
    expected_log_root = str(evidence_contract.get("buckets", {}).get("logs", {}).get("path") or ".runtime-cache/logs")
    if not str(config.get("channels", {}).get("app") or "").startswith(expected_log_root):
        errors.append("logging contract channels drift from evidence-contract logs bucket")

    for channel, rel_path in config.get("sample_targets", {}).items():
        _validate_jsonl_target(
            ROOT / str(rel_path),
            channel=str(channel),
            minimum_fields=minimum_fields,
            per_channel=per_channel,
            errors=errors,
        )

    for rel_path in ADDITIONAL_APP_CORRELATION_TARGETS:
        _validate_jsonl_target(
            ROOT / rel_path,
            channel="app",
            minimum_fields=minimum_fields,
            per_channel=per_channel,
            errors=errors,
        )

    if errors:
        print("[log-correlation-completeness] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[log-correlation-completeness] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
