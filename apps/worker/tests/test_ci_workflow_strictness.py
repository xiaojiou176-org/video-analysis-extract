from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "check_ci_workflow_strictness.py"
    spec = importlib.util.spec_from_file_location("check_ci_workflow_strictness", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_global_rules_reject_hosted_jobs_on_self_hosted_pool() -> None:
    module = _load_module()
    hosted_block = """  preflight-fast-hosted:
    runs-on: [self-hosted, shared-pool]
    continue-on-error: true
    timeout-minutes: 5
    steps:
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

    assert (
        "ci.yml: preflight-fast-hosted: hosted jobs must run on ubuntu-latest (or reusable workflow input [\"ubuntu-latest\"])"
        in failures
    )


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
    timeout-minutes: 5
    steps:
      - run: |
          ./scripts/quality_gate.sh \
            --mode pre-push \
            --ci-dedupe 1 \
            --skip-mutation 1 \
            --mutation-min-score 0.70 \
            --mutation-min-effective-ratio 0.30 \
            --mutation-max-no-tests-ratio 0.70
"""
    blocks = {
        "quality-gate-pre-push": qg_block,
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
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
    services:
      postgres:
    steps:
      - name: Run migrations for live smoke DB
      - name: Start Temporal dev server for live smoke
      - run: echo '--require-secrets "1"'
      - name: Validate required live smoke secrets
""",
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert (
        "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.62"
        not in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation effective ratio floor must be at least 0.25"
        not in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation no-tests ratio ceiling must be at most 0.75"
        not in failures
    )


def test_ci_specific_rules_rejects_weaker_quality_gate_mutation_thresholds() -> None:
    module = _load_module()
    qg_block = """  quality-gate-pre-push:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: |
          ./scripts/quality_gate.sh \
            --mode pre-push \
            --ci-dedupe 1 \
            --skip-mutation 1 \
            --mutation-min-score 0.61 \
            --mutation-min-effective-ratio 0.24 \
            --mutation-max-no-tests-ratio 0.76
"""
    blocks = {
        "quality-gate-pre-push": qg_block,
        "api-real-smoke": "  api-real-smoke:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "web-e2e": "  web-e2e:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
        "python-tests": "  python-tests:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n",
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
    services:
      postgres:
    steps:
      - name: Run migrations for live smoke DB
      - name: Start Temporal dev server for live smoke
      - run: echo '--require-secrets "1"'
      - name: Validate required live smoke secrets
""",
    }
    failures: list[str] = []

    module._check_ci_specific_rules(blocks, failures)

    assert "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.62" in failures
    assert (
        "ci.yml: quality-gate-pre-push: mutation effective ratio floor must be at least 0.25"
        in failures
    )
    assert (
        "ci.yml: quality-gate-pre-push: mutation no-tests ratio ceiling must be at most 0.75"
        in failures
    )


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
