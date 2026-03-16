#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "runtime" / "prune_runtime_cache.py"),
        "--assert-clean",
        "--subdir",
        "run",
        "--subdir",
        "logs",
        "--subdir",
        "reports",
        "--subdir",
        "evidence",
        "--subdir",
        "tmp",
    ]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
