# Public Repo Readiness

本仓库的公开策略是 **public source-first repo with limited-maintenance governance and governed local verification**，不是“镜像优先产品分发”，也不是“高信心 adoption-grade 开源产品”。

## Public Status

- 发布姿态：源码优先的公开仓库（public source-first）
- 维护模式：limited-maintenance
- 不承诺 hosted service、镜像即官方交付、或每条 external lane 同步闭环
- 当前 public 目标是 **安全可审阅、边界清楚、repo-side 验证诚实**，不是让陌生人无条件依赖外部分发链直接采用
- 远端仓库当前已经公开；但这不等于 GHCR、release evidence、provider/live lanes 已全部闭环。

## Required Public Governance Pack

以下文件构成最小公共治理包：

- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`
- `.github/CODEOWNERS`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`

## Public Boundary

public-safe:

- 源码、合同、治理控制面、generated reference docs
- sanitized performance budgets
- historical release evidence examples with explicit non-canonical wording
- sanitized public samples only

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
