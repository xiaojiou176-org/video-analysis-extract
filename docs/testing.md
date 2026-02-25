# Testing Guide (Wave4)

## Scope

本次 Wave4 增加了以下测试骨架：

- `apps/worker/tests`
- `apps/api/tests`
- `apps/mcp/tests`
- `apps/web/tests/e2e`

所有新增测试都包含至少一个真实行为断言（字段或状态码），不使用安慰剂断言。

## CI Topology (GitHub Actions)

- `preflight`：预检门禁（env contract、provider residual guard、schema parity、worker file line limits）。
- `db-migration-smoke` / `python-tests` / `api-real-smoke` / `backend-lint` / `frontend-lint` / `web-test-build` / `web-e2e`：依赖 `preflight` 并行执行。
- `api-real-smoke`：PR 可运行的真实 API 轻量烟测（启动 FastAPI + Postgres，覆盖 `/healthz` 与 subscriptions 写读链路），不依赖外部 provider secrets。
- `web-e2e`：增量浏览器策略。PR 仅跑 core（chromium/firefox）；`main` push 与 nightly schedule 跑 full（含 webkit）。
- `aggregate-gate`：汇总上述五个作业结果，任一非 `success` 即失败。
- `autofix-dry-run`：依赖 `python-tests` + `web-e2e`，仅在两者任一失败时运行（读取 `.runtime-cache` 诊断工件）。
- `nightly-flaky-python` + `nightly-flaky-web-e2e`：仅 nightly schedule 触发，执行重复运行策略用于发现 flaky。
- `live-smoke`：依赖 `aggregate-gate`，在 `main` push / nightly schedule 必跑；若缺少 `LIVE_SMOKE_API_BASE_URL` 或任一必需 secret 会直接失败（不再跳过放行）。
- `ci-final-gate`：最终门禁；始终检查 `aggregate-gate`，并在 nightly 强制 `nightly-flaky-*` 成功，在 `main` push / nightly schedule 强制 `live-smoke` 成功且不得为 `skipped`。

## Run Commands

### 0) 假断言门禁（全仓）

```bash
python3 scripts/check_test_assertions.py
```

说明：
- 默认禁止 `expect(true).toBe(true)`、`expect("x").toEqual("x")`、`expect(1).toBe(1)` 等左右同字面量断言。
- 默认禁止 `toBeDefined()`；如确有必要，可在同一行或上一行添加注释标记：
  `// allow-low-value-assertion: toBeDefined`

### 0.1) 一键质量门禁（推荐）

```bash
./scripts/quality_gate.sh
```

### 0.2) Git Hook 强制门禁（pre-commit / pre-push）

```bash
./scripts/install_git_hooks.sh
```

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
- CI 缓存策略：Node 使用 `setup-node` 的 npm 缓存（锁文件 `apps/web/package-lock.json`）；Python 使用 `actions/cache@v4` 缓存 `~/.cache/uv`，并配合 `uv sync --frozen`；测试与 e2e 产物统一写入 `.runtime-cache` 并作为 artifact 上传。
