# Public Repo Readiness

本仓库的公开策略是 **source-first public repo**，不是“镜像优先产品分发”。

## Public Status

- 发布形态：源码优先
- 维护模式：limited-maintenance
- 不承诺 hosted service、镜像即官方交付、或每条 external lane 同步闭环

## Required Public Governance Pack

以下文件构成最小公共治理包：

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `SUPPORT.md`
- `.github/CODEOWNERS`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`

## Public Boundary

public-safe:

- 源码、合同、治理控制面、generated reference docs
- sanitized performance budgets
- historical release evidence examples with explicit non-canonical wording

internal or conditional:

- provider-level secrets and live tokens
- GHCR/public distribution lane proof
- any sample that still points at production-like identities or routes

## Source-first Quickstart

对外默认入口：

1. `README.md`
2. `docs/start-here.md`
3. `docs/reference/done-model.md`

对外默认验收命令：

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```
