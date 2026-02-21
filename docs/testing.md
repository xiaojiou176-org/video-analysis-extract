# Testing Guide (Wave4)

## Scope

本次 Wave4 增加了以下测试骨架：

- `apps/worker/tests`
- `apps/api/tests`
- `apps/mcp/tests`
- `apps/web/tests/e2e`

所有新增测试都包含至少一个真实行为断言（字段或状态码），不使用安慰剂断言。

## Run Commands

### 1) Python tests (worker/api/mcp)

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
  pytest apps/worker/tests apps/api/tests apps/mcp/tests -q
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
