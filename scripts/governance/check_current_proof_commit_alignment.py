#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

sys.dont_write_bytecode = True

from common import current_git_commit, load_governance_json, read_runtime_metadata, repo_root, write_json_artifact


def _load_json_artifact(path) -> dict[str, object] | None:
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


def main() -> int:
    payload = load_governance_json("current-proof-contract.json")
    artifacts = payload.get("artifacts", [])
    root = repo_root()
    head_commit = current_git_commit()
    errors: list[str] = []
    rows: list[dict[str, object]] = []
    workflow_report_cache: dict[str, tuple[dict[str, object] | None, dict[str, dict[str, object]]]] = {}

    if not isinstance(artifacts, list) or not artifacts:
        print("[current-proof-commit-alignment] FAIL")
        print("  - contract must declare a non-empty artifacts list")
        return 1

    for item in artifacts:
        if not isinstance(item, dict):
            errors.append("artifact entry must be an object")
            continue
        name = str(item.get("name") or "<unknown>")
        rel = str(item.get("artifact") or "").strip()
        required = bool(item.get("required"))
        reason = str(item.get("reason") or "").strip()
        if not rel:
            errors.append(f"{name}: missing artifact path")
            continue

        path = root / rel
        row: dict[str, object] = {
            "name": name,
            "artifact": rel,
            "required": required,
            "reason": reason,
            "status": "missing",
            "source_commit": "",
        }
        if not path.is_file():
            if required:
                errors.append(f"{name}: required artifact missing: {rel}")
                row["status"] = "missing_required"
            rows.append(row)
            continue

        metadata = read_runtime_metadata(path)
        if metadata is None:
            errors.append(f"{name}: runtime metadata missing for {rel}")
            row["status"] = "missing_metadata"
            rows.append(row)
            continue

        source_commit = str(metadata.get("source_commit") or "").strip()
        row["source_commit"] = source_commit
        row["created_at"] = str(metadata.get("created_at") or "")
        if not source_commit:
            errors.append(f"{name}: metadata source_commit missing for {rel}")
            row["status"] = "missing_source_commit"
        elif source_commit != head_commit:
            errors.append(
                f"{name}: artifact source_commit {source_commit} does not match current HEAD {head_commit} for {rel}"
            )
            row["status"] = "stale_commit"
        else:
            row["status"] = "aligned"
            artifact_payload = _load_json_artifact(path)
            if artifact_payload is None:
                errors.append(f"{name}: unable to parse JSON artifact payload for {rel}")
                row["status"] = "invalid_json"
                rows.append(row)
                continue
            artifact_status = str(artifact_payload.get("status") or "").strip()
            if artifact_status:
                row["artifact_status"] = artifact_status
            if name == "external-lane-workflows":
                nested_errors: list[str] = []
                for lane in artifact_payload.get("lanes", []):
                    if not isinstance(lane, dict):
                        continue
                    lane_name = str(lane.get("name") or "<unknown>")
                    lane_state = str(lane.get("state") or "")
                    head_alignment, latest_head = _workflow_head_alignment(lane, head_commit)
                    if lane_state == "verified":
                        if not latest_head:
                            nested_errors.append(f"{lane_name}: verified lane is missing latest_run.headSha")
                        elif latest_head != head_commit:
                            nested_errors.append(
                                f"{lane_name}: verified lane headSha {latest_head} does not match current HEAD {head_commit}"
                            )
                        if lane.get("latest_run_matches_current_head") is not True:
                            nested_errors.append(
                                f"{lane_name}: verified lane must set latest_run_matches_current_head=true"
                            )
                    if head_alignment == "historical" and lane_state in {"verified", "blocked", "queued", "in_progress"}:
                        nested_errors.append(
                            f"{lane_name}: non-current remote run must not be reported as `{lane_state}`; use historical semantics instead"
                        )
                if nested_errors:
                    errors.extend(f"{name}: {item}" for item in nested_errors)
                row["workflow_lane_states"] = [
                    {
                        "name": str(lane.get("name") or "<unknown>"),
                        "state": str(lane.get("state") or ""),
                        "latest_run_head": _workflow_head_alignment(lane, head_commit)[1],
                        "head_alignment": _workflow_head_alignment(lane, head_commit)[0],
                        "latest_run_matches_current_head": lane.get("latest_run_matches_current_head"),
                    }
                    for lane in artifact_payload.get("lanes", [])
                    if isinstance(lane, dict)
                ]
            workflow_artifact_rel = str(item.get("workflow_artifact") or "").strip()
            external_lane = str(item.get("external_lane") or "").strip()
            required_statuses = {
                str(value).strip()
                for value in item.get("require_current_head_for_statuses", [])
                if str(value).strip()
            }
            if workflow_artifact_rel and external_lane and artifact_status in required_statuses:
                cached = workflow_report_cache.get(workflow_artifact_rel)
                if cached is None:
                    workflow_path = root / workflow_artifact_rel
                    workflow_payload = _load_json_artifact(workflow_path) if workflow_path.is_file() else None
                    workflow_rows = {
                        str(lane.get("name") or ""): lane
                        for lane in (workflow_payload or {}).get("lanes", [])
                        if isinstance(lane, dict)
                    }
                    cached = (workflow_payload, workflow_rows)
                    workflow_report_cache[workflow_artifact_rel] = cached
                workflow_payload, workflow_rows = cached
                workflow_lane = workflow_rows.get(external_lane)
                if workflow_payload is None:
                    errors.append(
                        f"{name}: status `{artifact_status}` requires workflow proof, but workflow artifact is missing or invalid: {workflow_artifact_rel}"
                    )
                elif workflow_lane is None:
                    errors.append(
                        f"{name}: status `{artifact_status}` requires workflow lane `{external_lane}`, but it is absent from {workflow_artifact_rel}"
                    )
                else:
                    workflow_state = str(workflow_lane.get("state") or "")
                    head_alignment, latest_head = _workflow_head_alignment(workflow_lane, head_commit)
                    row["workflow_lane"] = external_lane
                    row["workflow_state"] = workflow_state
                    row["workflow_latest_head"] = latest_head
                    row["workflow_head_alignment"] = head_alignment
                    if head_alignment != "current":
                        latest_head_label = latest_head or "<missing>"
                        errors.append(
                            f"{name}: status `{artifact_status}` must not report `{artifact_status}` as current proof when workflow lane `{external_lane}` is `{workflow_state or 'missing'}` with head alignment `{head_alignment}` (latest_run.headSha={latest_head_label}, current HEAD {head_commit})"
                        )
        rows.append(row)

    report = {
        "version": 1,
        "status": "pass" if not errors else "fail",
        "current_head": head_commit,
        "artifacts": rows,
        "errors": errors,
    }
    write_json_artifact(
        root / ".runtime-cache" / "reports" / "governance" / "current-proof-commit-alignment.json",
        report,
        source_entrypoint="scripts/governance/check_current_proof_commit_alignment.py",
        verification_scope="current-proof-commit-alignment",
        source_run_id="governance-current-proof-commit-alignment",
        freshness_window_hours=24,
        extra={"report_kind": "current-proof-commit-alignment"},
    )

    if errors:
        print("[current-proof-commit-alignment] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(f"[current-proof-commit-alignment] PASS ({len(rows)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
