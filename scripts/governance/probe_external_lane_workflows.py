#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import current_git_commit, write_json_artifact


WORKFLOW_MAP = {
    "ghcr-standard-image": "build-ci-standard-image.yml",
    "release-evidence-attestation": "release-evidence-attest.yml",
}


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=ROOT, check=check, capture_output=True, text=True)


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url").stdout.strip()
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$", remote)
    if not match:
        raise SystemExit(f"unable to derive GitHub repository slug from remote.origin.url: {remote}")
    return f"{match.group('owner')}/{match.group('repo')}"


def _json_or_none(command: list[str]) -> tuple[Any | None, dict[str, Any] | None]:
    result = _run(*command, check=False)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    return None, {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _lane_state(current_head: str, run: dict[str, Any] | None) -> tuple[str, str, bool, str, str]:
    if not run:
        return "missing", "no remote workflow run found", False, "", "missing"
    status = str(run.get("status") or "")
    conclusion = str(run.get("conclusion") or "")
    run_head = str(run.get("headSha") or "")
    if not run_head and conclusion == "success":
        return (
            "blocked",
            "remote workflow completed without headSha; current HEAD cannot be verified",
            False,
            run_head,
            "missing",
        )
    if run_head and run_head != current_head:
        if status in {"queued", "pending"}:
            return (
                "historical",
                f"latest queued remote workflow targets old head `{run_head}`; current HEAD `{current_head}` has no queued remote run",
                False,
                run_head,
                "historical",
            )
        if status == "in_progress":
            return (
                "historical",
                f"latest in-progress remote workflow targets old head `{run_head}`; current HEAD `{current_head}` has no active remote run",
                False,
                run_head,
                "historical",
            )
        if conclusion == "success":
            return (
                "historical",
                f"latest successful remote workflow targets old head `{run_head}`; current HEAD `{current_head}` still not externally verified",
                False,
                run_head,
                "historical",
            )
        if conclusion:
            return (
                "historical",
                f"latest completed remote workflow targets old head `{run_head}` with conclusion `{conclusion}`; current HEAD `{current_head}` still unresolved",
                False,
                run_head,
                "historical",
            )
        return (
            "historical",
            f"latest remote workflow targets old head `{run_head}`; current HEAD `{current_head}` still unresolved",
            False,
            run_head,
            "historical",
        )
    if status in {"queued", "pending"}:
        return "queued", "remote workflow queued for current HEAD", True, run_head, "current"
    if status == "in_progress":
        return "in_progress", "remote workflow in progress for current HEAD", True, run_head, "current"
    if conclusion == "success":
        return "verified", "remote workflow completed successfully for current HEAD", True, run_head, "current"
    if conclusion:
        return "blocked", f"remote workflow for current HEAD concluded `{conclusion}`", True, run_head, "current"
    return (
        "blocked",
        f"unexpected workflow state status={status} conclusion={conclusion}",
        bool(run_head == current_head),
        run_head,
        "current" if run_head == current_head and run_head else "missing",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture latest remote workflow states for external lanes.")
    parser.add_argument("--repo", default="", help="Explicit owner/repo slug. Defaults to origin remote.")
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/external-lane-workflows.json",
        help="Output report path.",
    )
    args = parser.parse_args()

    repo = args.repo.strip() or _repo_slug()
    current_head = current_git_commit()
    actor_payload, actor_error = _json_or_none(["gh", "api", "user"])
    actor = str((actor_payload or {}).get("login") or "")

    lanes: list[dict[str, Any]] = []
    overall_status = "pass"
    for lane_name, workflow_file in WORKFLOW_MAP.items():
        payload, error = _json_or_none(
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow_file,
                "--limit",
                "1",
                "--json",
                "databaseId,workflowName,status,conclusion,displayTitle,headSha,updatedAt,url",
            ]
        )
        latest_run = payload[0] if isinstance(payload, list) and payload else None
        lane_state, note, matches_current_head, latest_run_head_sha, head_alignment = _lane_state(current_head, latest_run)
        if lane_state == "blocked":
            overall_status = "blocked"
        lanes.append(
            {
                "name": lane_name,
                "workflow_file": workflow_file,
                "state": lane_state,
                "note": note,
                "latest_run_matches_current_head": matches_current_head,
                "latest_run_head_sha": latest_run_head_sha,
                "head_alignment": head_alignment,
                "latest_run": latest_run,
                "error": error,
            }
        )

    report = {
        "version": 1,
        "status": overall_status,
        "repo": repo,
        "actor": actor,
        "actor_error": actor_error,
        "source_commit": current_head,
        "lanes": lanes,
    }
    write_json_artifact(
        ROOT / args.output,
        report,
        source_entrypoint="scripts/governance/probe_external_lane_workflows.py",
        verification_scope="external-lane-workflows",
        source_run_id="external-lane-workflows",
        freshness_window_hours=24,
        extra={"report_kind": "external-lane-workflows"},
    )

    print("[external-lane-workflows] PASS")
    for lane in lanes:
        latest_run = lane.get("latest_run") or {}
        run_id = latest_run.get("databaseId", "")
        print(f"  - {lane['name']}: {lane['state']} run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
