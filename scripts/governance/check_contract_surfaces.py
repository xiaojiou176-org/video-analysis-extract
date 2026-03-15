#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import repo_root, write_runtime_metadata

OPENAPI_PATH_RE = re.compile(r"^  (/[^:]+):\s*$", re.MULTILINE)
OPENAPI_METHOD_RE = re.compile(r"^    (get|post|put|delete|patch):\s*$", re.MULTILINE)
WEB_CALL_RE = re.compile(
    r'request(?:Json|Text)<[^>]*>\(\s*"(?P<path>/[^"]+)"\s*,\s*(?P<opts>\{[^)]*?\})?',
    re.DOTALL,
)
WEB_CALL_FALLBACK_RE = re.compile(
    r'request(?:Json|Text)\(\s*"(?P<path>/[^"]+)"\s*,\s*(?P<opts>\{[^)]*?\})?',
    re.DOTALL,
)

VIRTUAL_MCP_PATH_PREFIX = "/api/v1/mcp/virtual/"
IGNORED_OPENAPI_REQUIRED = {
    "/healthz",
}


def _load_openapi_paths(path: Path) -> dict[str, set[str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    results: dict[str, set[str]] = {}
    current_path: str | None = None
    for line in lines:
        matched_path = re.match(r"^  (/[^:]+):\s*$", line)
        if matched_path:
            current_path = matched_path.group(1)
            results.setdefault(current_path, set())
            continue
        matched_method = re.match(r"^    (get|post|put|delete|patch):\s*$", line)
        if matched_method and current_path is not None:
            results.setdefault(current_path, set()).add(matched_method.group(1).upper())
            continue
        if line and not line.startswith(" "):
            current_path = None
    return results


def _extract_web_paths(path: Path) -> dict[str, set[str]]:
    text = path.read_text(encoding="utf-8")
    results: dict[str, set[str]] = {}
    for regex in (WEB_CALL_RE, WEB_CALL_FALLBACK_RE):
        for match in regex.finditer(text):
            route = match.group("path")
            raw_opts = match.group("opts") or ""
            method_match = re.search(r'method:\s*"([A-Za-z]+)"', raw_opts)
            method = method_match.group(1).upper() if method_match else "GET"
            results.setdefault(route, set()).add(method)
    return results


def _extract_mcp_paths(path: Path) -> dict[str, set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, set[str]] = {}
    for tool in payload.get("tools", []):
        details = tool.get("details", {})
        route = str(details.get("path") or "").strip()
        if not route or route.startswith(VIRTUAL_MCP_PATH_PREFIX):
            continue
        method = str(details.get("http_method") or details.get("method") or "GET").upper()
        results.setdefault(route, set()).add(method)
    return results


def _report_missing(
    *,
    label: str,
    used_paths: dict[str, set[str]],
    openapi_paths: dict[str, set[str]],
    enforce_methods: bool,
) -> list[str]:
    errors: list[str] = []
    for route, methods in sorted(used_paths.items()):
        if route not in openapi_paths:
            errors.append(f"{label}: route `{route}` is used but missing from contracts/source/openapi.yaml")
            continue
        if not enforce_methods:
            continue
        for method in sorted(methods):
            if method not in openapi_paths[route]:
                errors.append(
                    f"{label}: route `{route}` uses method `{method}` but openapi only declares "
                    + ", ".join(sorted(openapi_paths[route]))
                )
    return errors


def main() -> int:
    root = repo_root()
    openapi_paths = _load_openapi_paths(root / "contracts" / "source" / "openapi.yaml")
    web_paths = _extract_web_paths(root / "apps" / "web" / "lib" / "api" / "client.ts")
    mcp_paths = _extract_mcp_paths(root / "apps" / "mcp" / "schemas" / "tools.json")
    errors: list[str] = []
    errors.extend(
        _report_missing(
            label="web-contract-surface",
            used_paths=web_paths,
            openapi_paths=openapi_paths,
            enforce_methods=True,
        )
    )
    errors.extend(
        _report_missing(
            label="mcp-contract-surface",
            used_paths=mcp_paths,
            openapi_paths=openapi_paths,
            enforce_methods=False,
        )
    )

    report_path = root / ".runtime-cache" / "reports" / "governance" / "contract-surface-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 1,
        "web_paths": {key: sorted(value) for key, value in sorted(web_paths.items())},
        "mcp_paths": {key: sorted(value) for key, value in sorted(mcp_paths.items())},
        "openapi_paths": {key: sorted(value) for key, value in sorted(openapi_paths.items())},
        "status": "fail" if errors else "pass",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_runtime_metadata(
        report_path,
        source_entrypoint="scripts/governance/check_contract_surfaces.py",
        verification_scope="contract-surfaces",
        source_run_id="governance-contract-surface-report",
        freshness_window_hours=24,
        extra={"report_kind": "contract-surface-report"},
    )

    if errors:
        print("[contract-surfaces] FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1

    print(
        f"[contract-surfaces] PASS (web_paths={len(web_paths)}, mcp_paths={len(mcp_paths)}, openapi_paths={len(openapi_paths)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
