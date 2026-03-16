#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts" / "governance") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts" / "governance"))

from common import rel_path, write_json_artifact

ALLOWED_ROOTS = {
    ROOT / ".runtime-cache",
    ROOT / ".git",
    ROOT / ".venv",
    ROOT / "venv",
}
DIR_MARKERS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
FILE_SUFFIXES = {".pyc", ".pyo"}


def _is_within_allowed_root(path: Path) -> bool:
    for allowed in ALLOWED_ROOTS:
        try:
            path.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


def _collect_residue() -> tuple[list[str], list[str]]:
    residue_dirs: list[str] = []
    residue_files: list[str] = []

    for path in ROOT.rglob("*"):
        if _is_within_allowed_root(path):
            continue
        if path.is_dir() and path.name in DIR_MARKERS:
            residue_dirs.append(rel_path(path))
            continue
        if path.is_file() and path.suffix in FILE_SUFFIXES:
            residue_files.append(rel_path(path))

    return sorted(residue_dirs), sorted(residue_files)


def _remove_path(relative: str) -> None:
    target = ROOT / relative
    if target.is_dir():
        shutil.rmtree(target)
        return
    if target.exists():
        target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect or clean source-tree runtime residue that leaked outside .runtime-cache."
    )
    parser.add_argument("--apply", action="store_true", help="Delete detected residue paths.")
    parser.add_argument(
        "--write-report",
        default=".runtime-cache/reports/governance/source-runtime-residue.json",
        help="Runtime report path.",
    )
    args = parser.parse_args()

    residue_dirs, residue_files = _collect_residue()
    if args.apply:
        for relative in residue_files:
            _remove_path(relative)
        for relative in residue_dirs:
            _remove_path(relative)
        residue_dirs, residue_files = _collect_residue()

    report = {
        "version": 1,
        "status": "fail" if residue_dirs or residue_files else "pass",
        "directory_count": len(residue_dirs),
        "file_count": len(residue_files),
        "directories": residue_dirs,
        "files": residue_files,
        "mode": "apply" if args.apply else "audit",
    }
    write_json_artifact(
        ROOT / args.write_report,
        report,
        source_entrypoint="scripts/runtime/clean_source_runtime_residue.py",
        verification_scope="source-runtime-residue",
        source_run_id="source-runtime-residue-cleanup",
        freshness_window_hours=24,
        extra={"report_kind": "source-runtime-residue"},
    )

    if residue_dirs or residue_files:
        print("[source-runtime-residue] FAIL")
        for relative in residue_dirs:
            print(f"  - residue directory: {relative}")
        for relative in residue_files:
            print(f"  - residue file: {relative}")
        return 1

    print("[source-runtime-residue] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
