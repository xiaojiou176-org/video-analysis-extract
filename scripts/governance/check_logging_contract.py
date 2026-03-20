#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys

sys.dont_write_bytecode = True

from common import load_governance_json, repo_root


def main() -> int:
    config = load_governance_json("logging-contract.json")
    root = repo_root()
    errors: list[str] = []

    generator = root / "scripts" / "governance" / "generate_logging_samples.py"
    sample_generation = subprocess.run(
        [sys.executable, str(generator)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if sample_generation.returncode != 0:
        detail = sample_generation.stderr.strip() or sample_generation.stdout.strip() or "unknown error"
        errors.append(f"unable to generate logging samples: {detail}")

    for check in config.get("critical_checks", []):
        path = root / str(check["path"])
        if not path.is_file():
            errors.append(f"{check['path']}: missing critical logging contract file")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in check.get("contains", []):
            if snippet not in content:
                errors.append(f"{check['path']}: missing required logging contract snippet `{snippet}`")

    channels = config.get("channels", {})
    if not channels:
        errors.append("logging contract missing channels map")
    for name, value in channels.items():
        if not str(value).startswith(".runtime-cache/logs/"):
            errors.append(f"logging channel `{name}` must live under .runtime-cache/logs/: {value}")

    required_channels = {"app", "components", "tests", "governance", "infra", "upstreams"}
    if set(channels) != required_channels:
        errors.append(
            "logging channels must exactly match: "
            + ", ".join(sorted(required_channels))
        )

    channel_source_kind_map = config.get("channel_source_kind_map", {})
    expected_source_kinds = {
        "app": "app",
        "components": "app",
        "tests": "test",
        "governance": "governance",
        "infra": "infra",
        "upstreams": "upstream",
    }
    for channel, source_kind in expected_source_kinds.items():
        if channel_source_kind_map.get(channel) != source_kind:
            errors.append(
                f"logging contract channel `{channel}` must map to source_kind `{source_kind}`"
            )

    sample_targets = {
        channel: root / rel_path
        for channel, rel_path in config.get("sample_targets", {}).items()
    }
    if set(sample_targets) != required_channels:
        errors.append("logging contract sample_targets must exactly match all required channels")

    channel_required_fields = {
        str(channel): [str(field) for field in fields]
        for channel, fields in config.get("channel_required_fields", {}).items()
    }

    for channel, path in sample_targets.items():
        if not path.is_file():
            errors.append(f"logging sample for channel `{channel}` missing: {path.relative_to(root).as_posix()}")
            continue
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            errors.append(f"logging sample for channel `{channel}` is empty: {path.relative_to(root).as_posix()}")
            continue
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            errors.append(f"logging sample for channel `{channel}` is not valid JSONL: {exc}")
            continue
        for field in config.get("minimum_common_fields", []):
            if field not in payload:
                errors.append(
                    f"logging sample for channel `{channel}` missing required field `{field}`"
                )
                continue
            if field != "request_id" and payload[field] in (None, ""):
                errors.append(
                    f"logging sample for channel `{channel}` has empty required field `{field}`"
                )
        if payload.get("channel") != channel:
            errors.append(
                f"logging sample for channel `{channel}` has mismatched channel `{payload.get('channel')}`"
            )
        if payload.get("source_kind") != channel_source_kind_map.get(channel):
            errors.append(
                f"logging sample for channel `{channel}` has mismatched source_kind `{payload.get('source_kind')}`"
            )
        if not payload.get("service") and not payload.get("component"):
            errors.append(
                f"logging sample for channel `{channel}` must include non-empty `service` or `component`"
            )
        for field in channel_required_fields.get(channel, []):
            if payload.get(field) in (None, ""):
                errors.append(
                    f"logging sample for channel `{channel}` missing channel-required field `{field}`"
                )
        if channel == "app" and payload.get("trace_id") in (None, "", "missing_trace"):
            errors.append("logging sample for channel `app` must include a real trace_id")

    optional_sample_targets = {
        str(channel): [root / str(rel_path) for rel_path in rel_paths]
        for channel, rel_paths in config.get("optional_sample_targets", {}).items()
        if isinstance(rel_paths, list)
    }
    for channel, paths in optional_sample_targets.items():
        if channel not in required_channels:
            errors.append(f"logging contract optional_sample_targets contains unknown channel `{channel}`")
            continue
        for path in paths:
            if not path.is_file():
                errors.append(
                    f"logging optional sample for channel `{channel}` missing: {path.relative_to(root).as_posix()}"
                )
                continue
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not lines:
                errors.append(
                    f"logging optional sample for channel `{channel}` is empty: {path.relative_to(root).as_posix()}"
                )
                continue
            try:
                payload = json.loads(lines[-1])
            except json.JSONDecodeError as exc:
                errors.append(
                    f"logging optional sample for channel `{channel}` is not valid JSONL: {path.relative_to(root).as_posix()} ({exc})"
                )
                continue
            for field in config.get("minimum_common_fields", []):
                if field not in payload:
                    errors.append(
                        f"logging optional sample for channel `{channel}` missing required field `{field}`: {path.relative_to(root).as_posix()}"
                    )
                    continue
                if field != "request_id" and payload[field] in (None, ""):
                    errors.append(
                        f"logging optional sample for channel `{channel}` has empty required field `{field}`: {path.relative_to(root).as_posix()}"
                    )
            if payload.get("channel") != channel:
                errors.append(
                    f"logging optional sample for channel `{channel}` has mismatched channel `{payload.get('channel')}`: {path.relative_to(root).as_posix()}"
                )
            if payload.get("source_kind") != channel_source_kind_map.get(channel):
                errors.append(
                    f"logging optional sample for channel `{channel}` has mismatched source_kind `{payload.get('source_kind')}`: {path.relative_to(root).as_posix()}"
                )
            if not payload.get("service") and not payload.get("component"):
                errors.append(
                    f"logging optional sample for channel `{channel}` must include non-empty `service` or `component`: {path.relative_to(root).as_posix()}"
                )
            for field in channel_required_fields.get(channel, []):
                if payload.get(field) in (None, ""):
                    errors.append(
                        f"logging optional sample for channel `{channel}` missing channel-required field `{field}`: {path.relative_to(root).as_posix()}"
                    )
            if channel == "app" and payload.get("trace_id") in (None, "", "missing_trace"):
                errors.append(
                    f"logging optional sample for channel `app` must include a real trace_id: {path.relative_to(root).as_posix()}"
                )

    if errors:
        print("[logging-contract] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[logging-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
