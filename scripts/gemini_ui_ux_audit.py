#!/usr/bin/env python3
"""Gemini-powered semantic UI/UX audit for frontend files.

This hook is designed for pre-push usage so we can keep pre-commit fast.
It reads GEMINI_API_KEY from environment first, then falls back to root .env.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

MODEL = "gemini-3.0-flash"
FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-flash-latest", "gemini-3-flash-preview")
MAX_FILE_CHARS = 50_000
MAX_FILES_PER_REQUEST = 4
VALID_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".sass", ".html"}


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _resolve_api_key(repo_root: Path) -> str | None:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    dotenv_values = _load_env_file(repo_root / ".env")
    return dotenv_values.get("GEMINI_API_KEY", "").strip() or None


def _filter_files(args: list[str], repo_root: Path) -> list[Path]:
    selected: list[Path] = []
    seen: set[Path] = set()
    for name in args:
        candidate = (repo_root / name).resolve()
        try:
            rel = candidate.relative_to(repo_root)
        except ValueError:
            continue
        rel_str = str(rel)
        if not rel_str.startswith(("apps/web/app/", "apps/web/components/")):
            continue
        if candidate.suffix.lower() not in VALID_SUFFIXES:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        selected.append(candidate)
    return sorted(selected, key=str)


def _file_payload(path: Path, repo_root: Path) -> str:
    rel = path.relative_to(repo_root)
    content = path.read_text(encoding="utf-8", errors="ignore")
    snippet = content[:MAX_FILE_CHARS]
    return f"### FILE: {rel}\n```text\n{snippet}\n```\n"


def _build_prompt(batch_payload: str) -> str:
    return (
        "You are a strict senior frontend reviewer.\n"
        "Audit these files for semantic UI/UX quality.\n"
        "Focus on:\n"
        "1) Accessibility: WCAG 2.2 AA basics (alt text, ARIA misuse, keyboard focus hints).\n"
        "2) UX consistency: visual hierarchy, control affordance, interaction clarity.\n"
        "3) Design token discipline: avoid hardcoded colors/spacing when token systems are expected.\n"
        "4) Responsive risks: patterns likely to break on mobile.\n"
        "Only report concrete, actionable issues with file + line.\n"
        "Output format must be plain text lines only:\n"
        "SUMMARY|<one sentence>\n"
        "ISSUE|<error|warning>|<file>|<line>|<a11y|ux|tokens|responsive>|<message>|<suggestion>\n"
        "If no issues, output exactly one line: ISSUE|none\n\n"
        f"{batch_payload}"
    )


def _extract_line_report(raw: str) -> dict[str, Any]:
    summary = ""
    issues: list[dict[str, Any]] = []
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    for line in text.splitlines():
        row = line.strip()
        if not row:
            continue
        if row.startswith("SUMMARY|"):
            summary = row.split("|", 1)[1].strip()
            continue
        if row == "ISSUE|none":
            continue
        if not row.startswith("ISSUE|"):
            continue
        parts = row.split("|", 6)
        if len(parts) != 7:
            continue
        _, severity, file_name, line_no, category, message, suggestion = parts
        if severity not in {"error", "warning"}:
            continue
        try:
            parsed_line = int(line_no)
        except ValueError:
            parsed_line = 1
        issues.append(
            {
                "severity": severity,
                "file": file_name.strip() or "unknown",
                "line": parsed_line,
                "category": category.strip() or "ux",
                "message": message.strip() or "issue",
                "suggestion": suggestion.strip(),
            }
        )
    return {"summary": summary, "issues": issues}


def _candidate_models() -> list[str]:
    deduped: list[str] = []
    for model in (MODEL, *FALLBACK_MODELS):
        if model and model not in deduped:
            deduped.append(model)
    return deduped


def _audit_batch(client: genai.Client, payload: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for model_name in _candidate_models():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=_build_prompt(payload),
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2_000,
                    response_mime_type="text/plain",
                ),
            )
            text = response.text or ""
            if not text:
                raise RuntimeError(f"empty response from Gemini model={model_name}")
            if model_name != MODEL:
                print(
                    f"gemini-ui-ux-audit: fallback model in use ({model_name})",
                    file=sys.stderr,
                )
            return _extract_line_report(text)
        except Exception as exc:  # pragma: no cover - network/sdk defensive path
            last_error = exc
            continue
    raise RuntimeError(f"all Gemini model candidates failed: {last_error}")


def main() -> int:
    repo_root = Path.cwd()
    files = _filter_files(sys.argv[1:], repo_root)
    if not files:
        print("gemini-ui-ux-audit: no frontend files to audit")
        return 0

    api_key = _resolve_api_key(repo_root)
    if not api_key:
        print(
            "gemini-ui-ux-audit: GEMINI_API_KEY not found in environment or .env",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=api_key)
    all_issues: list[dict[str, Any]] = []
    summaries: list[str] = []

    for i in range(0, len(files), MAX_FILES_PER_REQUEST):
        batch = files[i : i + MAX_FILES_PER_REQUEST]
        payload = "\n".join(_file_payload(path, repo_root) for path in batch)
        try:
            parsed = _audit_batch(client, payload)
        except Exception as exc:  # pragma: no cover - defensive for hook runtime
            print(f"gemini-ui-ux-audit: request failed: {exc}", file=sys.stderr)
            return 1
        summary = str(parsed.get("summary", "")).strip()
        if summary:
            summaries.append(summary)
        for issue in parsed.get("issues", []):
            if isinstance(issue, dict):
                all_issues.append(issue)

    blocking = [i for i in all_issues if str(i.get("severity", "")).lower() == "error"]

    if all_issues:
        print("gemini-ui-ux-audit: findings")
        for issue in all_issues:
            file_name = issue.get("file", "unknown")
            line = issue.get("line", "?")
            severity = str(issue.get("severity", "warning")).upper()
            message = issue.get("message", "issue")
            suggestion = issue.get("suggestion", "")
            print(f"- [{severity}] {file_name}:{line} {message}")
            if suggestion:
                print(f"  -> {suggestion}")
    else:
        print("gemini-ui-ux-audit: no issues found")

    if summaries:
        print("gemini-ui-ux-audit: summaries")
        for line in summaries:
            print(f"- {line}")

    if blocking:
        print(
            f"gemini-ui-ux-audit: failed with {len(blocking)} error-level issue(s)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
