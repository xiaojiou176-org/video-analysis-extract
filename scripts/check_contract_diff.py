#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare API contract snapshots (base vs head), "
            "report breaking changes, and return non-zero on breaking changes."
        )
    )
    parser.add_argument("--base", required=True, help="Base contract JSON path.")
    parser.add_argument("--head", required=True, help="Head contract JSON path.")
    parser.add_argument(
        "--report",
        default="-",
        help="Markdown report output path. Use '-' for stdout (default: -).",
    )
    parser.add_argument(
        "--json-report",
        default="",
        help="Optional JSON report output path.",
    )
    return parser


def _load_contract(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"contract is not an object: {path}")
    return payload


def _operation_key(operation: dict[str, Any]) -> tuple[str, str]:
    method = str(operation.get("method", "")).upper()
    path = str(operation.get("path", ""))
    return method, path


def _index_operations(contract: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    operations = contract.get("operations")
    if not isinstance(operations, list):
        return {}

    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for item in operations:
        if isinstance(item, dict):
            indexed[_operation_key(item)] = item
    return indexed


def _status_sort_key(status: str) -> tuple[int, str]:
    if status.isdigit():
        return int(status), status
    return 999, status


def _get_schema_fingerprints_by_content_type(content: Any) -> dict[str, str]:
    if not isinstance(content, dict) or not content:
        return {}

    fingerprints: dict[str, str] = {}
    for content_type, schema in content.items():
        fingerprints[str(content_type)] = json.dumps(schema, ensure_ascii=False, sort_keys=True)
    return fingerprints


def _is_success_status(status: str) -> bool:
    return bool(re.match(r"^2\d\d$", status))


def _compare_operation(
    key: tuple[str, str],
    base_op: dict[str, Any],
    head_op: dict[str, Any],
    breaking: list[str],
    non_breaking: list[str],
) -> None:
    method, path = key
    title = f"{method} {path}"

    base_request = base_op.get("request", {}) if isinstance(base_op.get("request"), dict) else {}
    head_request = head_op.get("request", {}) if isinstance(head_op.get("request"), dict) else {}

    base_req_required = bool(base_request.get("required", False))
    head_req_required = bool(head_request.get("required", False))
    base_req_content = base_request.get("content")
    head_req_content = head_request.get("content")

    if (not base_req_required) and head_req_required:
        breaking.append(f"{title}: request body became required")

    base_req_by_ct = _get_schema_fingerprints_by_content_type(base_req_content)
    head_req_by_ct = _get_schema_fingerprints_by_content_type(head_req_content)
    for content_type, base_fp in sorted(base_req_by_ct.items()):
        head_fp = head_req_by_ct.get(content_type)
        if head_fp is None:
            breaking.append(f"{title}: request content type removed ({content_type})")
            continue
        if base_fp != head_fp:
            breaking.append(f"{title}: request schema changed for content type {content_type}")

    base_responses = (
        base_op.get("responses", {}) if isinstance(base_op.get("responses"), dict) else {}
    )
    head_responses = (
        head_op.get("responses", {}) if isinstance(head_op.get("responses"), dict) else {}
    )

    for status in sorted(base_responses.keys(), key=_status_sort_key):
        if status not in head_responses:
            breaking.append(f"{title}: response status removed ({status})")
            continue
        base_content = base_responses.get(status, {}).get("content")
        head_content = head_responses.get(status, {}).get("content")
        base_by_ct = _get_schema_fingerprints_by_content_type(base_content)
        head_by_ct = _get_schema_fingerprints_by_content_type(head_content)
        for content_type, base_fp in sorted(base_by_ct.items()):
            head_fp = head_by_ct.get(content_type)
            if head_fp is None:
                breaking.append(
                    f"{title}: response content type removed for status {status} ({content_type})"
                )
                continue
            if base_fp != head_fp:
                breaking.append(
                    f"{title}: response schema changed for status {status} ({content_type})"
                )

    base_success = {s for s in base_responses if _is_success_status(s)}
    head_success = {s for s in head_responses if _is_success_status(s)}
    if base_success and not (base_success & head_success):
        breaking.append(f"{title}: all previous success statuses removed")

    added_statuses = sorted(
        set(head_responses.keys()) - set(base_responses.keys()), key=_status_sort_key
    )
    if added_statuses:
        non_breaking.append(f"{title}: added response statuses {', '.join(added_statuses)}")


def _build_report(
    breaking: list[str],
    non_breaking: list[str],
    base_ops_count: int,
    head_ops_count: int,
) -> str:
    lines = [
        "# API Contract Diff Report",
        "",
        f"- Base operations: {base_ops_count}",
        f"- Head operations: {head_ops_count}",
        f"- Breaking changes: {len(breaking)}",
        f"- Non-breaking changes: {len(non_breaking)}",
        "",
        "## Breaking Changes",
    ]
    if breaking:
        lines.extend([f"- {item}" for item in breaking])
    else:
        lines.append("- None")

    lines.extend(["", "## Non-Breaking Changes"])
    if non_breaking:
        lines.extend([f"- {item}" for item in non_breaking])
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _write_output(path_arg: str, content: str) -> None:
    if path_arg == "-":
        print(content, end="")
        return

    path = Path(path_arg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        base_contract = _load_contract(args.base)
        head_contract = _load_contract(args.head)
    except Exception as exc:
        print(f"[contract-diff] failed to load contracts: {exc}", file=sys.stderr)
        return 2

    base_ops = _index_operations(base_contract)
    head_ops = _index_operations(head_contract)

    breaking: list[str] = []
    non_breaking: list[str] = []

    for key in sorted(base_ops.keys()):
        if key not in head_ops:
            method, path = key
            breaking.append(f"{method} {path}: endpoint removed")
            continue
        _compare_operation(key, base_ops[key], head_ops[key], breaking, non_breaking)

    for key in sorted(head_ops.keys()):
        if key not in base_ops:
            method, path = key
            non_breaking.append(f"{method} {path}: endpoint added")

    report = _build_report(
        breaking=breaking,
        non_breaking=non_breaking,
        base_ops_count=len(base_ops),
        head_ops_count=len(head_ops),
    )
    _write_output(args.report, report)

    if args.json_report:
        payload = {
            "base_operations": len(base_ops),
            "head_operations": len(head_ops),
            "breaking": breaking,
            "non_breaking": non_breaking,
        }
        json_path = Path(args.json_report)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if breaking:
        print("[contract-diff] breaking changes detected", file=sys.stderr)
        return 1

    print("[contract-diff] no breaking changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
