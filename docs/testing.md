# Testing Guide (Wave4)

## Scope

本次 Wave4 增加了以下测试骨架：

- `apps/worker/tests`
- `apps/api/tests`
- `apps/mcp/tests`
- `apps/web/tests/e2e`

所有新增测试都包含至少一个真实行为断言（字段或状态码），不使用安慰剂断言。

## CI Topology (GitHub Actions)

- `offline-gate`：主门禁（env contract、迁移、python tests、web lint/build、web e2e）。
- `autofix-dry-run`：依赖 `offline-gate`，仅在测试失败时运行（读取 `.runtime-cache` 诊断工件）。
- `live-smoke`：依赖 `offline-gate`，仅在必需 secrets 存在时运行。
- `autofix-dry-run` 与 `live-smoke` 在 `offline-gate` 后可并发执行。

## Run Commands

### 1) Python tests (worker/api/mcp, xdist=2)

```bash
PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run \
  --with pytest \
  --with pytest-xdist \
  --with fastapi \
  --with httpx \
  --with sqlalchemy \
  --with psycopg \
  --with pydantic \
  --with mcp \
  pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -n 2
```

### 1.1) MCP jobs normalizer（重点）

```bash
PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run \
  --with pytest \
  --with fastapi \
  --with httpx \
  --with sqlalchemy \
  --with psycopg \
  --with pydantic \
  --with mcp \
  pytest apps/mcp/tests/test_tool_normalizers.py -q
```

该用例应覆盖 `vd.jobs.get` 归一化后的关键字段保留：
- `steps`
- `degradations`
- `pipeline_final_status`
- `llm_required`
- `llm_gate_passed`
- `hard_fail_reason`
- `artifacts_index`
- `mode`

### 2) Playwright E2E

```bash
uv run --with playwright playwright install chromium

uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

说明：
- E2E 用例会自动启动本地 Next.js Web（`apps/web`）并注入本地 mock API，不依赖真实后端或外部 API。
- 运行前需确保 `apps/web/node_modules` 已安装（例如先执行 `cd apps/web && npm ci`）。

外部 Base URL 模式（复用已有 Web 实例，不启动本地 Next.js）：

```bash
WEB_BASE_URL='http://127.0.0.1:3000' \
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

说明：
- `WEB_BASE_URL` 必须是绝对 `http(s)` URL。
- 使用外部模式时，请确保目标 Web 已启动且其 API 指向与测试预期一致。

### 3) Web 静态检查

```bash
cd apps/web
npm run lint
```

## Notes

- `apps/web/tests/e2e/test_smoke_playwright.py` 覆盖关键按钮链路（dashboard / subscriptions / settings / jobs->artifacts），并对重定向提示与请求负载做强断言。
- 由于当前 Web 代码尚未完成 Next.js 16 `searchParams` 异步迁移，`jobs -> artifacts` 用例会先断言查询跳转与页面占位状态（`No artifact loaded yet.`）；迁移后可升级为 markdown/screenshot 区块可见性断言。
- API 路由测试会通过 `monkeypatch` 隔离 Temporal/数据库外部依赖，验证路由层映射行为。
- 需要访问真实依赖（Postgres/Temporal）的端到端链路，可在后续补专门的 integration 套件。
- CI 缓存策略：Node 使用 `setup-node` 的 npm 缓存（锁文件 `apps/web/package-lock.json`）；Python 采用 `uv sync --frozen`（当前 workflow 未配置独立 Python cache）；测试与 e2e 产物统一写入 `.runtime-cache` 并作为 artifact 上传。
