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
- `db-migration-smoke` / `python-tests` / `api-real-smoke` / `pr-llm-real-smoke` / `backend-lint` / `frontend-lint` / `web-test-build` / `web-e2e` / `external-playwright-smoke`：依赖 `preflight` 并行执行（其中 `pr-llm-real-smoke` 为条件触发）。
- `api-real-smoke`：PR 可运行的真实 API 轻量烟测（启动 FastAPI + Postgres，覆盖 `/healthz` 与 subscriptions 写读链路），不依赖外部 provider secrets。
- `web-e2e`：增量浏览器策略。PR 仅跑 core（chromium/firefox）；`main` push 与 nightly schedule 跑 full（含 webkit）。默认使用本地 mock API，不访问真实外部网站。
- `aggregate-gate`：汇总 `preflight + 10` 个核心作业（`db-migration-smoke` / `python-tests` / `api-real-smoke` / `pr-llm-real-smoke` / `backend-lint` / `frontend-lint` / `web-test-build` / `web-e2e` / `external-playwright-smoke` / `dependency-vuln-scan`）；其中 `pr-llm-real-smoke` 允许 `success/skipped`，其余任一非 `success` 即失败。
- `autofix-dry-run`：依赖 `python-tests` + `web-e2e`，仅在两者任一失败时运行（读取 `.runtime-cache` 诊断工件）。
- `nightly-flaky-python` + `nightly-flaky-web-e2e`：仅 nightly schedule 触发，执行重复运行策略用于发现 flaky。
- `live-smoke`：依赖 `aggregate-gate`，在 `main` push / nightly schedule 必跑；执行真实 LLM + 真实外部视频 URL（YouTube/Bilibili）链路。若缺少 `LIVE_SMOKE_API_BASE_URL` 或任一必需 secret 会直接失败（不再跳过放行）。
- `ci-final-gate`：最终门禁；始终检查 `aggregate-gate`，并在 nightly 强制 `nightly-flaky-*` 成功，在 `main` push / nightly schedule 强制 `live-smoke` 成功且不得为 `skipped`。

## 测试类型与依赖边界（避免误解）

| 测试/作业 | 默认依赖类型 | 是否真实外部依赖 | 是否需要 secrets |
|---|---|---|---|
| `python-tests` | 以单测/组件测试为主（含 monkeypatch） | 否 | 否 |
| `api-real-smoke` | 真实 FastAPI + 真实 Postgres + 真实 migration | 否（不打外部 provider） | 否 |
| `pr-llm-real-smoke` | PR 条件触发的真实 LLM 接口烟测（`/api/v1/computer-use/run`） | 是（调用真实 Gemini） | 是（仅 `GEMINI_API_KEY`） |
| `web-e2e` | Playwright UI 行为验证 + mock API | 否（默认不打外网） | 否 |
| `web-e2e` + `WEB_BASE_URL` | Playwright 复用外部 Web 实例 | 取决于目标实例 | 通常否 |
| `external-playwright-smoke` | Playwright 直连外部公共站点（`https://example.com`） | 是（真实外网） | 否（默认值由 job 参数提供，可按脚本参数覆盖） |
| `live-smoke` | 真实 `/api/v1/videos/process` + 真实 provider 链路 | 是（YouTube/Bilibili + Gemini/Resend） | 是（CI 主干必需） |

`pr-llm-real-smoke` 触发条件（PR 可选真实 LLM）：
- 仅 `pull_request` 事件。
- 仅同仓 PR（`head.repo.full_name == github.repository`），fork PR 不触发。
- 且仓库配置了 `GEMINI_API_KEY` secret；否则该 job 为 `skipped`，不阻塞 aggregate gate。

CI `live-smoke` 必需 secrets（`main` push / nightly schedule）：
- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `YOUTUBE_API_KEY`
- `LIVE_SMOKE_API_BASE_URL`

## 真实 Smoke 默认值与触发边界（与 CI 对齐）

- `pr-llm-real-smoke` 仅在以下条件同时满足时触发：
  - `github.event_name == 'pull_request'`
  - `github.event.pull_request.head.repo.full_name == github.repository`（同仓 PR，fork PR 不触发）
  - `secrets.GEMINI_API_KEY != ''`
- `external-playwright-smoke` 在 `preflight` 后固定执行，默认参数：
  - `--url https://example.com`
  - `--browser chromium`
  - `--expect-text "Example Domain"`
  - `--timeout-ms 45000`
  - `--output-dir .runtime-cache/external-playwright-smoke`
  - `--retries` 未显式传入时使用脚本默认值 `2`，且 live 策略强制最大值 `2`

Live 诊断与执行策略（本地/CI 一致）：
- 环境变量优先级：先读仓库 `.env`（无 `.env` 才读 `.env.local`），仅在缺失时回退 `zsh` login 环境变量。
- `YOUTUBE_API_KEY` 失效修复：`e2e_live_smoke.sh` 会按 `.env` → `.env.bak` → `.env.local` → `zsh` 自动探测可用 key，并在修复成功后回写 `.env`（日志仅展示脱敏 key 片段）。
- 若所有来源都无效：脚本直接失败，并输出“需要用户提供有效key”。
- 失败分类：诊断 JSON 必须携带 `failure_kind`，取值为 `code_logic_error` 或 `network_or_environment_timeout`。
- 长任务可观测：live 脚本输出 heartbeat 与 phase 进度日志（`phase=short_tests` / `phase=long_tests`）。
- 顺序规则：先 short tests 再 long tests，再执行 `phase=teardown`（仅做安全清理，不做破坏性操作）。
- 写操作约束：live smoke 仅执行可重复验证写入；诊断 JSON 必须包含 `write_operations[].idempotency_key`、`write_operations[].cleanup_action`、`teardown.steps[]`、`youtube_key_resolution[]`。

## 本地复现两类真实 Smoke（CI 同口径）

1. 复现 `external-playwright-smoke`：

```bash
uv sync --frozen --extra dev --extra e2e
uv run --with playwright python -m playwright install --with-deps chromium
uv run --with playwright bash scripts/external_playwright_smoke.sh \
  --url "https://example.com" \
  --browser "chromium" \
  --expect-text "Example Domain" \
  --timeout-ms "45000" \
  --output-dir ".runtime-cache/external-playwright-smoke"
```

2. 复现 `pr-llm-real-smoke`：

```bash
export GEMINI_API_KEY='<your-key>'
export DATABASE_URL='sqlite+pysqlite:////tmp/video-digestor-pr-llm-real-smoke.db'
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'
export TEMPORAL_NAMESPACE='default'
export TEMPORAL_TASK_QUEUE='video-analysis-worker'
export SQLITE_STATE_PATH='/tmp/video-digestor-pr-llm-real-state.db'
export NOTIFICATION_ENABLED='0'
export UI_AUDIT_GEMINI_ENABLED='false'
export VD_ALLOW_UNAUTH_WRITE='1'

mkdir -p .runtime-cache
uv run --with uvicorn uvicorn apps.api.app.main:app --host 127.0.0.1 --port 18081 > .runtime-cache/pr-llm-real-smoke.log 2>&1 &
api_pid=$!
trap 'kill ${api_pid} >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:18081/healthz" >/dev/null && break
  sleep 1
done
scripts/smoke_llm_real_local.sh --api-base-url "http://127.0.0.1:18081"
```

## Full-stack 本地自测（稳定性）

```bash
./scripts/full_stack.sh up
./scripts/full_stack.sh status
./scripts/full_stack.sh down
./scripts/full_stack.sh status
```

说明：
- `up` 会等待 API health 与 Web 端口就绪，失败时输出 `logs/full-stack/*.log` 关键片段，便于快速定位。
- 后台 `up` 场景默认关闭 API reload（`DEV_API_RELOAD=0`），避免 `status` 因 reload 父子进程变化误判 `stopped`。

## 触发差异（PR vs main vs nightly）

| 触发源 | 必跑项 | 可跳过项 | 强制门禁 |
|---|---|---|---|
| `pull_request` | `preflight`、`aggregate-gate` 依赖链、`web-e2e(core)`、`api-real-smoke`、`external-playwright-smoke`；`pr-llm-real-smoke` 满足条件时运行 | `live-smoke`（跳过） | `ci-final-gate` 允许 `live-smoke=skipped`；`pr-llm-real-smoke` 允许 `skipped` |
| `push` 到 `main` | `preflight`、`aggregate-gate` 依赖链、`web-e2e(full)`、`api-real-smoke`、`external-playwright-smoke`、`live-smoke` | `pr-llm-real-smoke`、nightly flaky 子集 | `ci-final-gate` 强制 `live-smoke=success` |
| `schedule` nightly | `preflight`、`aggregate-gate` 依赖链、`web-e2e(full)`、`api-real-smoke`、`external-playwright-smoke`、`live-smoke`、`nightly-flaky-*` | `pr-llm-real-smoke` | `ci-final-gate` 强制 `live-smoke=success` 且 `nightly-flaky-*` 全部成功 |

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

默认策略（阻断）：
- 全仓 Lint 错误必须为 0（`npm --prefix apps/web run lint` + `uv run --with ruff ruff check apps scripts`）。
- 禁止安慰剂断言（`python3 scripts/check_test_assertions.py --path .`）。
- Secrets 泄漏扫描必须通过（`sk-*` / `ghp_*` / `AKIA*` / 私钥头模式）。
- 空洞日志文案扫描必须通过（禁止 `Something went wrong` / `unexpected error` / `error occurred` / `unknown error`）。
- 文档漂移门禁强制执行（staged/push）。
- 覆盖率阈值：总覆盖率 `>=80%`，核心模块覆盖率 `>=95%`（worker pipeline + api 核心 router/service）。
- 变异测试门禁强制执行（Python 核心模块）：mutation score `>=0.60`（默认，可通过 `--mutation-min-score` 覆盖）。
- `pre-push` 采用 fail-fast：先短检查，再长测试；长测试并行执行并输出 heartbeat。

### 0.2) Git Hook 强制门禁（commit-msg / pre-commit / pre-push）

```bash
./scripts/install_git_hooks.sh
```

提交信息本地校验（Conventional Commits）：

```bash
echo "feat(api): add ingest health guard" > /tmp/commit-msg-ok.txt
.githooks/commit-msg /tmp/commit-msg-ok.txt
```

### 0.3) Hooks 与文档联动规则对齐（必须执行）

当前 Git Hooks 的实际检查项：

- `commit-msg`：
  - `npx --yes --package @commitlint/cli commitlint --config <tmp-config> --edit <commit-msg-file>`
  - 规则基于 Conventional Commits（例如 `feat: ...`、`fix(scope): ...`）。
  - 仓库根目录无 `package.json` 时，使用 `npx --yes` 临时拉取 `commitlint` + hook 内置最小规则配置，无需新增根依赖即可运行。
- `pre-commit`：
  - `python3 scripts/check_test_assertions.py --path .`
  - secrets 泄漏扫描（阻断）
  - `bash scripts/ci_or_local_gate_doc_drift.sh --scope staged`
  - `npm --prefix apps/web run lint`
  - `uv run --with ruff ruff check apps scripts`
- `pre-push`：
  - `python3 scripts/check_env_contract.py --strict`
  - `bash scripts/ci_or_local_gate_doc_drift.sh --scope push`
  - `python3 scripts/check_test_assertions.py --path .`
  - secrets 泄漏扫描（阻断）
  - `npm --prefix apps/web run lint`
  - `uv run --with ruff ruff check apps scripts`
  - `npm --prefix apps/web run test -- --coverage`
  - `uv run pytest ... --cov-fail-under=80`
  - `uv run coverage report ... --fail-under=95`（worker core / api core）
  - `DATABASE_URL='sqlite+pysqlite:///:memory:' uv run --extra dev --with mutmut mutmut run`
  - `uv run --extra dev --with mutmut mutmut export-cicd-stats`
  - `python3 -c '...读取 mutants/mutmut-cicd-stats.json 并校验 score>=阈值...'`（默认阈值 `0.60`）

变异测试工具不可用策略（阻断）：
- 若 `uv` 不可用：直接失败并提示安装 `uv`，禁止静默跳过。
- 若 `mutmut` 安装/执行失败：直接失败并提示执行 `uv sync --frozen --extra dev --extra e2e`。
- 若无有效突变体（`killed + survived == 0`）：直接失败，视为门禁无效配置。

文档联动强制规则（提交时人工校验，hooks 不会自动补）：

- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md`。
- 变更 `apps/worker/worker/pipeline/types.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 调整 API 行为或签名（`apps/api/app/routers/*.py`、`apps/api/app/services/*.py`、`apps/mcp/**/*.py`）：同步 `README.md`、`docs/runbook-local.md`、`docs/testing.md`。
- 调整 Schema 签名（`apps/mcp/schemas/tools.json`、`packages/shared-contracts/jsonschema/*.json`）：同步 `docs/testing.md`。
- 调整本地启动脚本参数/默认值（`scripts/dev_*.sh`、`scripts/full_stack.sh`、`scripts/bootstrap_full_stack.sh`、`scripts/smoke_full_stack.sh`）：同步 `docs/start-here.md`、`docs/runbook-local.md`、`README.md`。
- 调整日志/缓存/依赖策略：同步 `docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`。

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
