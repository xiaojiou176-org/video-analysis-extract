from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _script_path() -> Path:
    return _repo_root() / "scripts" / "release" / "generate_release_prechecks.py"


def _run_prechecks(tmp_path: Path, *extra_args: str) -> dict[str, object]:
    output_path = tmp_path / "prechecks.json"
    cmd = [
        sys.executable,
        str(_script_path()),
        "--repo-root",
        str(_repo_root()),
        "--output",
        str(output_path),
        *extra_args,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_release_prechecks_include_observability_checks_by_default(tmp_path: Path) -> None:
    payload = _run_prechecks(tmp_path)
    checks = payload.get("checks")
    assert isinstance(checks, list)

    checks_by_name = {item["name"]: item for item in checks if isinstance(item, dict)}
    assert "api_red_metrics_minimum" in checks_by_name
    assert "api_trace_header_echo" in checks_by_name
    assert "slo_thresholds_documented" in checks_by_name

    assert checks_by_name["api_red_metrics_minimum"]["required"] is True
    assert checks_by_name["api_trace_header_echo"]["required"] is True
    assert checks_by_name["slo_thresholds_documented"]["required"] is True


def test_release_prechecks_can_skip_runtime_observability_checks(tmp_path: Path) -> None:
    payload = _run_prechecks(tmp_path, "--skip-observability-checks")
    checks = payload.get("checks")
    assert isinstance(checks, list)

    check_names = {item["name"] for item in checks if isinstance(item, dict)}
    assert "api_red_metrics_minimum" not in check_names
    assert "api_trace_header_echo" not in check_names
    assert "slo_thresholds_documented" in check_names
