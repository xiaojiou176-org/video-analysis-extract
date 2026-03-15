#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


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
    parser.add_argument("--upstream-id", default="")
    parser.add_argument("--upstream-operation", default="")
    parser.add_argument("--upstream-contract-surface", default="")
    parser.add_argument("--failure-class", default="")
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
        "message": _redact(args.message),
    }
    optional_fields = {
        "test_id": args.test_id,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
