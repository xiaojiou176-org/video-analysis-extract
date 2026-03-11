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

    assert 'CONTAINERIZED="auto"' in script
    assert "--containerized 0|1|auto" in script
    assert 'if [[ "$CONTAINERIZED" != "0" && "$CONTAINERIZED" != "1" && "$CONTAINERIZED" != "auto" ]]; then' in script
    assert 'exec "$ROOT_DIR/scripts/run_in_standard_env.sh"' not in script


def test_quality_gate_provides_host_service_defaults_for_api_real_smoke_local() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'smoke_database_url="postgresql+psycopg://postgres:postgres@host.docker.internal:5432/video_analysis"' in script
    assert 'smoke_database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis"' in script
    assert 'smoke_temporal_target_host="host.docker.internal:7233"' in script
    assert 'smoke_temporal_target_host="127.0.0.1:7233"' in script
    assert 'local smoke_workspace_dir="${PIPELINE_WORKSPACE_DIR:-$ROOT_DIR/.runtime-cache/api-real-smoke-workspace}"' in script
    assert 'local smoke_artifact_root="${PIPELINE_ARTIFACT_ROOT:-$ROOT_DIR/.runtime-cache/api-real-smoke-artifacts}"' in script
    assert 'PIPELINE_WORKSPACE_DIR="$smoke_workspace_dir"' in script
    assert 'PIPELINE_ARTIFACT_ROOT="$smoke_artifact_root"' in script


def test_quality_gate_uses_minimal_database_url_for_contract_diff_export() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'local contract_database_url="${DATABASE_URL:-sqlite+pysqlite:///:memory:}"' in script
    assert 'DATABASE_URL="$contract_database_url" uv run python scripts/export_api_contract.py' in script
