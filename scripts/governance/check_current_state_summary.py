#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import current_git_commit, read_runtime_metadata, repo_root

CURRENT_WORKFLOW_STATUSES = {"verified", "queued", "in_progress"}
SUMMARY_PATH = ".runtime-cache/reports/governance/current-state-summary.md"
WORKFLOW_PATH = ".runtime-cache/reports/governance/external-lane-workflows.json"


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _workflow_head_alignment(lane: dict[str, object], head_commit: str) -> tuple[str, str]:
    latest_run = lane.get("latest_run") or {}
    if not isinstance(latest_run, dict):
        latest_run = {}
    latest_head = str(lane.get("latest_run_head_sha") or latest_run.get("headSha") or "").strip()
    matches_current_head = lane.get("latest_run_matches_current_head") is True
    if matches_current_head or (latest_head and latest_head == head_commit):
        return "current", latest_head
    if latest_head:
        return "historical", latest_head
    return "missing", latest_head


def _summary_lane_states(markdown: str) -> dict[str, str]:
    states: dict[str, str] = {}
    for match in re.finditer(r"^\| `(?P<lane>[^`]+)` \| `(?P<state>[^`]+)` \|", markdown, flags=re.MULTILINE):
        states[match.group("lane")] = match.group("state")
    return states


def main() -> int:
    root = repo_root()
    head_commit = current_git_commit()
    errors: list[str] = []

    summary_path = root / SUMMARY_PATH
    if not summary_path.is_file():
        print("[current-state-summary] FAIL")
        print(f"  - summary report missing: {SUMMARY_PATH}")
        return 1

    try:
        summary_text = summary_path.read_text(encoding="utf-8")
    except OSError as exc:
        print("[current-state-summary] FAIL")
        print(f"  - unable to read summary report: {exc}")
        return 1

    metadata = read_runtime_metadata(summary_path)
    if metadata is None:
        errors.append("summary report missing runtime metadata")
    elif str(metadata.get("source_commit") or "") != head_commit:
        errors.append(
            "summary runtime metadata source_commit does not match current HEAD; treat this page as historical until rerendered"
        )

    if f"- current HEAD: `{head_commit}`" not in summary_text:
        errors.append("summary markdown current HEAD line does not match current HEAD")

    lane_states = _summary_lane_states(summary_text)

    remote_report_path = root / ".runtime-cache" / "reports" / "governance" / "remote-platform-truth.json"
    remote_report = _load_json(remote_report_path)
    if remote_report is None:
        errors.append("remote platform truth report missing or invalid")
    else:
        expected_state = str(remote_report.get("status") or "unknown")
        observed_state = lane_states.get("remote-platform-integrity")
        if observed_state is None:
            errors.append("summary missing `remote-platform-integrity` row")
        elif observed_state != expected_state:
            errors.append(
                f"summary row `remote-platform-integrity` must mirror runtime report state `{expected_state}`"
            )

    required_checks_path = root / ".runtime-cache" / "reports" / "governance" / "remote-required-checks.json"
    required_checks = _load_json(required_checks_path)
    if required_checks is None:
        errors.append("remote required checks report missing or invalid")
    else:
        expected_state = str(required_checks.get("status") or "unknown")
        observed_state = lane_states.get("remote-required-checks")
        if observed_state is None:
            errors.append("summary missing `remote-required-checks` row")
        elif observed_state != expected_state:
            errors.append(
                f"summary row `remote-required-checks` must mirror runtime report state `{expected_state}`"
            )

    workflow_path = root / WORKFLOW_PATH
    workflow_payload = _load_json(workflow_path)
    if workflow_payload is None:
        errors.append(f"workflow report missing or invalid: {WORKFLOW_PATH}")
    else:
        for lane in workflow_payload.get("lanes", []):
            if not isinstance(lane, dict):
                continue
            lane_name = str(lane.get("name") or "").strip()
            if not lane_name:
                continue
            head_alignment, latest_head = _workflow_head_alignment(lane, head_commit)
            workflow_row_name = f"workflow:{lane_name}"
            workflow_row_state = lane_states.get(workflow_row_name)
            aggregate_row_state = lane_states.get(lane_name)
            if workflow_row_state is None:
                errors.append(f"summary missing workflow row for `{workflow_row_name}`")
                continue
            if workflow_row_state != str(lane.get("state") or "unknown"):
                errors.append(
                    f"summary workflow row `{workflow_row_name}` must mirror workflow artifact state `{lane.get('state')}`"
                )
            if head_alignment == "historical":
                if workflow_row_state != "historical":
                    errors.append(f"historical workflow row `{workflow_row_name}` must stay `historical` in summary")
                if aggregate_row_state in CURRENT_WORKFLOW_STATUSES:
                    latest_label = latest_head or "<missing>"
                    errors.append(
                        f"summary lane `{lane_name}` must not be rendered as `{aggregate_row_state}` when latest remote run is historical (latest_run.headSha={latest_label}, current HEAD {head_commit})"
                    )

    if errors:
        print("[current-state-summary] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("[current-state-summary] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
