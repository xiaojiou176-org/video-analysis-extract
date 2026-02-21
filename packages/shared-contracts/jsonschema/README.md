# JSON Schemas

Phase 3 共享契约副本：
- `common.schema.json`: Worker 通用对象与 pipeline 结果契约。
- `steps.schema.json`: Poll/Process workflow 与 activity 输入输出契约。
- `mcp-tools.schema.json`: MCP tools 输入契约（含 `vd.videos.process`、`vd.artifacts.get_markdown`）。

源码来源：
- `apps/worker/worker/contracts/*.json`
- `apps/mcp/schemas/tools.json`
