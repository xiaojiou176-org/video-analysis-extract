<!-- generated: docs governance control plane; do not edit directly -->

# Required Checks Reference

Generated from `aggregate-gate` in `.github/workflows/ci.yml`.

This page answers one narrow question in plain English: has the required-check list that controls PR/merge drifted or not?
In other words, it lists the merge-relevant required checks shared by branch protection and `aggregate-gate`; that list now **includes** `remote-integrity`.
`remote-required-checks=status=pass` only proves merge-relevant required-check integrity, which means branch protection and aggregate-required-check integrity stay aligned. It does **not** prove `ci-final-gate`, `live-smoke`, or nightly terminal closure.

| Check | Classification |
| --- | --- |
| `trusted-pr-boundary` | required |
| `required-ci-secrets` | required |
| `changes` | required |
| `preflight-fast` | required |
| `remote-integrity` | required |
| `preflight-heavy` | required |
| `profile-governance` | required |
| `quality-gate-pre-push` | required |
| `db-migration-smoke` | required |
| `mutation-testing` | required |
| `python-tests` | required |
| `api-real-smoke` | required |
| `pr-llm-real-smoke` | conditional |
| `backend-lint` | required |
| `frontend-lint` | required |
| `web-test-build` | required |
| `web-e2e` | required |
| `web-e2e-perceived` | required |
| `external-playwright-smoke` | conditional |
| `dependency-vuln-scan` | required |
