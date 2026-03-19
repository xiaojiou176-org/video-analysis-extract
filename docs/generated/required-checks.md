<!-- generated: docs governance control plane; do not edit directly -->

# Required Checks Reference

Generated from `aggregate-gate` in `.github/workflows/ci.yml`.

这页先讲人话：它回答的是“会影响 PR/merge 放行的 required lane 清单有没有漂移”。
换句话说，这里列的是 branch protection / aggregate gate 共同依赖的 merge-relevant required checks，其中现在**包含** `remote-integrity`。
`remote-required-checks=status=pass` 只证明 merge-relevant required-check integrity（也就是 branch protection / aggregate-required-check integrity）对齐，**不证明** `ci-final-gate`、`live-smoke` 或 nightly terminal closure。

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
