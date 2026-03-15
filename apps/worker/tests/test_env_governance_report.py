from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[3] / "scripts" / "governance" / "report_env_governance.py"


def _write_contract(path: Path, variables: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "variables": variables}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_report(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(_script_path()),
        "--repo-root",
        str(tmp_path),
        "--contract",
        "infra/config/env.contract.json",
        "--env-file",
        ".env",
        "--env-example",
        ".env.example",
        "--docs",
        "docs/testing.md",
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_residual_refs_hit_and_fail_on_returns_1(tmp_path: Path) -> None:
    (tmp_path / "apps").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)

    _write_contract(
        tmp_path / "infra/config/env.contract.json",
        [
            {
                "name": "KNOWN_VAR",
                "scope": "runtime",
                "required": False,
                "secret": False,
                "default": None,
                "consumer": ["apps/runtime.py"],
                "description": "known var",
            }
        ],
    )

    (tmp_path / "apps/runtime.py").write_text(
        'import os\nos.getenv("DATABASE_URL")\n', encoding="utf-8"
    )
    (tmp_path / ".env.example").write_text("KNOWN_VAR=1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("KNOWN_VAR=1\n", encoding="utf-8")
    (tmp_path / "docs/testing.md").write_text("`KNOWN_VAR`\n", encoding="utf-8")

    out_json = tmp_path / ".runtime-cache/reports/governance/report.json"
    proc = _run_report(
        tmp_path,
        "--fail-on",
        "residual_refs",
        "--json-out",
        str(out_json),
    )

    assert proc.returncode == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["residual_refs"]["unregistered_code_refs"]


def test_delete_candidates_hit_but_not_in_fail_on_returns_0(tmp_path: Path) -> None:
    (tmp_path / "apps").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)

    _write_contract(
        tmp_path / "infra/config/env.contract.json",
        [
            {
                "name": "OLD_VAR",
                "scope": "runtime",
                "required": False,
                "secret": False,
                "default": None,
                "consumer": ["apps/runtime.py"],
                "description": "stale var",
            }
        ],
    )

    (tmp_path / "apps/runtime.py").write_text("print('no env refs here')\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("OLD_VAR=1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("OLD_VAR=1\n", encoding="utf-8")
    (tmp_path / "docs/testing.md").write_text("`OLD_VAR`\n", encoding="utf-8")

    out_json = tmp_path / ".runtime-cache/reports/governance/report.json"
    proc = _run_report(
        tmp_path,
        "--fail-on",
        "residual_refs,doc_drift",
        "--json-out",
        str(out_json),
    )

    assert proc.returncode == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(payload["delete_candidates"]) == 1
    assert payload["summary"]["should_fail"] is False


def test_doc_drift_hit_and_fail_on_returns_1(tmp_path: Path) -> None:
    (tmp_path / "apps").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)

    _write_contract(
        tmp_path / "infra/config/env.contract.json",
        [
            {
                "name": "SQLITE_PATH",
                "scope": "runtime",
                "required": True,
                "secret": False,
                "default": None,
                "consumer": ["apps/runtime.py"],
                "description": "required var",
            }
        ],
    )

    (tmp_path / "apps/runtime.py").write_text(
        'import os\nos.getenv("SQLITE_PATH")\n',
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("SQLITE_PATH=ok\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SQLITE_PATH=ok\n", encoding="utf-8")
    (tmp_path / "docs/testing.md").write_text("no env vars documented\n", encoding="utf-8")

    out_json = tmp_path / ".runtime-cache/reports/governance/report.json"
    proc = _run_report(
        tmp_path,
        "--fail-on",
        "doc_drift",
        "--json-out",
        str(out_json),
    )

    assert proc.returncode == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["doc_drift"]["missing_required_in_docs"] == ["SQLITE_PATH"]
