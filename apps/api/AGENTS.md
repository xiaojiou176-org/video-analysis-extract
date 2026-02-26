# apps/api 模块协作规范

## 0. 模块目的
- 本模块是视频分析系统的 HTTP 控制面，提供 `/healthz` 与 `/api/v1/*`。
- 本模块必须稳定暴露订阅、任务、产物、通知、检索等能力。

## 1. 技术栈
- Python 3.11+
- FastAPI + Pydantic + SQLAlchemy
- pytest

## 2. 导航入口（Lazy-Load）
1. `apps/api/app/main.py`（FastAPI 入口）
2. `apps/api/app/routers/`（路由层）
3. `apps/api/app/services/`（业务服务层）
4. `apps/api/app/repositories/`（数据访问层）
5. `apps/api/tests/`（模块测试）

## 3. 质量门禁（MUST）

### 3.1 模块命令
```bash
./scripts/dev_api.sh

PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/api/tests -q
```

### 3.2 强制规则
1. 涉及 API 逻辑改动时，必须通过 `apps/api/tests`。
2. 涉及跨模块改动时，必须遵循根门禁：env contract + backend pytest + web lint + fake assertion gate。
3. 不允许提交 `expect(true).toBe(true)` 或无效断言测试。
4. 涉及启动/链路改动时，必须补一次 `./scripts/smoke_full_stack.sh` 或在交付中说明未执行原因。

## 4. 文档优先级（模块内）
1. `apps/api/AGENTS.md`
2. `apps/api/CLAUDE.md`
3. `docs/start-here.md`
4. `docs/runbook-local.md`
5. `README.md`
6. 根级 `AGENTS.md` / `CLAUDE.md`

冲突处理：模块执行细节以本文件优先，跨模块与全局规则以根级文档优先。

## 5. 文档联动（Docs Drift）
- API 契约、鉴权或路由行为变化：同步 `README.md`。
- 环境变量变化：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 启动或运行方式变化：同步 `docs/start-here.md`、`docs/runbook-local.md`。

## 6. Hooks 对齐
- pre-commit：`./scripts/quality_gate.sh --mode pre-commit`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope staged`）。
- pre-push：`./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope push`）。
