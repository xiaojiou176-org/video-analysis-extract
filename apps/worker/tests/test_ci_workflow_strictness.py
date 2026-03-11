from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_module():
    module_path = _repo_root() / "scripts" / "check_ci_workflow_strictness.py"
    spec = importlib.util.spec_from_file_location("check_ci_workflow_strictness", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_web_e2e_import_stubs() -> None:
    playwright_module = ModuleType("playwright")
    sync_api_module = ModuleType("playwright.sync_api")
    sync_api_module.Browser = object
    sync_api_module.Page = object

    class _SyncPlaywrightContext:
        def __enter__(self) -> Any:
            raise AssertionError("sync_playwright stub should not be entered in collection hook contract test")

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    sync_api_module.sync_playwright = lambda: _SyncPlaywrightContext()
    playwright_module.sync_api = sync_api_module
    sys.modules.setdefault("playwright", playwright_module)
    sys.modules.setdefault("playwright.sync_api", sync_api_module)

    support_module = ModuleType("support")
    mock_api_module = ModuleType("support.mock_api")
    mock_api_module.MockApiServer = object
    mock_api_module.MockApiState = object
    mock_api_module.start_mock_api_server = lambda: None
    mock_api_module.stop_mock_api_server = lambda running: None

    runtime_utils_module = ModuleType("support.runtime_utils")
    runtime_utils_module.parse_external_web_base_url = lambda value: None
    runtime_utils_module.resolve_worker_id = lambda configured_worker_id, **_: configured_worker_id or "gw0"
    runtime_utils_module.slugify_nodeid = lambda nodeid: nodeid.replace("/", "-")
    runtime_utils_module.wait_http_ok = lambda url: None
    runtime_utils_module.with_free_port_retry = lambda starter, **_: (starter(3000), 3000)
    runtime_utils_module.worker_dist_dir = lambda worker_id: f".next-{worker_id}"

    support_module.mock_api = mock_api_module
    support_module.runtime_utils = runtime_utils_module
    sys.modules.setdefault("support", support_module)
    sys.modules.setdefault("support.mock_api", mock_api_module)
    sys.modules.setdefault("support.runtime_utils", runtime_utils_module)


def test_global_rules_timeout_uses_job_level_not_step_level() -> None:
    module = _load_module()
    block = """  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo lint
"""
    failures: list[str] = []

    module._check_global_rules(
        Path("ci.yml"),
        "name: CI\non:\n  pull_request:\n",
        {"lint": block},
        failures,
    )

    assert "ci.yml: lint: missing timeout-minutes" in failures


def test_global_rules_hosted_continue_on_error_uses_job_level_not_step_level() -> None:
    module = _load_module()
    hosted_block = """  preflight-fast-hosted:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo preflight
"""
    required_ci_secrets_block = """  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(
        Path("ci.yml"),
        "name: CI\non:\n  pull_request:\n",
        {
            "required-ci-secrets": required_ci_secrets_block,
            "preflight-fast-hosted": hosted_block,
        },
        failures,
    )

    expected = (
        "ci.yml: preflight-fast-hosted: hosted jobs must set continue-on-error: true "
        "to allow fallback takeover"
    )
    assert expected in failures


def test_pre_push_hook_uses_local_safe_ci_dedupe() -> None:
    hook_path = Path(__file__).resolve().parents[3] / ".githooks" / "pre-push"
    content = hook_path.read_text(encoding="utf-8")

    assert "--ci-dedupe 0" in content
    assert "--ci-dedupe 1" not in content


def test_global_rules_reusable_workflow_must_define_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    reusable = tmp_path / ".github" / "workflows" / "no-timeout.yml"
    reusable.parent.mkdir(parents=True, exist_ok=True)
    reusable.write_text(
        """name: reusable
on:
  workflow_call:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
""",
        encoding="utf-8",
    )
    block = """  preflight-fast-hosted:
    uses: ./.github/workflows/no-timeout.yml
"""
    failures: list[str] = []

    module._check_global_rules(
        Path("ci.yml"),
        "name: CI\non:\n  pull_request:\n",
        {"preflight-fast-hosted": block},
        failures,
    )

    assert (
        "ci.yml: preflight-fast-hosted: reusable workflow ./.github/workflows/no-timeout.yml must define timeout-minutes on runnable jobs"
        in failures
    )


def test_has_needs_dep_ignores_step_list_items() -> None:
    module = _load_module()
    block = """  preflight-fast:
    needs:
      - required-ci-secrets
    steps:
      - run: |
          cat <<'EOF'
          - preflight-fast-hosted
          EOF
"""
    assert module._has_needs_dep(block, "preflight-fast-hosted") is False


def test_has_needs_dep_supports_multiline_flow_style() -> None:
    module = _load_module()
    block = """  preflight-fast:
    needs: [
      preflight-fast-hosted,
      preflight-fast-fallback,
    ]
    runs-on: ubuntu-latest
"""
    assert module._has_needs_dep(block, "preflight-fast-hosted") is True
    assert module._has_needs_dep(block, "preflight-fast-fallback") is True


def test_has_needs_dep_supports_anchor_with_block_list_and_comments() -> None:
    module = _load_module()
    block = """  preflight-fast:
    needs: &preflight_needs
      - preflight-fast-hosted  # hosted chain
      - preflight-fast-fallback
    runs-on: ubuntu-latest
"""
    assert module._has_needs_dep(block, "preflight-fast-hosted") is True
    assert module._has_needs_dep(block, "preflight-fast-fallback") is True


def test_job_level_uses_target_accepts_trailing_comment() -> None:
    module = _load_module()
    block = """  preflight-fast-hosted:
    uses: ./.github/workflows/no-timeout.yml # delegate checks
"""
    assert module._job_level_uses_target(block) == "./.github/workflows/no-timeout.yml"


def test_global_rules_require_checkout_clean_true() -> None:
    module = _load_module()
    workflow = """name: CI
on:
  pull_request:
jobs:
      lint:
        runs-on: ubuntu-latest
        timeout-minutes: 5
        steps:
          - name: Checkout
        uses: actions/checkout@1234567890abcdef1234567890abcdef12345678
          - run: echo lint
  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(Path("ci.yml"), workflow, dict(module._job_blocks(workflow)), failures)

    assert (
        "ci.yml:10: actions/checkout must declare with.clean: true on shared self-hosted runners"
        in failures
    )


def test_global_rules_forbid_checkout_workspace_tool_cache_paths() -> None:
    module = _load_module()
    workflow = """name: CI
on:
  pull_request:
env:
  CI_CACHE_ROOT: ${{ runner.temp }}/ci-cache
  PLAYWRIGHT_BROWSERS_PATH: ${{ github.workspace }}/.runtime-cache/ms-playwright
jobs:
      lint:
        runs-on: ubuntu-latest
        timeout-minutes: 5
        steps:
          - name: Checkout
        uses: actions/checkout@1234567890abcdef1234567890abcdef12345678
        with:
          clean: true
      - name: Cache Playwright browsers
        uses: actions/cache@1234567890abcdef1234567890abcdef12345678
        with:
          path: ${{ github.workspace }}/.runtime-cache/ms-playwright
  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(Path("ci.yml"), workflow, dict(module._job_blocks(workflow)), failures)

    assert (
        "ci.yml:6: PLAYWRIGHT_BROWSERS_PATH must resolve under runner.temp/CI_CACHE_ROOT, not repo paths or ~/.cache"
        in failures
    )
    assert (
        "ci.yml:17: actions/cache path `${{ github.workspace }}/.runtime-cache/ms-playwright` must resolve under runner.temp/CI_CACHE_ROOT"
        in failures
    )


def test_global_rules_require_ci_cache_root_for_cached_workflows() -> None:
    module = _load_module()
    workflow = """name: CI
on:
  pull_request:
jobs:
      lint:
        runs-on: ubuntu-latest
        timeout-minutes: 5
        steps:
          - name: Checkout
        uses: actions/checkout@1234567890abcdef1234567890abcdef12345678
        with:
          clean: true
      - name: Cache uv
        uses: actions/cache@1234567890abcdef1234567890abcdef12345678
        with:
          path: ${{ runner.temp }}/ci-cache/uv
  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(Path("ci.yml"), workflow, dict(module._job_blocks(workflow)), failures)

    assert (
        "ci.yml: workflows using actions/cache must declare CI_CACHE_ROOT under runner.temp"
        in failures
    )


def test_global_rules_reject_ci_concurrency_group_with_github_sha() -> None:
    module = _load_module()
    workflow = """name: CI
on:
  workflow_dispatch:
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}-${{ github.sha }}
  cancel-in-progress: true
jobs:
  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(Path("ci.yml"), workflow, dict(module._job_blocks(workflow)), failures)

    assert (
        "ci.yml: top-level concurrency.group must not include github.sha; use a stable workflow/event/ref key"
        in failures
    )


def test_global_rules_allow_ci_concurrency_group_with_manual_run_id() -> None:
    module = _load_module()
    workflow = """name: CI
on:
  workflow_dispatch:
concurrency:
  group: ${{ github.event_name == 'workflow_dispatch' && format('ci-{0}-{1}-{2}', github.workflow, github.ref, github.run_id) || format('ci-{0}-{1}-{2}', github.workflow, github.event_name, github.ref) }}
  cancel-in-progress: true
jobs:
  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    failures: list[str] = []

    module._check_global_rules(Path("ci.yml"), workflow, dict(module._job_blocks(workflow)), failures)

    assert (
        "ci.yml: top-level concurrency.group must not include github.sha; use a stable workflow/event/ref key"
        not in failures
    )


def test_ci_specific_rules_aggregate_needs_must_not_be_satisfied_by_comment_text() -> None:
    module = _load_module()
    aggregate_block = """  aggregate-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: always()
    needs:
      - quality-gate-pre-push
      - api-real-smoke
      - web-e2e
      - python-tests
    steps:
      - run: echo "- required-ci-secrets"
"""
    blocks = {
        "quality-gate-pre-push": "  quality-gate-pre-push:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "aggregate-gate": aggregate_block,
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert "ci.yml: aggregate-gate: missing needs dependency `required-ci-secrets`" in failures


def test_ci_specific_rules_aggregate_must_validate_required_ci_secrets_result() -> None:
    module = _load_module()
    aggregate_block = """  aggregate-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: always()
    needs:
      - required-ci-secrets
      - quality-gate-pre-push
      - api-real-smoke
      - web-e2e
      - python-tests
    steps:
      - run: echo "aggregate"
"""
    blocks = {
        "quality-gate-pre-push": "  quality-gate-pre-push:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "aggregate-gate": aggregate_block,
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert (
        "ci.yml: aggregate-gate: must map required-ci-secrets job result into runtime gate logic (results[required_ci_secrets]=...)"
        in failures
    )
    assert (
        "ci.yml: aggregate-gate: must hard-fail when required-ci-secrets result is not success"
        in failures
    )


def test_ci_specific_rules_accepts_stricter_quality_gate_mutation_thresholds() -> None:
    module = _load_module()
    qg_block = """  quality-gate-pre-push:
    runs-on: ubuntu-latest
    container:
      image: ${{ needs.ci-contract.outputs.standard_image_ref }}
    timeout-minutes: 5
    steps:
      - run: |
          ./scripts/strict_ci_entry.sh --mode pre-push \
            --ci-dedupe 1 \
            --skip-mutation 1 \
            --mutation-min-score 0.70 \
            --mutation-min-effective-ratio 0.30 \
            --mutation-max-no-tests-ratio 0.70
"""
    blocks = {
        "quality-gate-pre-push": qg_block,
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "pr-llm-real-smoke": "  pr-llm-real-smoke:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "web-test-build": "  web-test-build:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "aggregate-gate": """  aggregate-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: always()
    needs:
      - required-ci-secrets
      - quality-gate-pre-push
      - api-real-smoke
      - web-e2e
      - python-tests
    steps:
      - run: echo "needs.required-ci-secrets.result"
""",
        "preflight-fast": "",
        "live-smoke": """  live-smoke:
    container:
      image: ${{ needs.ci-contract.outputs.standard_image_ref }}
    services:
      postgres:
    steps:
      - run: ./scripts/strict_ci_entry.sh --mode live-smoke
      - run: echo 'GEMINI_API_KEY'
      - run: echo 'RESEND_API_KEY'
      - run: echo 'YOUTUBE_API_KEY'
""",
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert (
        "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.64"
        not in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation effective ratio floor must be at least 0.27"
        not in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation no-tests ratio ceiling must be at most 0.72"
        not in failures
    )


def test_ci_specific_rules_rejects_weaker_quality_gate_mutation_thresholds() -> None:
    module = _load_module()
    qg_block = """  quality-gate-pre-push:
    runs-on: ubuntu-latest
    container:
      image: ${{ needs.ci-contract.outputs.standard_image_ref }}
    timeout-minutes: 5
    steps:
      - run: |
          ./scripts/strict_ci_entry.sh --mode pre-push \
            --ci-dedupe 1 \
            --skip-mutation 1 \
            --mutation-min-score 0.61 \
            --mutation-min-effective-ratio 0.24 \
            --mutation-max-no-tests-ratio 0.76
"""
    blocks = {
        "quality-gate-pre-push": qg_block,
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "pr-llm-real-smoke": "  pr-llm-real-smoke:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "web-test-build": "  web-test-build:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    container:\n      image: ${{ needs.ci-contract.outputs.standard_image_ref }}\n    timeout-minutes: 5\n",
        "aggregate-gate": """  aggregate-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    if: always()
    needs:
      - required-ci-secrets
      - quality-gate-pre-push
      - api-real-smoke
      - web-e2e
      - python-tests
    steps:
      - run: echo "needs.required-ci-secrets.result"
""",
        "preflight-fast": "",
        "live-smoke": """  live-smoke:
    container:
      image: ${{ needs.ci-contract.outputs.standard_image_ref }}
    services:
      postgres:
    steps:
      - run: ./scripts/strict_ci_entry.sh --mode live-smoke
      - run: echo 'GEMINI_API_KEY'
      - run: echo 'RESEND_API_KEY'
      - run: echo 'YOUTUBE_API_KEY'
""",
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.64" in failures
    assert (
        "ci.yml: quality-gate-pre-push: mutation effective ratio floor must be at least 0.27"
        in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation no-tests ratio ceiling must be at most 0.72"
        in failures
    )


def test_python_tests_job_calls_repo_script_inside_strict_ci_entry() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "./scripts/strict_ci_entry.sh --mode python-tests" in workflow


def test_ci_python_tests_script_preserves_backend_coverage_and_junit_contract() -> None:
    script = (_repo_root() / "scripts" / "ci_python_tests.sh").read_text(encoding="utf-8")

    assert "mkdir -p .runtime-cache" in script
    assert "uv sync --frozen --extra dev --extra e2e" in script
    assert script.index("uv sync --frozen --extra dev --extra e2e") < script.index(
        "uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA -n 2"
    )
    assert "uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA -n 2" in script
    assert "--cov-report=xml:.runtime-cache/python-coverage.xml" in script
    assert "--junitxml=.runtime-cache/python-tests-junit.xml" in script
    assert ".runtime-cache/python-tests.log" in script
    assert "python-coverage-worker-core.log" in script
    assert "python-coverage-api-core.log" in script
    assert "python skip guard passed" in script


def test_api_real_smoke_job_calls_repo_script_inside_strict_ci_entry() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "./scripts/strict_ci_entry.sh --mode api-real-smoke" in workflow


def test_web_e2e_job_calls_repo_script_inside_strict_ci_entry() -> None:
    module = _load_module()
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    web_e2e_block = dict(module._job_blocks(workflow))["web-e2e"]
    script = (_repo_root() / "scripts" / "ci_web_e2e.sh").read_text(encoding="utf-8")
    strict_entry = (_repo_root() / "scripts" / "strict_ci_entry.sh").read_text(encoding="utf-8")

    assert "./scripts/strict_ci_entry.sh --mode web-e2e" in web_e2e_block
    assert "./scripts/ci_web_e2e.sh" in strict_entry
    assert 'DATABASE_URL="${DATABASE_URL:-}"' in script
    assert 'db_url="postgresql+psycopg://' not in script
    assert 'ensure_node_toolchain' in script
    assert 'npm --prefix apps/web ci' in script


def test_quality_gate_and_live_smoke_jobs_use_strict_ci_entry_and_contract_container() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "./scripts/strict_ci_entry.sh \\" in workflow
    assert "--mode pre-push" in workflow
    assert "--mode live-smoke" in workflow
    assert "image: ${{ needs.ci-contract.outputs.standard_image_ref }}" in workflow


def test_global_rules_rejects_resolver_without_hosted_or_fallback_success_checks() -> None:
    module = _load_module()
    required_ci_secrets_block = """  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    hosted_block = """  preflight-fast-hosted:
    runs-on: ubuntu-latest
    continue-on-error: true
    timeout-minutes: 5
"""
    fallback_block = """  preflight-fast-fallback:
    runs-on: e2-core
    timeout-minutes: 5
    if: ${{ always() && needs['preflight-fast-hosted'].result != 'success' }}
"""
    resolver_block = """  preflight-fast:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    needs: [preflight-fast-hosted, preflight-fast-fallback]
    if: ${{ always() && needs.required-ci-secrets.result == 'success' }}
"""
    failures: list[str] = []

    module._check_global_rules(
        Path("ci.yml"),
        "name: CI\non:\n  pull_request:\n",
        {
            "required-ci-secrets": required_ci_secrets_block,
            "preflight-fast-hosted": hosted_block,
            "preflight-fast-fallback": fallback_block,
            "preflight-fast": resolver_block,
        },
        failures,
    )

    assert (
        "ci.yml: preflight-fast: resolver must only pass when hosted or fallback is successful"
        in failures
    )


def test_global_rules_accepts_resolver_success_checks_with_double_quotes() -> None:
    module = _load_module()
    required_ci_secrets_block = """  required-ci-secrets:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python3 scripts/check_required_ci_secrets.py --required GEMINI_API_KEY
"""
    hosted_block = """  preflight-fast-hosted:
    runs-on: ubuntu-latest
    continue-on-error: true
    timeout-minutes: 5
"""
    fallback_block = """  preflight-fast-fallback:
    runs-on: e2-core
    timeout-minutes: 5
    if: ${{ always() && needs.preflight-fast-hosted.result != "success" }}
"""
    resolver_block = """  preflight-fast:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    needs:
      - preflight-fast-hosted
      - preflight-fast-fallback
    if: ${{ always() && (needs.preflight-fast-hosted.result == "success" || needs['preflight-fast-fallback'].result == "success") }}
"""
    failures: list[str] = []

    module._check_global_rules(
        Path("ci.yml"),
        "name: CI\non:\n  pull_request:\n",
        {
            "required-ci-secrets": required_ci_secrets_block,
            "preflight-fast-hosted": hosted_block,
            "preflight-fast-fallback": fallback_block,
            "preflight-fast": resolver_block,
        },
        failures,
    )

    assert (
        "ci.yml: preflight-fast: resolver must only pass when hosted or fallback is successful"
        not in failures
    )


@dataclass
class _CollectionConfig:
    hook: Any

    def getoption(self, name: str) -> str:
        assert name == "--web-e2e-use-mock-api"
        return ""


@dataclass
class _CollectedTestItem:
    nodeid: str
    fixturenames: list[str] = field(default_factory=list)
    keywords: dict[str, Any] = field(default_factory=dict)
    config: Any = None


def test_web_e2e_mock_only_cases_are_deselected_for_real_api_collection() -> None:
    _install_web_e2e_import_stubs()
    conftest_path = _repo_root() / "apps" / "web" / "tests" / "e2e" / "conftest.py"
    spec = importlib.util.spec_from_file_location("web_e2e_conftest", conftest_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    deselected: list[_CollectedTestItem] = []
    config = _CollectionConfig(
        hook=SimpleNamespace(pytest_deselected=lambda items: deselected.extend(items))
    )
    items = [
        _CollectedTestItem(
            nodeid="apps/web/tests/e2e/test_dashboard.py::test_dashboard_empty_subscription_and_tasks_links_with_mock_api",
            config=config,
        ),
        _CollectedTestItem(
            nodeid="apps/web/tests/e2e/test_feed.py::test_feed_filter_submit_and_clear",
            config=config,
        ),
    ]

    module.pytest_collection_modifyitems(config, items)

    assert [item.nodeid for item in items] == [
        "apps/web/tests/e2e/test_feed.py::test_feed_filter_submit_and_clear"
    ]
    assert [item.nodeid for item in deselected] == [
        "apps/web/tests/e2e/test_dashboard.py::test_dashboard_empty_subscription_and_tasks_links_with_mock_api"
    ]
