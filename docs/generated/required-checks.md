<!-- generated: docs governance control plane; do not edit directly -->

# Required Checks Reference

Generated from `aggregate-gate` in `.github/workflows/ci.yml`.

这页先讲人话：它只回答“需要进入 branch protection / aggregate gate 的 required checks 列表有没有漂移”。
`remote-required-checks=status=pass` 只证明 aggregate-required-check integrity，**不证明** `ci-final-gate`、`live-smoke` 或 nightly terminal closure。

| Check | Classification |
| --- | --- |
| `trusted-pr-boundary` | required |
| `required-ci-secrets` | required |
| `changes` | required |
| `preflight-fast` | required |
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
