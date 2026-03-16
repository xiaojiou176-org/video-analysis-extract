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


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _repo_slug_from_remote(remote: str) -> str:
    patterns = [
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote)
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    raise SystemExit(f"unable to derive GitHub repository slug from remote.origin.url: {remote}")


def _repo_slug() -> str:
    remote = _run("git", "config", "--get", "remote.origin.url").stdout.strip()
    return _repo_slug_from_remote(remote)


def _json_or_none(command: list[str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = _run(*command, check=False)
    if result.returncode == 0:
        return json.loads(result.stdout), None
    error = {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    return None, error


def _current_actor() -> str:
    payload, _ = _json_or_none(["gh", "api", "user"])
    return str((payload or {}).get("login") or "").strip()


def _switch_actor(login: str) -> None:
    result = _run("gh", "auth", "switch", "-u", login, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"unable to switch GitHub actor to `{login}`: {detail}")


def _load_required_checks() -> list[str]:
    path = ROOT / "docs" / "generated" / "required-checks.md"
    pattern = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*required\s*\|$")
    checks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if match:
            checks.append(match.group("name"))
    return checks


def _actual_required_checks(branch_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(branch_payload, dict):
        return []
    required = branch_payload.get("required_status_checks")
    if not isinstance(required, dict):
        return []
    contexts = required.get("contexts")
    if isinstance(contexts, list):
        return sorted({str(item) for item in contexts if str(item).strip()})
    checks = required.get("checks")
    if isinstance(checks, list):
        values: set[str] = set()
        for item in checks:
            if isinstance(item, dict) and str(item.get("context") or "").strip():
                values.add(str(item["context"]))
        return sorted(values)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe remote GitHub repository/platform truth for the current repo.")
    parser.add_argument(
        "--output",
        default=".runtime-cache/reports/governance/remote-platform-truth.json",
        help="Report output path under repo root.",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Explicit GitHub repository slug (owner/repo). Defaults to origin remote.",
    )
    parser.add_argument(
        "--actor",
        default="",
        help="Optional gh account login to switch to for the probe.",
    )
    args = parser.parse_args()

    previous_actor = _current_actor()
    requested_actor = args.actor.strip()
    if requested_actor and requested_actor != previous_actor:
        _switch_actor(requested_actor)

    try:
        slug = args.repo.strip() or _repo_slug()
        actor_result = _run("gh", "api", "user", check=False)
        actor = ""
        actor_error: dict[str, Any] | None = None
        if actor_result.returncode == 0:
            actor = json.loads(actor_result.stdout).get("login", "")
        else:
            actor_error = {
                "returncode": actor_result.returncode,
                "stdout": actor_result.stdout.strip(),
                "stderr": actor_result.stderr.strip(),
            }

        repo_payload, repo_error = _json_or_none(
            ["gh", "repo", "view", slug, "--json", "name,owner,visibility,defaultBranchRef,isPrivate"]
        )
        actions_payload, actions_error = _json_or_none(["gh", "api", f"repos/{slug}/actions/permissions"])
        branch_payload, branch_error = _json_or_none(["gh", "api", f"repos/{slug}/branches/main/protection"])

        expected_required_checks = _load_required_checks()
        actual_required_checks = _actual_required_checks(branch_payload)
        missing_checks = sorted(set(expected_required_checks) - set(actual_required_checks))
        extra_checks = sorted(set(actual_required_checks) - set(expected_required_checks))

        overall_status = "pass"
        blocker_type = ""
        if repo_error:
            overall_status = "blocked"
            blocker_type = "repo-readability"
        elif branch_error or str((repo_payload or {}).get("visibility") or "") != "PUBLIC":
            overall_status = "blocked"
            blocker_type = "branch-protection-platform-boundary"
        elif missing_checks or extra_checks:
            overall_status = "blocked"
            blocker_type = "required-check-integrity-mismatch"

        report = {
            "version": 2,
            "status": overall_status,
            "blocker_type": blocker_type,
            "repo": slug,
            "actor": actor,
            "requested_actor": requested_actor,
            "previous_actor": previous_actor,
            "actor_error": actor_error,
            "source_commit": current_git_commit(),
            "repo_view": repo_payload,
            "repo_view_error": repo_error,
            "actions_permissions": actions_payload,
            "actions_permissions_error": actions_error,
            "branch_protection": branch_payload,
            "branch_protection_error": branch_error,
            "required_checks": {
                "expected": expected_required_checks,
                "actual": actual_required_checks,
                "missing": missing_checks,
                "extra": extra_checks,
                "match": not missing_checks and not extra_checks,
            },
        }

        write_json_artifact(
            ROOT / args.output,
            report,
            source_entrypoint="scripts/governance/probe_remote_platform_truth.py",
            verification_scope="remote-platform-truth",
            source_run_id="remote-platform-truth-probe",
            freshness_window_hours=24,
            extra={"report_kind": "remote-platform-truth"},
        )

        if overall_status == "pass":
            print("[remote-platform-truth] PASS")
            print(f"  - repo={slug}")
            print(f"  - actor={actor or '<unknown>'}")
            return 0

        print("[remote-platform-truth] BLOCKED")
        print(f"  - repo={slug}")
        print(f"  - actor={actor or '<unknown>'}")
        print(f"  - blocker_type={blocker_type}")
        if branch_error:
            print(f"  - branch_protection_error={branch_error.get('stderr') or branch_error.get('stdout')}")
        elif repo_error:
            print(f"  - repo_view_error={repo_error.get('stderr') or repo_error.get('stdout')}")
        elif missing_checks or extra_checks:
            print(f"  - missing_checks={','.join(missing_checks) or '<none>'}")
            print(f"  - extra_checks={','.join(extra_checks) or '<none>'}")
        return 0
    finally:
        if requested_actor and previous_actor and requested_actor != previous_actor:
            _switch_actor(previous_actor)


if __name__ == "__main__":
    raise SystemExit(main())
