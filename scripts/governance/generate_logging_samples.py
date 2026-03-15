#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from common import repo_root


def _emit_jsonl_sample(
    *,
    root: Path,
    path: Path,
    run_id: str,
    trace_id: str,
    request_id: str,
    service: str,
    component: str,
    channel: str,
    source_kind: str,
    event: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "runtime" / "log_jsonl_event.py"),
            "--path",
            str(path),
            "--run-id",
            run_id,
            "--trace-id",
            trace_id,
            "--request-id",
            request_id,
            "--service",
            service,
            "--component",
            component,
            "--channel",
            channel,
            "--source-kind",
            source_kind,
            "--event",
            event,
            "--severity",
            "info",
            "--message",
            f"{channel} logging sample ready",
        ],
        check=True,
        cwd=root,
    )


def main() -> int:
    root = repo_root()
    sample_run_id = "logging-contract-sample-run"
    targets = {
        "governance": (
            root / ".runtime-cache" / "logs" / "governance" / "governance-gate.jsonl",
            "governance",
            "governance-gate",
            "governance",
            "sample_ready",
        ),
        "tests": (
            root / ".runtime-cache" / "logs" / "tests" / "logging-contract-tests.jsonl",
            "tests",
            "logging-contract-tests",
            "test",
            "sample_ready",
        ),
        "app": (
            root / ".runtime-cache" / "logs" / "app" / "api-http.jsonl",
            "api",
            "http",
            "app",
            "http_request",
        ),
        "components": (
            root / ".runtime-cache" / "logs" / "components" / "full-stack" / "logging-contract-components.jsonl",
            "full-stack",
            "full-stack",
            "app",
            "sample_ready",
        ),
        "infra": (
            root / ".runtime-cache" / "logs" / "infra" / "bootstrap" / "logging-contract-infra.jsonl",
            "bootstrap",
            "bootstrap-strict-ci-runtime",
            "infra",
            "sample_ready",
        ),
    }
    for channel, (path, service, component, source_kind, event) in targets.items():
        _emit_jsonl_sample(
            root=root,
            path=path,
            run_id=sample_run_id,
            trace_id=f"trace-{channel}-sample",
            request_id=f"req-{channel}-sample",
            service=service,
            component=component,
            channel=channel,
            source_kind=source_kind,
            event=event,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
