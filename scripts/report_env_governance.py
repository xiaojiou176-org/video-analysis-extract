#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FAIL_ON = 1
EXIT_INPUT_ERROR = 2
EXIT_RUNTIME_ERROR = 3

CONTRACT_FIELDS = {
    "name",
    "scope",
    "required",
    "secret",
    "default",
    "consumer",
    "description",
}

IGNORE_REFS = {
    "BASH_SOURCE",
    "ENV_PROFILE",
    "GITHUB_ACTOR",
    "HOME",
    "PATH",
    "PIPELINE_STEPS",
    "PYTEST_XDIST_WORKER",
    "PWD",
    "PYTHONPATH",
    "WEB_E2E_BROWSER",
}

FAIL_ON_TYPES = {"residual_refs", "doc_drift", "delete_candidates"}

PY_GETENV_RE = re.compile(r'os\.getenv\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
PY_ENV_RE = re.compile(r'os\.environ\[\s*["\']([A-Z][A-Z0-9_]*)["\']\s*\]')
PY_ENV_GET_RE = re.compile(r'os\.environ\.get\(\s*["\']([A-Z][A-Z0-9_]*)["\']')
TS_PROCESS_ENV_RE = re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)")
SH_DEFAULT_ENV_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)[:-][^}]*\}")
ENV_FILE_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)\s*$")
ENV_EXAMPLE_EXPORT_RE = re.compile(
    r"^\s*(?:#\s*)?(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE
)
DOC_ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*[A-Z0-9])\s*=\s*", re.MULTILINE)
DOC_BACKTICK_RE = re.compile(r"`([A-Z][A-Z0-9_]*[A-Z0-9])`")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _resolve_docs(root: Path, docs: list[str]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for item in docs:
        for token in item.split(","):
            cleaned = token.strip()
            if not cleaned:
                continue
            path = _resolve_path(root, cleaned)
            if path in seen:
                continue
            seen.add(path)
            resolved.append(path)
    return resolved


def _resolve_fail_on(raw: str) -> set[str]:
    values = {token.strip() for token in raw.split(",") if token.strip()}
    if not values:
        return {"residual_refs", "doc_drift"}
    unknown = values - FAIL_ON_TYPES
    if unknown:
        raise ValueError(f"unknown --fail-on values: {', '.join(sorted(unknown))}")
    return values


def _load_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"env contract must be a JSON object: {path}")
    variables = payload.get("variables")
    if not isinstance(variables, list):
        raise ValueError(f"env contract must contain 'variables' list: {path}")

    for idx, item in enumerate(variables):
        if not isinstance(item, dict):
            raise ValueError(f"variables[{idx}] must be object: {path}")
        missing = CONTRACT_FIELDS - set(item.keys())
        if missing:
            raise ValueError(f"variables[{idx}] missing fields {sorted(missing)}: {path}")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ValueError(f"variables[{idx}] invalid name {name!r}: {path}")
        if not isinstance(item.get("required"), bool):
            raise ValueError(f"variables[{idx}] required must be bool: {path}")
        if not isinstance(item.get("secret"), bool):
            raise ValueError(f"variables[{idx}] secret must be bool: {path}")
        consumers = item.get("consumer")
        if not isinstance(consumers, list) or any(not isinstance(x, str) for x in consumers):
            raise ValueError(f"variables[{idx}] consumer must be list[str]: {path}")

    return payload


def _resolve_consumers(root: Path, pattern: str) -> list[Path]:
    if any(ch in pattern for ch in ("*", "?", "[")):
        return [Path(p) for p in glob.glob(str(root / pattern), recursive=False)]
    return [root / pattern]


def _file_contains_name(path: Path, name: str) -> bool:
    if not path.is_file():
        return False
    content = path.read_text(encoding="utf-8", errors="ignore")
    return re.search(rf"\b{re.escape(name)}\b", content) is not None


def _collect_delete_candidates(root: Path, variables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in variables:
        name = item["name"]
        consumers = item.get("consumer", [])
        found = False
        checked_paths: list[str] = []
        for consumer in consumers:
            for path in _resolve_consumers(root, consumer):
                checked_paths.append(str(path.relative_to(root)) if path.exists() else str(path))
                if _file_contains_name(path, name):
                    found = True
                    break
            if found:
                break
        if not found:
            candidates.append(
                {
                    "name": name,
                    "scope": item.get("scope"),
                    "consumers": consumers,
                    "checked_paths": checked_paths,
                    "reason": "declared consumer paths do not contain variable reference",
                }
            )
    return candidates


def _iter_files(root: Path, include_paths: list[str] | None = None) -> list[Path]:
    files: list[Path] = []
    bases = include_paths[:] if include_paths else ["apps", "scripts"]
    for base in bases:
        base_dir = root / base
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*"):
            if not path.is_file():
                continue
            if any(
                part in {".git", "node_modules", "__pycache__"} or part.startswith(".next")
                for part in path.parts
            ):
                continue
            if "tests" in path.parts or "__tests__" in path.parts:
                continue
            if path.suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".sh"}:
                files.append(path)
    return files


def _collect_code_references(
    root: Path, include_paths: list[str] | None = None
) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for file_path in _iter_files(root, include_paths=include_paths):
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        found: set[str] = set()
        if file_path.suffix == ".py":
            found.update(PY_GETENV_RE.findall(content))
            found.update(PY_ENV_RE.findall(content))
            found.update(PY_ENV_GET_RE.findall(content))
        if file_path.suffix in {".ts", ".tsx", ".js", ".mjs"}:
            found.update(TS_PROCESS_ENV_RE.findall(content))
        if file_path.suffix == ".sh":
            found.update(SH_DEFAULT_ENV_RE.findall(content))

        filtered = {item for item in found if item not in IGNORE_REFS}
        if filtered:
            refs[str(file_path.relative_to(root))] = filtered
    return refs


def _parse_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def _load_env_file_items(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    items: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        matched = ENV_FILE_LINE_RE.match(line)
        if not matched:
            continue
        key, raw_value = matched.group(1), matched.group(2)
        items[key] = _parse_env_value(raw_value)
    return items


def _load_env_example_vars(path: Path) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(f"env example not found: {path}")
    content = path.read_text(encoding="utf-8", errors="ignore")
    return set(ENV_EXAMPLE_EXPORT_RE.findall(content))


def _collect_doc_refs(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    content = path.read_text(encoding="utf-8", errors="ignore")
    names = set(DOC_ASSIGN_RE.findall(content)) | set(DOC_BACKTICK_RE.findall(content))
    return {name for name in names if name not in IGNORE_REFS and not name.endswith("_")}


def _collect_residual_refs(
    contract_names: set[str],
    code_refs: dict[str, set[str]],
    env_items: dict[str, str],
) -> dict[str, Any]:
    code_rows: list[dict[str, Any]] = []
    for file_path, refs in sorted(code_refs.items()):
        missing = sorted(name for name in refs if name not in contract_names)
        if missing:
            code_rows.append({"file": file_path, "names": missing})

    env_missing = sorted(
        name for name in env_items if name not in contract_names and name not in IGNORE_REFS
    )

    return {
        "unregistered_code_refs": code_rows,
        "unregistered_env_file_keys": env_missing,
    }


def _collect_doc_drift(
    required_vars: set[str],
    contract_names: set[str],
    env_example_vars: set[str],
    docs: list[Path],
    root: Path,
) -> dict[str, Any]:
    doc_refs_by_file: list[dict[str, Any]] = []
    all_doc_refs: set[str] = set()
    missing_docs: list[str] = []

    for path in docs:
        if not path.is_file():
            missing_docs.append(
                str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
            )
            continue
        refs = sorted(_collect_doc_refs(path))
        all_doc_refs.update(refs)
        if refs:
            rel_path = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
            doc_refs_by_file.append({"file": rel_path, "names": refs})

    missing_required_in_env_example = sorted(
        name for name in required_vars if name not in env_example_vars
    )
    missing_required_in_docs = sorted(name for name in required_vars if name not in all_doc_refs)
    stale_doc_refs = sorted(name for name in all_doc_refs if name not in contract_names)

    return {
        "missing_required_in_env_example": missing_required_in_env_example,
        "missing_required_in_docs": missing_required_in_docs,
        "stale_doc_refs": stale_doc_refs,
        "doc_refs_by_file": doc_refs_by_file,
        "missing_docs": missing_docs,
    }


def _has_doc_drift(doc_drift: dict[str, Any]) -> bool:
    return bool(
        doc_drift["missing_required_in_env_example"]
        or doc_drift["missing_required_in_docs"]
        or doc_drift["stale_doc_refs"]
    )


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    delete_candidates = report["delete_candidates"]
    residual_refs = report["residual_refs"]
    doc_drift = report["doc_drift"]

    lines: list[str] = []
    lines.append("# Env Governance Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- contract: `{summary['contract']}`")
    lines.append(f"- fail_on: `{', '.join(summary['fail_on'])}`")
    lines.append(f"- delete_candidates: `{summary['delete_candidate_count']}`")
    lines.append(f"- residual_refs: `{summary['residual_ref_count']}`")
    lines.append(f"- doc_drift_items: `{summary['doc_drift_count']}`")
    lines.append(f"- should_fail: `{summary['should_fail']}`")
    lines.append("")

    lines.append("## Delete Candidates")
    lines.append("")
    if not delete_candidates:
        lines.append("- none")
    else:
        for row in delete_candidates:
            lines.append(f"- `{row['name']}` ({row['scope']})")
            lines.append(f"  - reason: {row['reason']}")
            lines.append(
                f"  - consumers: {', '.join(row['consumers']) if row['consumers'] else '-'}"
            )
    lines.append("")

    lines.append("## Residual Refs")
    lines.append("")
    if (
        not residual_refs["unregistered_code_refs"]
        and not residual_refs["unregistered_env_file_keys"]
    ):
        lines.append("- none")
    else:
        for row in residual_refs["unregistered_code_refs"]:
            lines.append(f"- `{row['file']}`: {', '.join(row['names'])}")
        if residual_refs["unregistered_env_file_keys"]:
            lines.append(
                "- env file keys: " + ", ".join(residual_refs["unregistered_env_file_keys"])
            )
    lines.append("")

    lines.append("## Doc Drift")
    lines.append("")
    if not _has_doc_drift(doc_drift):
        lines.append("- none")
    else:
        if doc_drift["missing_required_in_env_example"]:
            lines.append(
                "- missing in .env.example: "
                + ", ".join(doc_drift["missing_required_in_env_example"])
            )
        if doc_drift["missing_required_in_docs"]:
            lines.append("- missing in docs: " + ", ".join(doc_drift["missing_required_in_docs"]))
        if doc_drift["stale_doc_refs"]:
            lines.append("- stale doc refs: " + ", ".join(doc_drift["stale_doc_refs"]))

    return "\n".join(lines) + "\n"


def _build_report(
    root: Path,
    contract_path: Path,
    env_file_path: Path,
    env_example_path: Path,
    docs: list[Path],
    fail_on: set[str],
) -> dict[str, Any]:
    payload = _load_contract(contract_path)
    variables = payload["variables"]
    contract_names = {item["name"] for item in variables}
    required_vars = {item["name"] for item in variables if item["required"]}

    delete_candidates = _collect_delete_candidates(root, variables)

    code_refs = _collect_code_references(root)
    env_items = _load_env_file_items(env_file_path)
    residual_refs = _collect_residual_refs(contract_names, code_refs, env_items)

    env_example_vars = _load_env_example_vars(env_example_path)
    doc_drift = _collect_doc_drift(
        required_vars=required_vars,
        contract_names=contract_names,
        env_example_vars=env_example_vars,
        docs=docs,
        root=root,
    )

    hits = {
        "delete_candidates": bool(delete_candidates),
        "residual_refs": bool(
            residual_refs["unregistered_code_refs"] or residual_refs["unregistered_env_file_keys"]
        ),
        "doc_drift": _has_doc_drift(doc_drift),
    }

    fail_reasons = sorted(name for name in fail_on if hits[name])
    summary = {
        "contract": str(contract_path.relative_to(root))
        if contract_path.is_relative_to(root)
        else str(contract_path),
        "fail_on": sorted(fail_on),
        "delete_candidate_count": len(delete_candidates),
        "residual_ref_count": len(residual_refs["unregistered_code_refs"])
        + len(residual_refs["unregistered_env_file_keys"]),
        "doc_drift_count": len(doc_drift["missing_required_in_env_example"])
        + len(doc_drift["missing_required_in_docs"])
        + len(doc_drift["stale_doc_refs"]),
        "should_fail": bool(fail_reasons),
        "fail_reasons": fail_reasons,
    }

    return {
        "summary": summary,
        "delete_candidates": delete_candidates,
        "residual_refs": residual_refs,
        "doc_drift": doc_drift,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate env-governance report: delete candidates, residual refs, and doc drift."
    )
    parser.add_argument("--contract", default="infra/config/env.contract.json")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--env-example", default=".env.example")
    parser.add_argument(
        "--docs",
        nargs="+",
        default=[
            "ENVIRONMENT.md",
            "README.md",
            "docs/start-here.md",
            "docs/runbook-local.md",
            "docs/testing.md",
        ],
    )
    parser.add_argument("--json-out", default="")
    parser.add_argument("--md-out", default="")
    parser.add_argument("--fail-on", default="residual_refs,doc_drift")
    parser.add_argument("--repo-root", default="")

    args = parser.parse_args(argv)

    try:
        root = _resolve_path(Path.cwd(), args.repo_root) if args.repo_root.strip() else _repo_root()
        if not root.is_dir():
            raise FileNotFoundError(f"repo root not found: {root}")

        contract_path = _resolve_path(root, args.contract)
        env_file_path = _resolve_path(root, args.env_file)
        env_example_path = _resolve_path(root, args.env_example)
        docs = _resolve_docs(root, args.docs)
        fail_on = _resolve_fail_on(args.fail_on)

        if not contract_path.is_file():
            raise FileNotFoundError(f"contract not found: {contract_path}")

        report = _build_report(
            root=root,
            contract_path=contract_path,
            env_file_path=env_file_path,
            env_example_path=env_example_path,
            docs=docs,
            fail_on=fail_on,
        )

        markdown = _render_markdown(report)

        if args.json_out.strip():
            json_out_path = _resolve_path(root, args.json_out)
            json_out_path.parent.mkdir(parents=True, exist_ok=True)
            json_out_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

        if args.md_out.strip():
            md_out_path = _resolve_path(root, args.md_out)
            md_out_path.parent.mkdir(parents=True, exist_ok=True)
            md_out_path.write_text(markdown, encoding="utf-8")

        print(
            "[env-governance] "
            f"delete_candidates={report['summary']['delete_candidate_count']} "
            f"residual_refs={report['summary']['residual_ref_count']} "
            f"doc_drift={report['summary']['doc_drift_count']} "
            f"fail_reasons={','.join(report['summary']['fail_reasons']) or '-'}"
        )

        return EXIT_FAIL_ON if report["summary"]["should_fail"] else EXIT_OK
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[env-governance] input error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except Exception as exc:  # pragma: no cover
        print(f"[env-governance] runtime error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


if __name__ == "__main__":
    raise SystemExit(run())
