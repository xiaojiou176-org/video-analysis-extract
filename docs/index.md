# Documentation Index

## Start Here

- 1 分钟入口（唯一）：`docs/start-here.md`
- 项目前门：`README.md`
- AI/协作协议：`AGENTS.md`
- 本地运行与排障：`docs/runbook-local.md`

## How-To

- 本地启动、迁移、验收：`docs/runbook-local.md`
- 测试执行：`docs/testing.md`
- GCE 可选阅读栈部署（Miniflux + Nextflux）：`docs/deploy/miniflux-nextflux-gce.md`

## Reference

- 状态机与流程契约：`docs/state-machine.md`
- 环境变量契约：`ENVIRONMENT.md`
- 治理仪表盘：`docs/generated/governance-dashboard.md`
- CI 主链参考：`docs/generated/ci-topology.md`
- Required checks 参考：`docs/generated/required-checks.md`
- runner baseline 参考：`docs/generated/runner-baseline.md`
- release evidence 参考：`docs/generated/release-evidence.md`
- 日志治理：`docs/reference/logging.md`
- 缓存治理：`docs/reference/cache.md`
- 依赖治理：`docs/reference/dependency-governance.md`
- repo-side / external done model：`docs/reference/done-model.md`
- public repo readiness：`docs/reference/public-repo-readiness.md`
- public artifact exposure：`docs/reference/public-artifact-exposure.md`
- public rights / provenance：`docs/reference/public-rights-and-provenance.md`
- public privacy / data boundary：`docs/reference/public-privacy-and-data-boundary.md`
- public brand boundary：`docs/reference/public-brand-boundary.md`
- AI evaluation：`docs/reference/ai-evaluation.md`
- newcomer/result proof：`docs/reference/newcomer-result-proof.md`
- 任务级价值证明：`docs/reference/value-proof.md`

## Explanation

- 架构：`docs/architecture.md`
- 项目定位：`docs/reference/project-positioning.md`

## Maintenance Rule

当以下内容发生变化时，必须同步更新相关文档：

- `infra/migrations/*.sql` -> `README.md`、`docs/runbook-local.md`
- `PIPELINE_STEPS` -> `docs/state-machine.md`
- 环境变量定义 -> `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`
