# apps/worker

`apps/worker` 是仓库的任务执行层，负责 Temporal workflow/activity、pipeline 编排、状态持久化和外部内容采集。

## 责任

- 执行 poll、pipeline、cleanup、digest 等后台任务
- 管理 `run_id`、workflow 状态和运行时产物
- 驱动评论、字幕、摘要、embedding、artifact 写入

## 依赖边界

- 可以依赖：共享契约、状态存储、第三方 SDK、仓库级脚本约定
- 不允许依赖：`apps/api/app` 与 `apps/mcp` 的内部实现

## 运行与证据

- Worker 运行日志统一写入 `.runtime-cache/logs/components/`
- workflow / activity 证据进入 `.runtime-cache/reports/` 与 `.runtime-cache/evidence/`
- 关键执行链必须保留 `run_id`
