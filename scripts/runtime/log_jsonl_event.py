#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))
from common import current_git_commit, write_runtime_metadata


_TOKEN_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~-]+", re.IGNORECASE),
    re.compile(r"\b(?:sk|ghp|gho|github_pat)_[A-Za-z0-9_]+\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def _redact(value: str) -> str:
    redacted = value
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub("<redacted>", redacted)
    return redacted


def main() -> int:
    parser = argparse.ArgumentParser(description="Append one structured JSONL log event.")
    parser.add_argument("--path", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trace-id", default="")
    parser.add_argument("--request-id", default="")
    parser.add_argument("--service", default="")
    parser.add_argument("--component", required=True)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--source-kind", default="")
    parser.add_argument("--test-id", default="")
    parser.add_argument("--test-run-id", default="")
    parser.add_argument("--gate-run-id", default="")
    parser.add_argument("--upstream-id", default="")
    parser.add_argument("--upstream-operation", default="")
    parser.add_argument("--upstream-contract-surface", default="")
    parser.add_argument("--failure-class", default="")
    parser.add_argument("--entrypoint", default="")
    parser.add_argument("--env-profile", default="")
    parser.add_argument("--repo-commit", default="")
    parser.add_argument("--event", required=True)
    parser.add_argument("--severity", required=True)
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    source_kind = args.source_kind.strip()
    if not source_kind:
        source_kind = {
            "app": "app",
            "components": "app",
        "tests": "test",
        "governance": "governance",
        "infra": "infra",
        "upstreams": "upstream",
        }.get(args.channel, "app")

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "trace_id": args.trace_id or "missing_trace",
        "request_id": args.request_id or "",
        "service": args.service or args.component,
        "component": args.component,
        "channel": args.channel,
        "event": args.event,
        "severity": args.severity,
        "source_kind": source_kind,
        "repo_commit": args.repo_commit or current_git_commit(),
        "entrypoint": args.entrypoint or args.component,
        "env_profile": args.env_profile or "unknown",
        "message": _redact(args.message),
    }
    optional_fields = {
        "test_id": args.test_id,
        "test_run_id": args.test_run_id,
        "gate_run_id": args.gate_run_id,
        "upstream_id": args.upstream_id,
        "upstream_operation": args.upstream_operation,
        "upstream_contract_surface": args.upstream_contract_surface,
        "failure_class": args.failure_class,
    }
    for key, value in optional_fields.items():
        if value:
            payload[key] = value

    path = Path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    write_runtime_metadata(
        path,
        source_entrypoint=args.entrypoint or args.component,
        verification_scope=f"log:{args.channel}",
        source_run_id=args.run_id,
        source_commit=payload["repo_commit"],
        freshness_window_hours=24 * 30,
        extra={
            "channel": args.channel,
            "source_kind": source_kind,
            "env_profile": payload["env_profile"],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
