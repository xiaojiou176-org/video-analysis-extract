#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
WORKFLOW_PATH = WORKFLOW_DIR / "ci.yml"


def _job_blocks(text: str) -> list[tuple[str, str]]:
    jobs: list[tuple[str, int]] = []
    for match in re.finditer(r"^  ([A-Za-z0-9_-]+):\n", text, flags=re.MULTILINE):
        jobs.append((match.group(1), match.start()))
    blocks: list[tuple[str, str]] = []
    for i, (name, start) in enumerate(jobs):
        end = jobs[i + 1][1] if i + 1 < len(jobs) else len(text)
        blocks.append((name, text[start:end]))
    return blocks


def _contains_required_ci_gate(block: str) -> bool:
    return "check_required_ci_secrets.py" in block and "--required GEMINI_API_KEY" in block


def _has_needs_dep(block: str, dep: str) -> bool:
    if f"- {dep}" in block:
        return True
    pattern = rf"^\s+needs:\s*\[[^\]]*\b{re.escape(dep)}\b[^\]]*\]\s*$"
    return re.search(pattern, block, flags=re.MULTILINE) is not None


def _check_global_rules(
    workflow_path: Path, text: str, blocks: dict[str, str], failures: list[str]
) -> None:
    # Skip reusable workflows (workflow_call).
    is_reusable = "on:\n  workflow_call:" in text or "on:\n    workflow_call:" in text

    # Any runnable job must declare timeout-minutes.
    # Jobs that delegate to reusable workflows (uses:) have timeout in the reusable workflow.
    for job, block in blocks.items():
        has_direct_runs_on = re.search(r"^\s{4}runs-on:", block, flags=re.MULTILINE) is not None
        has_uses = "uses:" in block
        if has_direct_runs_on and not has_uses and "timeout-minutes:" not in block:
            failures.append(f"{workflow_path.name}: {job}: missing timeout-minutes")

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

        if "continue-on-error: true" not in hosted_block:
            failures.append(
                f"{workflow_path}: {job_name}: hosted jobs must set continue-on-error: true to allow fallback takeover"
            )

        if "runs-on: ubuntu-latest" not in hosted_block:
            failures.append(f"{workflow_path}: {job_name}: hosted jobs must use ubuntu-latest")

        if not fallback_block:
            failures.append(
                f"{workflow_path}: {fallback_name}: missing fallback job for {job_name}"
            )
        else:
            if "runs-on: e2-core" not in fallback_block:
                failures.append(
                    f"{workflow_path}: {fallback_name}: fallback jobs must run on e2-core"
                )
            if not re.search(
                rf"^\s+if:\s+\$\{{\{{.*always\(\).*(needs\['{re.escape(job_name)}'\]\.result\s*!=\s*'success'|needs\.{re.escape(job_name)}\.result\s*!=\s*'success').*\}}\}}\s*$",
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
            if "result == 'success'" not in resolver_block:
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
        if "--mode pre-push" not in qg_block:
            failures.append("ci.yml: quality-gate-pre-push: missing pre-push quality gate command")
        if "--ci-dedupe 1" not in qg_block:
            failures.append(
                "ci.yml: quality-gate-pre-push: must set --ci-dedupe 1 to avoid duplicate heavy checks already enforced by standalone CI jobs"
            )
        if "--skip-mutation 1" not in qg_block:
            failures.append(
                "ci.yml: quality-gate-pre-push: must set --skip-mutation 1 because mutation-testing runs as a dedicated standalone CI job"
            )
        if "--mutation-min-score 0.62" not in qg_block:
            failures.append(
                "ci.yml: quality-gate-pre-push: mutation threshold must be at least 0.62"
            )
        if "--mutation-min-effective-ratio 0.25" not in qg_block:
            failures.append("ci.yml: quality-gate-pre-push: missing mutation effective ratio floor")
        if "--mutation-max-no-tests-ratio 0.75" not in qg_block:
            failures.append(
                "ci.yml: quality-gate-pre-push: missing mutation no-tests ratio ceiling"
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
    if "- required-ci-secrets" not in aggregate:
        failures.append("ci.yml: aggregate-gate: missing needs dependency `required-ci-secrets`")
    for required_job in ("quality-gate-pre-push", "api-real-smoke", "web-e2e", "python-tests"):
        if f"- {required_job}" not in aggregate:
            failures.append(f"ci.yml: aggregate-gate: missing needs dependency `{required_job}`")

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
