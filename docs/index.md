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
- 日志治理：`docs/reference/logging.md`
- 缓存治理：`docs/reference/cache.md`
- 依赖治理：`docs/reference/dependency-governance.md`

## Explanation

- 架构（Phase1-2）：`docs/phase1-2-architecture.md`
- 架构（Phase3）：`docs/phase3-architecture.md`

## Maintenance Rule

当以下内容发生变化时，必须同步更新相关文档：

- `infra/migrations/*.sql` -> `README.md`、`docs/runbook-local.md`
- `PIPELINE_STEPS` -> `docs/state-machine.md`
- 环境变量定义 -> `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`
