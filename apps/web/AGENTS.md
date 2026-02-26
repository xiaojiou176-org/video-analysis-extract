# apps/web 模块协作规范

## 0. 模块目的

- 本模块提供视频分析系统的 Web 管理台与操作界面。
- 本模块必须覆盖订阅管理、任务状态、产物查看、设置与交互反馈。

## 1. 技术栈

- Next.js
- TypeScript
- Playwright + Vitest

## 2. 导航索引（Lazy-Load）

1. `apps/web/app/`（App Router 页面与 server actions）
2. `apps/web/components/`（可复用组件）
3. `apps/web/lib/`（API client/工具）
4. `apps/web/tests/e2e/` 与 `apps/web/__tests__/`（测试）
5. `apps/web/app/page.tsx`（首页入口）

## 3. 质量门禁（MUST）

### 3.1 模块命令

```bash
npm --prefix apps/web ci
npm --prefix apps/web run lint
npm --prefix apps/web run test

uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

### 3.2 强制规则

1. 涉及页面、交互、状态流改动时，必须通过 `lint + test`。
2. 涉及 E2E 口径改动时，必须同步 `docs/testing.md`。
3. 涉及跨模块改动时，必须遵循根门禁：env contract + backend pytest + web lint + fake assertion gate。
4. 涉及启动/联调路径改动时，必须补一次 `./scripts/smoke_full_stack.sh` 或在交付中说明未执行原因。

## 4. 文档优先级（模块内）

1. `apps/web/AGENTS.md`
2. `apps/web/CLAUDE.md`
3. `docs/testing.md`
4. `docs/start-here.md`
5. `docs/runbook-local.md`
6. 根级 `AGENTS.md` / `CLAUDE.md`

冲突处理：前端测试口径与执行细节以本模块文档和 `docs/testing.md` 优先，跨模块与全局规则以根级文档优先。

## 5. 文档联动（Docs Drift）

- 页面路由、关键交互路径、测试口径变化：同步 `docs/testing.md` 与 `README.md`。
- 本地启动方式或脚本默认值变化：同步 `docs/start-here.md`、`docs/runbook-local.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。

## 6. Hooks 对齐

- pre-commit：`./scripts/quality_gate.sh --mode pre-commit`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope staged`）。
- pre-push：`./scripts/quality_gate.sh --mode pre-push --heartbeat-seconds 20`（含 `scripts/ci_or_local_gate_doc_drift.sh --scope push`）。
