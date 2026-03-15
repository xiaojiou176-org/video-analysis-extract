# apps/api

`apps/api` 是仓库的 HTTP 控制面，负责暴露 `/api/v1/*`、认证/授权、健康检查、工作流触发与查询。

## 责任

- 接收外部请求并做参数/鉴权校验
- 通过服务层驱动 ingest、jobs、subscriptions、videos、ui audit 等能力
- 暴露 `trace_id`，把请求关联信息传给下游

## 依赖边界

- 可以依赖：仓库级配置、共享契约、标准库、第三方库
- 不允许依赖：`apps/worker/worker`、`apps/mcp` 的内部实现

## 运行与证据

- 本地 API 启动日志与联调日志统一写入 `.runtime-cache/logs/components/`
- API smoke 与失败证据进入 `.runtime-cache/reports/`、`.runtime-cache/evidence/`
- HTTP 级关联字段至少包含 `trace_id` 与 `request_id`
