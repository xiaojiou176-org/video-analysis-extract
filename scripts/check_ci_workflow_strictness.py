#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
WORKFLOW_PATH = WORKFLOW_DIR / "ci.yml"
MIN_MUTATION_SCORE = 0.62
MIN_MUTATION_EFFECTIVE_RATIO = 0.25
MAX_MUTATION_NO_TESTS_RATIO = 0.75


def _job_blocks(text: str) -> list[tuple[str, str]]:
    jobs_section = re.search(r"^jobs:\s*$", text, flags=re.MULTILINE)
    if not jobs_section:
        return []

    section_start = jobs_section.end()
    section_end = len(text)
    next_top_level = re.search(r"^[A-Za-z0-9_-]+:\s*$", text[section_start:], flags=re.MULTILINE)
    if next_top_level:
        section_end = section_start + next_top_level.start()

    jobs: list[tuple[str, int]] = []
    jobs_text = text[section_start:section_end]
    for match in re.finditer(r"^  ([A-Za-z0-9_-]+):\n", jobs_text, flags=re.MULTILINE):
        jobs.append((match.group(1), section_start + match.start()))
    blocks: list[tuple[str, str]] = []
    for i, (name, start) in enumerate(jobs):
        end = jobs[i + 1][1] if i + 1 < len(jobs) else section_end
        blocks.append((name, text[start:end]))
    return blocks


def _contains_required_ci_gate(block: str) -> bool:
    return "check_required_ci_secrets.py" in block and "--required GEMINI_API_KEY" in block


def _has_job_level_uses(block: str) -> bool:
    return re.search(r"^\s{4}uses:\s+\S+", block, flags=re.MULTILINE) is not None


def _job_level_uses_target(block: str) -> str | None:
    match = re.search(r"^\s{4}uses:\s+(\S+?)(?:\s+#.*)?\s*$", block, flags=re.MULTILINE)
    return match.group(1) if match else None


def _local_reusable_workflow_has_timeouts(uses_target: str) -> bool:
    reusable_path = Path(uses_target[2:])
    if not reusable_path.is_file():
        return False
    reusable_text = reusable_path.read_text(encoding="utf-8")
    reusable_blocks = dict(_job_blocks(reusable_text))
    for block in reusable_blocks.values():
        has_direct_runs_on = re.search(r"^\s{4}runs-on:", block, flags=re.MULTILINE) is not None
        has_uses = _has_job_level_uses(block)
        if has_direct_runs_on and not has_uses and "timeout-minutes:" not in block:
            return False
    return True


def _has_needs_dep(block: str, dep: str) -> bool:
    lines = block.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^\s{4}needs:\s*(.*)$", line)
        if not match:
            continue

        tail = match.group(1).strip()
        if tail.startswith("&"):
            tail = ""

        if tail:
            # needs: [a, b] (single or multi-line flow style)
            if tail.startswith("["):
                flow = tail
                j = i + 1
                while "]" not in flow and j < len(lines):
                    flow += lines[j].strip()
                    j += 1
                inner = flow[flow.find("[") + 1 : flow.rfind("]")]
                items = [
                    item.strip().strip("'\"")
                    for item in inner.split(",")
                    if item.strip()
                ]
                return dep in items

            value = tail.split("#", 1)[0].strip().strip("'\"")
            return dep == value

        # needs:
        #   - a
        #   - b
        j = i + 1
        items: list[str] = []
        while j < len(lines):
            item_line = lines[j]
            if item_line.strip() == "":
                j += 1
                continue
            if not re.match(r"^\s{6,}", item_line):
                break
            item_match = re.match(r"^\s{6,}-\s*(.+?)\s*$", item_line)
            if item_match:
                item = item_match.group(1).split("#", 1)[0].strip().strip("'\"")
                if item:
                    items.append(item)
            j += 1
        return dep in items

    return False


def _extract_flag_value(block: str, flag: str) -> float | None:
    pattern = rf"{re.escape(flag)}\s+([0-9]+(?:\.[0-9]+)?)"
    match = re.search(pattern, block)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_job_level_if_expression(block: str) -> str | None:
    lines = block.splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^\s{4}if:\s*(.+)$", line)
        if not match:
            continue

        value = match.group(1).strip()
        if value.startswith("${{"):
            expr = value
            j = i + 1
            while "}}" not in expr and j < len(lines):
                cont = lines[j]
                if not re.match(r"^\s{6,}", cont):
                    break
                expr += " " + cont.strip()
                j += 1
            if "}}" in expr:
                return expr[expr.find("${{") + 3 : expr.rfind("}}")].strip()
        return value
    return None


def _if_expr_checks_success_for_job(if_expr: str, job_name: str) -> bool:
    patterns = (
        rf"needs\.{re.escape(job_name)}\.result\s*==\s*['\"]success['\"]",
        rf"needs\[['\"]{re.escape(job_name)}['\"]\]\.result\s*==\s*['\"]success['\"]",
    )
    return any(re.search(pattern, if_expr) is not None for pattern in patterns)


def _aggregate_maps_required_ci_result(block: str) -> bool:
    patterns = (
        r"results\[required_ci_secrets\]\s*=\s*['\"]\$\{\{\s*needs\.required-ci-secrets\.result\s*\}\}['\"]",
        r"results\[required_ci_secrets\]\s*=\s*['\"]\$\{\{\s*needs\[['\"]required-ci-secrets['\"]\]\.result\s*\}\}['\"]",
    )
    return any(re.search(pattern, block) is not None for pattern in patterns)


def _aggregate_enforces_required_ci_success(block: str) -> bool:
    direct_patterns = (
        r'if\s+\[\[\s*"\$\{results\[required_ci_secrets\]\}"\s*!=\s*"success"\s*\]\]',
        r"check_required_job\s+required_ci_secrets\s+['\"]?1['\"]?",
    )
    if any(re.search(pattern, block) is not None for pattern in direct_patterns):
        return True

    has_required_in_for_loop = re.search(
        r"for\s+job\s+in\s+[^\n]*\brequired_ci_secrets\b", block
    ) is not None
    has_success_only_guard = re.search(
        r'if\s+\[\[\s*"\$result"\s*!=\s*"success"\s*\]\]\s*;\s*then(?:\s|\n)*failed=1',
        block,
    ) is not None
    return has_required_in_for_loop and has_success_only_guard


def _check_global_rules(
    workflow_path: Path, text: str, blocks: dict[str, str], failures: list[str]
) -> None:
    # Third-party actions must be pinned to immutable commit SHAs.
    for match in re.finditer(r"^\s+uses:\s+([^\s#]+)", text, flags=re.MULTILINE):
        uses_target = match.group(1).strip()
        if uses_target.startswith(("./", "docker://")):
            continue
        if "@" not in uses_target:
            failures.append(
                f"{workflow_path.name}: unpinned action reference `{uses_target}` (missing @<commit-sha>)"
            )
            continue
        action_ref = uses_target.rsplit("@", 1)[1]
        if not re.fullmatch(r"[0-9a-f]{40}", action_ref):
            failures.append(
                f"{workflow_path.name}: action `{uses_target}` must pin a 40-char commit SHA"
            )

    # Inline pipe-to-shell patterns are forbidden in workflows.
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:bash|sh)\b", stripped):
            failures.append(
                f"{workflow_path.name}:{lineno}: forbidden pipe-to-shell command detected (`curl|sh` or `wget|sh`)"
            )

    # Skip reusable workflows (workflow_call).
    is_reusable = "on:\n  workflow_call:" in text or "on:\n    workflow_call:" in text

    # Any runnable job must declare timeout-minutes.
    # Jobs that delegate to reusable workflows (uses:) have timeout in the reusable workflow.
    for job, block in blocks.items():
        has_direct_runs_on = re.search(r"^\s{4}runs-on:", block, flags=re.MULTILINE) is not None
        has_uses = _has_job_level_uses(block)
        if has_direct_runs_on and not has_uses and "timeout-minutes:" not in block:
            failures.append(f"{workflow_path.name}: {job}: missing timeout-minutes")
            continue
        if has_uses and "timeout-minutes:" not in block:
            uses_target = _job_level_uses_target(block)
            if not uses_target:
                failures.append(f"{workflow_path.name}: {job}: missing timeout-minutes")
                continue
            if not uses_target.startswith("./"):
                failures.append(
                    f"{workflow_path.name}: {job}: reusable workflow jobs without local `uses: ./...` must set timeout-minutes explicitly"
                )
                continue
            if not _local_reusable_workflow_has_timeouts(uses_target):
                failures.append(
                    f"{workflow_path.name}: {job}: reusable workflow {uses_target} must define timeout-minutes on runnable jobs"
                )

    # continue-on-error=true is only allowed on hosted jobs that have explicit
    # fallback partners. This lets hosted billing/capacity failures degrade
    # gracefully without masking real failures in non-hosted jobs.
    for job, block in blocks.items():
        has_continue = re.search(
            r"^\s{4}continue-on-error:\s*true\s*$", block, flags=re.MULTILINE
        ) is not None
        if not has_continue:
            continue
        if not job.endswith("-hosted"):
            failures.append(
                f"{workflow_path.name}: {job}: continue-on-error=true is only allowed on *-hosted jobs"
            )
            continue
        base = job[: -len("-hosted")]
        fallback_name = f"{base}-fallback"
        if fallback_name not in blocks:
            failures.append(
                f"{workflow_path.name}: {job}: continue-on-error=true requires companion fallback job {fallback_name}"
            )

    # Reusable workflows (workflow_call) don't need required-ci-secrets job.
    if is_reusable:
        return

    # Every workflow must hard-fail when required CI secrets are missing.
    required_ci_secrets = blocks.get("required-ci-secrets", "")
    if not required_ci_secrets:
        failures.append(f"{workflow_path.name}: required-ci-secrets: missing job")
    elif not _contains_required_ci_gate(required_ci_secrets):
        failures.append(
            f"{workflow_path.name}: required-ci-secrets: must run check_required_ci_secrets.py with --required GEMINI_API_KEY"
        )

    # Hosted -> fallback -> resolver chain checks for small tasks.
    for job_name, hosted_block in blocks.items():
        if not job_name.endswith("-hosted"):
            continue

        base = job_name[: -len("-hosted")]
        fallback_name = f"{base}-fallback"
        resolver_name = base
        fallback_block = blocks.get(fallback_name, "")
        resolver_block = blocks.get(resolver_name, "")

        # Jobs that call reusable workflows via `uses:` cannot set
        # `continue-on-error` at the caller level.
        if not _has_job_level_uses(hosted_block) and "continue-on-error: true" not in hosted_block:
            failures.append(
                f"{workflow_path}: {job_name}: hosted jobs must set continue-on-error: true to allow fallback takeover"
            )

        if (
            "runs-on: [self-hosted, e2-core, spot, shared-pool]" not in hosted_block
            and "runs-on: '[\"self-hosted\",\"e2-core\",\"spot\",\"shared-pool\"]'" not in hosted_block
        ):
            failures.append(
                f"{workflow_path}: {job_name}: hosted jobs must run on self-hosted runner pool"
            )

        if not fallback_block:
            failures.append(
                f"{workflow_path}: {fallback_name}: missing fallback job for {job_name}"
            )
        else:
            if (
                "runs-on: [self-hosted, e2-core, spot, shared-pool]" not in fallback_block
                and "runs-on: '[\"self-hosted\",\"e2-core\",\"spot\",\"shared-pool\"]'" not in fallback_block
            ):
                failures.append(
                    f"{workflow_path}: {fallback_name}: fallback jobs must run on self-hosted runner pool"
                )
            if not re.search(
                rf"^\s+if:\s+\$\{{\{{.*always\(\).*(needs\['{re.escape(job_name)}'\]\.result\s*!=\s*['\"]success['\"]|needs\.{re.escape(job_name)}\.result\s*!=\s*['\"]success['\"]).*\}}\}}\s*$",
                fallback_block,
                flags=re.MULTILINE,
            ):
                failures.append(
                    f"{workflow_path}: {fallback_name}: fallback must use always() and trigger only when {job_name} != success"
                )

        if not resolver_block:
            failures.append(
                f"{workflow_path}: {resolver_name}: missing resolver job for hosted/fallback chain"
            )
        else:
            if not _has_needs_dep(resolver_block, job_name) or not _has_needs_dep(
                resolver_block, fallback_name
            ):
                failures.append(
                    f"{workflow_path}: {resolver_name}: resolver needs must include both {job_name} and {fallback_name}"
                )
            if not re.search(r"^\s+if:\s+\$\{\{\s*always\(\)", resolver_block, flags=re.MULTILINE):
                failures.append(
                    f"{workflow_path}: {resolver_name}: resolver must use if: ${{{{ always() ... }}}}"
                )
            resolver_if_expr = _extract_job_level_if_expression(resolver_block) or ""
            hosted_ok = _if_expr_checks_success_for_job(resolver_if_expr, job_name)
            fallback_ok = _if_expr_checks_success_for_job(resolver_if_expr, fallback_name)
            if not (hosted_ok and fallback_ok):
                failures.append(
                    f"{workflow_path}: {resolver_name}: resolver must only pass when hosted or fallback is successful"
                )


def _check_ci_specific_rules(blocks: dict[str, str], failures: list[str]) -> None:
    # quality-gate-pre-push must run broadly (not main/schedule-only gated).
    qg_block = blocks.get("quality-gate-pre-push", "")
    if not qg_block:
        failures.append("ci.yml: quality-gate-pre-push: missing job")
    else:
        if re.search(r"^\s{4}if:\s", qg_block, flags=re.MULTILINE):
            failures.append(
                "ci.yml: quality-gate-pre-push: should not narrow execution with job-level if"
            )
        if not re.search(r"--mode\s+pre-push\b", qg_block):
            failures.append("ci.yml: quality-gate-pre-push: missing pre-push quality gate command")
        if not re.search(r"--ci-dedupe\s+1\b", qg_block):
            failures.append(
                "ci.yml: quality-gate-pre-push: must set --ci-dedupe 1 to avoid duplicate heavy checks already enforced by standalone CI jobs"
            )
        if not re.search(r"--skip-mutation\s+1\b", qg_block):
            failures.append(
                "ci.yml: quality-gate-pre-push: must set --skip-mutation 1 because mutation-testing runs as a dedicated standalone CI job"
            )
        min_score = _extract_flag_value(qg_block, "--mutation-min-score")
        if min_score is None:
            failures.append("ci.yml: quality-gate-pre-push: missing mutation score floor")
        elif min_score < MIN_MUTATION_SCORE:
            failures.append(
                "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.62"
            )
        min_effective_ratio = _extract_flag_value(qg_block, "--mutation-min-effective-ratio")
        if min_effective_ratio is None:
            failures.append("ci.yml: quality-gate-pre-push: missing mutation effective ratio floor")
        elif min_effective_ratio < MIN_MUTATION_EFFECTIVE_RATIO:
            failures.append(
                "ci.yml: quality-gate-pre-push: mutation effective ratio floor must be at least 0.25"
            )
        max_no_tests_ratio = _extract_flag_value(qg_block, "--mutation-max-no-tests-ratio")
        if max_no_tests_ratio is None:
            failures.append(
                "ci.yml: quality-gate-pre-push: missing mutation no-tests ratio ceiling"
            )
        elif max_no_tests_ratio > MAX_MUTATION_NO_TESTS_RATIO:
            failures.append(
                "ci.yml: quality-gate-pre-push: mutation no-tests ratio ceiling must be at most 0.75"
            )

    # Real smoke jobs must not bypass write auth.
    for job_name in ("api-real-smoke", "pr-llm-real-smoke"):
        block = blocks.get(job_name, "")
        if not block:
            failures.append(f"ci.yml: {job_name}: missing job")
            continue
        if "VD_ALLOW_UNAUTH_WRITE" in block:
            failures.append(f"ci.yml: {job_name}: forbidden VD_ALLOW_UNAUTH_WRITE bypass detected")

    # Aggregate gate must require critical jobs.
    aggregate = blocks.get("aggregate-gate", "")
    if not aggregate:
        failures.append("ci.yml: aggregate-gate: missing job")
    if aggregate and not _has_needs_dep(aggregate, "required-ci-secrets"):
        failures.append("ci.yml: aggregate-gate: missing needs dependency `required-ci-secrets`")
    for required_job in ("quality-gate-pre-push", "api-real-smoke", "web-e2e", "python-tests"):
        if aggregate and not _has_needs_dep(aggregate, required_job):
            failures.append(f"ci.yml: aggregate-gate: missing needs dependency `{required_job}`")
    if aggregate and not _aggregate_maps_required_ci_result(aggregate):
        failures.append(
            "ci.yml: aggregate-gate: must map required-ci-secrets job result into runtime gate logic (results[required_ci_secrets]=...)"
        )
    if aggregate and not _aggregate_enforces_required_ci_success(aggregate):
        failures.append(
            "ci.yml: aggregate-gate: must hard-fail when required-ci-secrets result is not success"
        )

    # Preflight must include focused-test guard steps.
    required_preflight_markers = {
        "Test focus/todo marker guard": "test focus/todo marker guard step",
        "E2E strictness guard": "e2e strictness guard step",
        "Mutation scope guard": "mutation scope guard step",
        "Mutation test selection guard": "mutation test selection guard step",
    }
    preflight_fast = blocks.get("preflight-fast", "")
    missing_in_preflight = [
        description
        for marker, description in required_preflight_markers.items()
        if marker not in preflight_fast
    ]
    if missing_in_preflight:
        # Fallback-aware structure: `preflight-fast` can be a resolver while hosted/fallback
        # execute the actual checks. In that case, both execution paths must contain markers.
        # If hosted/fallback use reusable workflows (uses:), check the reusable workflow file.
        for job_name in ("preflight-fast-hosted", "preflight-fast-fallback"):
            block = blocks.get(job_name, "")
            if "uses: ./.github/workflows/_preflight-fast-steps.yml" in block:
                # Read the reusable workflow and check it contains the markers.
                reusable_path = Path(".github/workflows/_preflight-fast-steps.yml")
                if reusable_path.is_file():
                    reusable_text = reusable_path.read_text(encoding="utf-8")
                    for marker, description in required_preflight_markers.items():
                        if marker not in reusable_text:
                            failures.append(f"ci.yml: {job_name}: missing {description} (delegated to _preflight-fast-steps.yml)")
                else:
                    failures.append(f"ci.yml: {job_name}: reusable workflow _preflight-fast-steps.yml not found")
            else:
                # Inline steps mode.
                for marker, description in required_preflight_markers.items():
                    if marker not in block:
                        failures.append(f"ci.yml: {job_name}: missing {description}")

    # live-smoke must run on a fully provisioned local stack and enforce secrets.
    live_smoke = blocks.get("live-smoke", "")
    if not live_smoke:
        failures.append("ci.yml: live-smoke: missing job")
    else:
        required_live_smoke_markers = {
            "services:\n      postgres:": "postgres service",
            "Run migrations for live smoke DB": "migration step",
            "Start Temporal dev server for live smoke": "temporal startup step",
            '--require-secrets "1"': "hard secrets requirement",
            "Validate required live smoke secrets": "explicit secret validation step",
        }
        for marker, description in required_live_smoke_markers.items():
            if marker not in live_smoke:
                failures.append(f"ci.yml: live-smoke: missing {description}")


def main() -> int:
    if not WORKFLOW_PATH.is_file():
        raise SystemExit(f"missing workflow file: {WORKFLOW_PATH}")

    failures: list[str] = []
    workflow_files = sorted(WORKFLOW_DIR.glob("*.yml"))
    if not workflow_files:
        failures.append("missing workflow files under .github/workflows")
    for workflow in workflow_files:
        text = workflow.read_text(encoding="utf-8")
        blocks = dict(_job_blocks(text))
        _check_global_rules(workflow, text, blocks, failures)
        if workflow == WORKFLOW_PATH:
            _check_ci_specific_rules(blocks, failures)

    if failures:
        print("ci workflow strictness gate failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("ci workflow strictness gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
