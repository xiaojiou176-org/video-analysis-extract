from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_quality_gate_backend_lint_scope_is_backend_only() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert "uv run --with ruff ruff check apps/api apps/worker apps/mcp" in script
    assert "uv run --with ruff ruff check apps scripts" not in script


def test_quality_gate_core_coverage_patterns_support_relative_and_absolute_paths() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert (
        "apps/worker/worker/pipeline/orchestrator.py,*/apps/worker/worker/pipeline/orchestrator.py"
        in script
    )
    assert "apps/worker/worker/pipeline/runner.py,*/apps/worker/worker/pipeline/runner.py" in script
    assert "apps/api/app/routers/ingest.py,*/apps/api/app/routers/ingest.py" in script
    assert "apps/api/app/services/jobs.py,*/apps/api/app/services/jobs.py" in script


def test_quality_gate_pre_push_runs_real_smoke_when_backend_changes() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'if [[ "$STRICT_FULL_RUN" == "1" || ( "$CI_DEDUPE" != "1" && "$EFFECTIVE_BACKEND_CHANGED" == "true" ) ]]; then' in script
    assert "phase=api-real-smoke-local (backend changed)" in script
    assert "run_api_real_smoke_local_gate" in script


def test_quality_gate_mutation_defaults_are_stricter_for_effective_ratio_and_no_tests() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'MUTATION_MIN_EFFECTIVE_RATIO="0.27"' in script
    assert 'MUTATION_MAX_NO_TESTS_RATIO="0.72"' in script
