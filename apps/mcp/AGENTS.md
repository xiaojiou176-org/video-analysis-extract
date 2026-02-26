# apps/mcp 模块协作规范

## 0. 模块目的
- 本模块是视频分析系统的 MCP 工具层，向上游 Agent 暴露稳定工具接口。
- 本模块必须将 MCP 调用稳定映射到 API/服务能力，并保证参数与返回结构可验证。

## 1. 技术栈
- Python 3.11+
- FastMCP
- pytest

## 2. 导航索引（Lazy-Load）
1. `apps/mcp/server.py`（MCP 服务入口）
2. `apps/mcp/tools/`（工具实现）
3. `apps/mcp/schemas/`（入参/出参 schema）
4. `apps/mcp/tests/`（模块测试）

## 3. 质量门禁（MUST）

### 3.1 模块命令
```bash
./scripts/dev_mcp.sh

PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/mcp/tests -q
```

### 3.2 强制规则
1. 涉及 MCP 工具参数、返回结构或路由改动时，必须通过 `apps/mcp/tests`。
2. 涉及 API/MCP 契约联动改动时，必须补充对应测试并同步 `README.md`。
3. 涉及跨模块改动时，必须遵循根门禁：env contract + backend pytest + web lint + fake assertion gate。
4. 涉及启动/联调路径改动时，必须补一次 `./scripts/smoke_full_stack.sh` 或在交付中说明未执行原因。

## 4. 文档优先级（模块内）
1. `apps/mcp/AGENTS.md`
2. `apps/mcp/CLAUDE.md`
3. `docs/start-here.md`
4. `docs/runbook-local.md`
5. `README.md`
6. 根级 `AGENTS.md` / `CLAUDE.md`

冲突处理：MCP 工具层执行细节以本模块文档优先，跨模块与全局规则以根级文档优先。

## 5. 文档联动（Docs Drift）
- MCP 工具名称、参数 schema、返回结构变化：同步 `README.md` 与相关模块文档。
- MCP 启动方式或脚本默认值变化：同步 `docs/start-here.md`、`docs/runbook-local.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。

## 6. Hooks 对齐
- pre-commit：`./scripts/quality_gate.sh --mode pre-commit`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope staged`）。
- pre-push：`./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope push`）。
