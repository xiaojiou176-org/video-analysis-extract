from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_quality_gate_preserves_required_existing_semantics() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'MUTATION_MIN_SCORE="0.64"' in script
    assert 'MUTATION_MIN_EFFECTIVE_RATIO="0.27"' in script
    assert 'MUTATION_MAX_NO_TESTS_RATIO="0.72"' in script
    assert "Coverage thresholds: total >= 95%, core modules >= 95%." in script
    assert '"LIVE_SMOKE_REQUIRE_SECRETS": "1"' in script
    assert "uv run --with ruff ruff check apps/api apps/worker apps/mcp" in script
    assert "npm --prefix apps/web run test:coverage" in script


def test_quality_gate_remains_a_pure_gate_runner_without_owning_container_reexec() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert "CONTAINERIZED=\"auto\"" in script
    assert "--containerized 0|1|auto" in script
    assert 'if [[ "$CONTAINERIZED" != "0" && "$CONTAINERIZED" != "1" && "$CONTAINERIZED" != "auto" ]]; then' in script
    assert 'exec "$ROOT_DIR/scripts/run_in_standard_env.sh"' not in script
