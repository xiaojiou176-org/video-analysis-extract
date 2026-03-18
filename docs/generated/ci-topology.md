<!-- generated: docs governance control plane; do not edit directly -->

# CI Topology Reference

## Trust Boundary

- mode: `trusted_internal_pr_only`
- summary: Self-hosted CI is reserved for trusted internal pull requests. Fork or untrusted PRs must not enter the privileged self-hosted path.
- policy source: `config/docs/boundary-policy.json`

## Strict Runtime Contract

- standard image repository: `ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard`
- standard image workdir: `/workspace`
- python version: `3.12`
- node major: `22`
- coverage min: `95`
- core coverage min: `95`
- mutation min score: `0.64`

## Governance Control Plane

- root allowlist entries: `40`
- local-private root tolerations: `5`
- runtime root: `.runtime-cache`
- current-run CI KPI summary: `.runtime-cache/reports/release-readiness/ci-kpi-summary.json`
- current-run rollback/readiness reports: `.runtime-cache/reports/release-readiness/`
- current-run release-evidence attestation readiness: `.runtime-cache/reports/release/release-evidence-attest-readiness.json`
- active upstream inventory entries: `18`
- upstream templates: `1`
- governance gate entrypoint: `./bin/governance-audit --mode pre-commit|pre-push|ci|audit`
- GHCR image publish workflow primes Docker Buildx on self-hosted runners before calling `scripts/ci/build_standard_image.sh`

## Aggregate Gate Inventory

## Completion Lanes

- repo-side canonical path: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- external lane path: `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- source of truth: `docs/reference/done-model.md`

## Aggregate Gate Inventory

| Job | Role |
| --- | --- |
| `trusted-pr-boundary` | required chain input |
| `required-ci-secrets` | required chain input |
| `changes` | required chain input |
| `preflight-fast` | required chain input |
| `preflight-heavy` | required chain input |
| `profile-governance` | required chain input |
| `quality-gate-pre-push` | required chain input |
| `db-migration-smoke` | integration or end-to-end evidence |
| `mutation-testing` | required chain input |
| `python-tests` | required chain input |
| `api-real-smoke` | integration or end-to-end evidence |
| `pr-llm-real-smoke` | conditional edge or live evidence input |
| `backend-lint` | fast/static correctness |
| `frontend-lint` | fast/static correctness |
| `web-test-build` | required chain input |
| `web-e2e` | integration or end-to-end evidence |
| `web-e2e-perceived` | integration or end-to-end evidence |
| `external-playwright-smoke` | conditional edge or live evidence input |
| `dependency-vuln-scan` | required chain input |

## Governance Audit Workflows

- `monthly-governance-audit.yml`: emits recurring root/runtime/logging/upstream governance evidence

## Trigger Surfaces

- pull_request:
- push: branches: - main - release/** - codex/**
- schedule: - cron: "0 3 * * *"

## Docs Control Plane Outputs

- `docs/generated/governance-dashboard.md`
- `docs/generated/ci-topology.md`
- `docs/generated/required-checks.md`
- `docs/generated/runner-baseline.md`
- `docs/generated/release-evidence.md`
- `docs/generated/external-lane-snapshot.md`
