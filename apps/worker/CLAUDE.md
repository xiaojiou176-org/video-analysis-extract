# apps/worker 模块协作规范

## 0. 模块目的
- 本模块负责视频处理主流水线执行：poll、pipeline、状态写回、产物生成。
- 本模块必须与 Temporal 协作，严格执行 `3 阶段 + 9-step pipeline`。

## 1. 技术栈
- Python 3.11+
- Temporal worker
- pytest

## 2. 导航索引（Lazy-Load）
1. `apps/worker/worker/main.py`（worker 入口）
2. `apps/worker/worker/pipeline/`（流程编排）
3. `apps/worker/worker/temporal/`（workflow/activities）
4. `apps/worker/tests/`（模块测试）

## 3. 质量门禁（MUST）

### 3.1 模块命令
```bash
./scripts/dev_worker.sh

PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests -q
```

### 3.2 强制规则
1. 涉及 pipeline 行为改动时，必须通过 `apps/worker/tests`。
2. 涉及 `PIPELINE_STEPS` 改动时，必须同步 `docs/state-machine.md` 并完成对应验证。
3. 涉及跨模块改动时，必须遵循根门禁：env contract + backend pytest + web lint + fake assertion gate。
4. 涉及启动/链路改动时，必须补一次 `./scripts/smoke_full_stack.sh` 或在交付中说明未执行原因。

## 4. 文档优先级（模块内）
1. `apps/worker/AGENTS.md`
2. `apps/worker/CLAUDE.md`
3. `docs/state-machine.md`
4. `docs/start-here.md`
5. `docs/runbook-local.md`
6. 根级 `AGENTS.md` / `CLAUDE.md`

冲突处理：worker 行为契约以 `docs/state-machine.md` 与本模块文档优先，跨模块与全局规则以根级文档优先。

## 5. 文档联动（Docs Drift）
- 修改 `apps/worker/worker/pipeline/types.py` 中 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 调整 worker 启动参数、运行路径或脚本默认值：同步 `docs/start-here.md`、`docs/runbook-local.md`、`README.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。

## 6. Hooks 对齐
- pre-commit：`./scripts/quality_gate.sh --mode pre-commit`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope staged`）。
- pre-push：`./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope push`）。
