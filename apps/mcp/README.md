# apps/mcp

`apps/mcp` 是仓库的工具层，把 API 能力转换成 MCP tool surface，对外暴露稳定工具契约。

## 责任

- 通过 HTTP 调用 API，而不是直接偷用 API 内部实现
- 做参数归一化、错误归一化、响应脱敏
- 维护 MCP tools schema 与共享契约的一致性

## 依赖边界

- 可以依赖：共享契约、MCP runtime、HTTP client
- 不允许依赖：`apps/api/app`、`apps/worker/worker` 内部实现

## 运行与证据

- MCP 运行日志统一写入 `.runtime-cache/logs/components/`
- 工具调用失败必须保留 redacted error payload
