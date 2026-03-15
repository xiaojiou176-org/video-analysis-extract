#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export API contract snapshot from FastAPI OpenAPI schema "
            "(routes + method + major schema summary)."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root that contains apps/api/app/main.py (default: current directory).",
    )
    parser.add_argument(
        "--module",
        default="apps.api.app.main",
        help="Python module path that exposes FastAPI app instance (default: apps.api.app.main).",
    )
    parser.add_argument(
        "--app-name",
        default="app",
        help="FastAPI app variable name in module (default: app).",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Output file path. Use '-' for stdout (default: -).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation spaces (default: 2).",
    )
    return parser


def _schema_descriptor(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return {"kind": "unknown"}

    ref = schema.get("$ref")
    if isinstance(ref, str):
        return {"kind": "ref", "ref": ref.split("/")[-1]}

    schema_type = schema.get("type")
    if schema_type == "array":
        return {"kind": "array", "items": _schema_descriptor(schema.get("items", {}))}
    if schema_type == "object":
        props = schema.get("properties")
        summarized_props: dict[str, Any] = {}
        if isinstance(props, dict):
            for key in sorted(props.keys()):
                summarized_props[key] = _schema_descriptor(props[key])
        out: dict[str, Any] = {
            "kind": "object",
            "required": sorted(schema.get("required", []))
            if isinstance(schema.get("required"), list)
            else [],
            "properties": summarized_props,
        }
        additional = schema.get("additionalProperties")
        if isinstance(additional, bool):
            out["additionalProperties"] = additional
        elif isinstance(additional, dict):
            out["additionalProperties"] = _schema_descriptor(additional)
        return out

    for key in ("oneOf", "anyOf", "allOf"):
        value = schema.get(key)
        if isinstance(value, list):
            return {
                "kind": key,
                "items": [_schema_descriptor(item) for item in value],
            }

    out = {
        "kind": schema_type if isinstance(schema_type, str) else "unknown",
    }
    enum_value = schema.get("enum")
    if isinstance(enum_value, list):
        out["enum"] = enum_value
    fmt = schema.get("format")
    if isinstance(fmt, str):
        out["format"] = fmt
    return out


def _summarize_content(content: Any) -> dict[str, Any]:
    if not isinstance(content, dict):
        return {}
    summary: dict[str, Any] = {}
    for content_type in sorted(content.keys()):
        media = content.get(content_type)
        schema = media.get("schema") if isinstance(media, dict) else {}
        summary[content_type] = _schema_descriptor(schema)
    return summary


def _summarize_operation(path: str, method: str, operation: dict[str, Any]) -> dict[str, Any]:
    request_body = operation.get("requestBody")
    request_content = {}
    request_required = False
    if isinstance(request_body, dict):
        request_content = _summarize_content(request_body.get("content"))
        request_required = bool(request_body.get("required", False))

    responses: dict[str, Any] = {}
    operation_responses = operation.get("responses")
    if isinstance(operation_responses, dict):
        for status in sorted(operation_responses.keys()):
            response_item = operation_responses.get(status)
            content_summary = {}
            if isinstance(response_item, dict):
                content_summary = _summarize_content(response_item.get("content"))
            responses[status] = {"content": content_summary}

    return {
        "path": path,
        "method": method.upper(),
        "operationId": operation.get("operationId"),
        "tags": sorted(operation.get("tags", []))
        if isinstance(operation.get("tags"), list)
        else [],
        "deprecated": bool(operation.get("deprecated", False)),
        "request": {
            "required": request_required,
            "content": request_content,
        },
        "responses": responses,
    }


def _summarize_components(openapi_doc: dict[str, Any]) -> dict[str, Any]:
    components = openapi_doc.get("components")
    if not isinstance(components, dict):
        return {}
    schemas = components.get("schemas")
    if not isinstance(schemas, dict):
        return {}

    output: dict[str, Any] = {}
    for name in sorted(schemas.keys()):
        output[name] = _schema_descriptor(schemas[name])
    return output


def _apply_default_env() -> None:
    # FastAPI app settings require these env vars at import time.
    defaults = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "TEMPORAL_TARGET_HOST": "127.0.0.1:7233",
        "TEMPORAL_NAMESPACE": "default",
        "TEMPORAL_TASK_QUEUE": "video-analysis-worker",
        "SQLITE_STATE_PATH": "/tmp/video-digestor-contract-export.db",
        "NOTIFICATION_ENABLED": "0",
        "UI_AUDIT_GEMINI_ENABLED": "0",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def _load_openapi(
    repo_root: Path,
    module_name: str,
    app_name: str,
) -> dict[str, Any]:
    original_cwd = Path.cwd()
    os.chdir(repo_root)
    sys.path.insert(0, str(repo_root))
    importlib.invalidate_caches()
    _apply_default_env()

    try:
        module = importlib.import_module(module_name)
        app = getattr(module, app_name)
        return app.openapi()
    finally:
        os.chdir(original_cwd)


def _build_contract(openapi_doc: dict[str, Any]) -> dict[str, Any]:
    paths = openapi_doc.get("paths")
    operations: list[dict[str, Any]] = []
    if isinstance(paths, dict):
        for path in sorted(paths.keys()):
            path_item = paths[path]
            if not isinstance(path_item, dict):
                continue
            for method in sorted(path_item.keys()):
                if method.lower() not in HTTP_METHODS:
                    continue
                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue
                operations.append(
                    _summarize_operation(path=path, method=method, operation=operation)
                )

    info = openapi_doc.get("info", {}) if isinstance(openapi_doc.get("info"), dict) else {}

    return {
        "contract_version": 1,
        "openapi": openapi_doc.get("openapi"),
        "app": {
            "title": info.get("title"),
            "version": info.get("version"),
        },
        "operations": operations,
        "schemas": _summarize_components(openapi_doc),
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"[contract-export] repo root not found: {repo_root}", file=sys.stderr)
        return 2

    try:
        openapi_doc = _load_openapi(
            repo_root=repo_root,
            module_name=args.module,
            app_name=args.app_name,
        )
        contract = _build_contract(openapi_doc)
    except Exception as exc:
        print(f"[contract-export] failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(contract, ensure_ascii=False, indent=args.indent, sort_keys=True)
    if args.output == "-":
        print(rendered)
        return 0

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    print(f"[contract-export] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
