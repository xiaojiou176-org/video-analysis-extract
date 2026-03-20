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
    env_profile: str,
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
            "--test-run-id",
            run_id if channel == "tests" else "",
            "--gate-run-id",
            run_id if channel == "governance" else "",
            "--entrypoint",
            f"scripts/governance/generate_logging_samples.py:{channel}",
            "--env-profile",
            env_profile,
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
    env_profile = "governance-sample"
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
        "upstreams": (
            root / ".runtime-cache" / "logs" / "upstreams" / "logging-contract-upstreams.jsonl",
            "provider-canary",
            "provider-canary",
            "upstream",
            "probe_ready",
        ),
    }
    for channel, (path, service, component, source_kind, event) in targets.items():
        extra_args: list[str] = []
        if channel == "upstreams":
            extra_args = [
                "--upstream-id",
                "sample-upstream",
                "--upstream-operation",
                "health_probe",
            ]
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "runtime" / "log_jsonl_event.py"),
                "--path",
                str(path),
                "--run-id",
                sample_run_id,
                "--trace-id",
                f"trace-{channel}-sample",
                "--request-id",
                f"req-{channel}-sample",
                "--service",
                service,
                "--component",
                component,
                "--channel",
                channel,
                "--source-kind",
                source_kind,
                "--test-run-id",
                sample_run_id if channel == "tests" else "",
                "--gate-run-id",
                sample_run_id if channel == "governance" else "",
                "--entrypoint",
                f"scripts/governance/generate_logging_samples.py:{channel}",
                "--env-profile",
                env_profile,
                "--event",
                event,
                "--severity",
                "info",
                "--message",
                f"{channel} logging sample ready",
                *extra_args,
            ],
            check=True,
            cwd=root,
        )

    additional_app_targets = (
        (
            root / ".runtime-cache" / "logs" / "app" / "worker-commands.jsonl",
            "worker",
            "worker-cli",
            "worker-command-sample",
        ),
        (
            root / ".runtime-cache" / "logs" / "app" / "mcp-api.jsonl",
            "mcp",
            "mcp-api",
            "mcp-api-sample",
        ),
    )
    for path, service, component, run_id in additional_app_targets:
        _emit_jsonl_sample(
            root=root,
            path=path,
            run_id=run_id,
            trace_id=f"trace-{component}",
            request_id=f"req-{component}",
            service=service,
            component=component,
            channel="app",
            source_kind="app",
            event="sample_ready",
            env_profile=env_profile,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
