#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

BUTTON_PATTERN = re.compile(r"<button\b[^>]*>(?P<label>.*?)</button>", re.IGNORECASE | re.DOTALL)
PYTEST_BUTTON_PATTERN = re.compile(
    r"""get_by_role\(\s*["']button["']\s*,\s*name\s*=\s*["'](?P<label>[^"']+)["']\s*\)""",
    re.DOTALL,
)
RTL_BUTTON_PATTERN = re.compile(
    r"""getByRole\(\s*["']button["']\s*,\s*\{\s*name\s*:\s*["'](?P<label>[^"']+)["']\s*\}\s*\)""",
    re.DOTALL,
)


def normalize_label(raw: str) -> str:
    cleaned = re.sub(r"{[^{}]*}", " ", raw)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def collect_button_labels(app_root: Path) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {}
    for file_path in sorted(app_root.glob("**/*.tsx")):
        content = file_path.read_text(encoding="utf-8")
        for match in BUTTON_PATTERN.finditer(content):
            label = normalize_label(match.group("label"))
            if not label:
                continue
            labels.setdefault(label, set()).add(str(file_path))
    return labels


def collect_pytest_e2e_labels(e2e_root: Path) -> set[str]:
    labels: set[str] = set()
    for file_path in sorted(e2e_root.glob("*.py")):
        content = file_path.read_text(encoding="utf-8")
        for match in PYTEST_BUTTON_PATTERN.finditer(content):
            label = normalize_label(match.group("label"))
            if label:
                labels.add(label)
    return labels


def collect_rtl_unit_labels(unit_test_root: Path) -> set[str]:
    labels: set[str] = set()
    for file_path in sorted(unit_test_root.rglob("*")):
        if not file_path.is_file():
            continue
        filename = file_path.name
        if not filename.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
            continue
        content = file_path.read_text(encoding="utf-8")
        for match in RTL_BUTTON_PATTERN.finditer(content):
            label = normalize_label(match.group("label"))
            if label:
                labels.add(label)
    return labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check button text coverage between apps/web/app/**/*.tsx and "
            "apps/web/tests/e2e/*.py by matching get_by_role('button', name=...)."
        )
    )
    parser.add_argument(
        "--app-root",
        type=Path,
        default=Path("apps/web/app"),
        help="Root directory containing app tsx files. Default: apps/web/app",
    )
    parser.add_argument(
        "--e2e-root",
        type=Path,
        default=Path("apps/web/tests/e2e"),
        help="Root directory containing playwright pytest files. Default: apps/web/tests/e2e",
    )
    parser.add_argument(
        "--unit-test-root",
        type=Path,
        default=Path("apps/web/__tests__"),
        help="Root directory containing web unit tests. Default: apps/web/__tests__",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Minimum button coverage ratio [0,1]. Default: 1.0",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.threshold <= 1:
        raise SystemExit("threshold must be in [0,1]")
    if not args.app_root.is_dir():
        raise SystemExit(f"app root not found: {args.app_root}")
    if not args.e2e_root.is_dir():
        raise SystemExit(f"e2e root not found: {args.e2e_root}")
    if not args.unit_test_root.is_dir():
        raise SystemExit(f"unit test root not found: {args.unit_test_root}")

    app_labels = collect_button_labels(args.app_root)
    e2e_labels = collect_pytest_e2e_labels(args.e2e_root)
    unit_labels = collect_rtl_unit_labels(args.unit_test_root)
    covered_labels = e2e_labels | unit_labels
    total = len(app_labels)
    covered = sorted(label for label in app_labels if label in covered_labels)
    uncovered = sorted(label for label in app_labels if label not in covered_labels)
    ratio = (len(covered) / total) if total > 0 else 1.0

    print(
        "web button coverage: "
        f"covered={len(covered)} total={total} ratio={ratio:.2%} threshold={args.threshold:.2%} "
        f"(e2e_labels={len(e2e_labels)} unit_labels={len(unit_labels)})"
    )
    if uncovered:
        print("uncovered buttons:")
        for label in uncovered:
            files = ", ".join(sorted(app_labels[label]))
            print(f"  - {label} ({files})")

    if ratio < args.threshold:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
