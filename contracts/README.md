# Shared Contracts

这个目录是仓库唯一共享契约层，只放跨边界可复用的公开 contract，不放运行时代码。

## 负责什么

- `openapi.yaml`：API 公开契约真相源。
- `jsonschema/*.json`：共享 JSON schema 副本与校验面。
- `jsonschema/README.md`：JSON schema 的来源与一致性说明。

## 谁依赖它

- `apps/api`：公开 HTTP 路由与 schema 对齐。
- `apps/mcp`：工具 schema、MCP surface 与 OpenAPI/JSON schema 对齐。
- `apps/web`：浏览器侧 API surface 只允许依赖这里导出的 contract，不允许穿透后端实现。
- `scripts/governance/*`：contract parity、surface drift、schema mirror 校验。

## 禁止事项

- 禁止引入网络、env、subprocess、socket、shell 等运行时 side effect。
- 禁止把 `apps/api`、`apps/worker`、`apps/mcp` 的内部实现复制进来。
- 禁止在 overview 文档中手写镜像这些 contract 的高漂移事实。

## 变更入口

- 修改 `openapi.yaml` 后，必须同步验证 `apps/mcp/schemas/tools.json` 与 Web API surface。
- 修改 `jsonschema/*` 后，必须同步验证 schema parity 与共享 contract 使用方。

## 最低验证链

```bash
python3 scripts/governance/check_contract_surfaces.py
python3 scripts/governance/check_contract_locality.py
python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py
```
