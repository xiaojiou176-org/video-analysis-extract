# 视频分析提取 (Phase3)

本仓库是本地优先的视频分析系统，包含 `API + Worker + MCP + Web` 四层：

- `apps/api`：FastAPI 控制面，提供 `/api/v1/*`
- `apps/worker`：Temporal worker，执行 poll + pipeline
- `apps/mcp`：FastMCP 工具层，转发 API 能力
- `apps/web`：Next.js 管理台

## 项目目的

- 将视频内容处理为可操作的结构化信息：拉取、解析、摘要、检索、分发。
- 提供统一入口给自动化与人工操作：API（服务）、MCP（工具）、Web（管理台）。
- 保持本地优先与可验证交付：命令可复现，测试/门禁可追溯。

## 技术栈总览

- 后端：Python、FastAPI、SQLAlchemy
- 任务执行：Temporal Worker（9-step pipeline）
- 工具层：FastMCP
- 前端：Next.js
- 存储：PostgreSQL + SQLite（状态）+ Redis（可选）
- 质量门禁：uv、pytest、Playwright、ruff、npm lint/test、git hooks

## 1 分钟入口

先读 `docs/start-here.md`。它是唯一上手入口，聚合了启动命令、口径说明和后续文档导航。

## Clone 后快速跑通（推荐）

```bash
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

这三步会把仓库拉到“可运行 + 可验证”的状态（本地优先）。

说明：

- `bootstrap_full_stack.sh` 默认会拉起 core services（Postgres/Redis/Temporal）和 reader stack（Miniflux/Nextflux）。
- `smoke_full_stack.sh` 默认会校验 reader stack，并执行一次 `AI Feed -> Miniflux` 回写检查。
- 若你临时不想检查 reader：`FULL_STACK_REQUIRE_READER=0 ./scripts/smoke_full_stack.sh`

## IaC 与标准环境（AI 必须）

仓库当前可复现环境方案：

- Docker Compose（基础设施真相源）：`infra/compose/core-services.compose.yml`、`infra/compose/miniflux-nextflux.compose.yml`
- DevContainer（AI/自动化标准执行环境）：`.devcontainer/devcontainer.json`

推荐进入标准环境后再执行 lint/test/live smoke：

```bash
# 1) 在 VS Code 里执行: Dev Containers: Reopen in Container
# 或使用 devcontainer CLI:
devcontainer up --workspace-folder .

# 2) 在容器内执行（统一口径）
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

运行风险说明：

- 现有 `scripts/deploy_core_services.sh` 与 `scripts/deploy_reader_stack.sh` 已直接绑定上述 compose 文件，不需要改脚本。
- 风险 1：DevContainer 依赖宿主 Docker（通过 `/var/run/docker.sock`），若宿主未启动 Docker，容器内 compose 无法拉起。
- 风险 2：live smoke 依赖真实外部 API Key（如 `GEMINI_API_KEY`），标准环境只保证执行一致性，不保证外部资源可用。
- 风险 3：本地裸机与容器混用时，端口/数据库残留状态可能不一致；建议同一轮验证只使用一种环境执行。

## 处理流程（统一口径）

`ProcessJobWorkflow` 由 3 个阶段组成：

1. `mark_running`
2. `run_pipeline_activity`（固定 9 steps）
3. `mark_succeeded` 或 `mark_failed`

9-step pipeline：

1. `fetch_metadata`
2. `download_media`
3. `collect_subtitles`
4. `collect_comments`
5. `extract_frames`
6. `llm_outline`
7. `llm_digest`
8. `build_embeddings`
9. `write_artifacts`

状态机细节见 `docs/state-machine.md`。

## 模型策略（Gemini-only）

- Provider 固定为 `gemini`，`llm_outline`/`llm_digest` 不支持其他 provider。
- 结构化输出固定为 JSON：`response_mime_type=application/json` + schema 校验（严格 `extra=forbid`）。
- Function calling：
  - `llm_outline` / `llm_digest` 启用工具（证据引用与帧选择）。
  - 翻译回退路径关闭 function calling。
- Computer Use（函数调用回合）安全闸：
  - 仅允许 `select_supporting_frames` 与 `build_evidence_citations` 两个工具；非白名单调用会被标记 `blocked`。
  - `computer_use` 入口由 `GEMINI_COMPUTER_USE_*` 与 `overrides.llm*.enable_computer_use` 控制；当 `enable_computer_use=true` 且未显式提供 handler 时，pipeline 会默认注入 `build_default_computer_use_handler`。
  - `computer_use_require_confirmation` 默认 `true`；即使未来接入 handler，未确认也会返回 `computer_use_confirmation_required`。
  - 最大调用回合由 `max_function_call_rounds` 控制（默认 `2`，可由 `overrides.llm.max_function_call_rounds` / `overrides.llm_outline.max_function_call_rounds` / `overrides.llm_digest.max_function_call_rounds` 覆盖）。
  - 达到上限后以 `termination_reason=max_function_call_rounds_reached` 结束当前轮。
- Thinking 策略：
  - 默认由 `GEMINI_THINKING_LEVEL` 控制。
  - 复杂任务强制 `include_thoughts=true`；缺少 thought signatures 视为硬失败。
  - 请求级可通过 `overrides.llm.thinking_level` 覆盖。
- Context cache：
  - 由 `GEMINI_CONTEXT_CACHE_ENABLED/TTL_SECONDS/MIN_CHARS` 控制。
- Media resolution 入口：
  - 支持 `low|medium|high|ultra_high`。
  - `PIPELINE_LLM_INPUT_MODE`（`auto|text|video_text|frames_text`）
  - `PIPELINE_MAX_FRAMES` 与 `overrides.frames.max_frames`
  - 运行态 `llm_media_input`（`video_available`, `frame_count`）

### Embedding / Retrieval 入口

- Embedding 配置入口：`GEMINI_EMBEDDING_MODEL`
- Retrieval 入口（当前阶段）：`GET /api/v1/jobs/{job_id}` 的 `artifacts_index`（MCP `vd.jobs.get` 同步暴露）

### Thought Metadata / Signatures 可见性

- API：`GET /api/v1/jobs/{job_id}` 的 `steps[].result.llm_meta.thinking` 包含：
  - `thought_count`
  - `thought_signatures`
  - `thought_signature_digest`
  - `usage`（token 统计）
- MCP：`vd.jobs.get` 保留同结构字段（位于 `steps[].result`）。
- 兼容字段：`steps[].thought_metadata` 统一归一化为稳定结构，兼容来源 `result.thought_metadata|thinking_metadata|thoughts_metadata|thoughts|llm_meta.thinking`；无数据时返回空结构（非 `null`）。

## 本地运行（标准 6 步）

### 1) 安装依赖

前置：Python 3.11+、`uv`、PostgreSQL 16、Temporal dev server、(可选) Redis。

```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

### 2) 启动基础服务

```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3) 初始化环境变量

```bash
./scripts/init_env_example.sh
cp .env.example .env
python3 scripts/check_env_contract.py --strict
set -a; source .env; set +a
```

说明：`scripts/dev_*.sh` 和 `scripts/run_*.sh` 只自动加载仓库根目录 `.env`；额外配置请通过当前 shell 环境变量显式注入。
补充：`.env.example` 已精简为最小可启动模板；脚本参数全集请查看 `docs/reference/env-script-overrides.md`。

### 4) 初始化数据库

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

### 5) 启动应用进程

分别在 3 个终端启动：

```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

脚本入口参数（Batch C）：

- `./scripts/dev_api.sh --app apps.api.app.main:app --no-reload`
- `./scripts/dev_worker.sh --worker-dir "$PWD/apps/worker" --entry worker.main --command run-worker --no-show-hints`
- `./scripts/dev_mcp.sh --entry apps.mcp.server --mcp-dir "$PWD/apps/mcp"`
- `./scripts/init_env_example.sh --output "$PWD/.env.generated.example" --force`

### 6) 最小验收

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 20}'
```

`GET /api/v1/jobs/{job_id}` 与 `vd.jobs.get` 稳定字段：

- `step_summary`
- `steps`
- `degradations`
- `pipeline_final_status`
- `artifacts_index`
- `mode`

## 测试入口

```bash
python3 scripts/check_test_assertions.py

./scripts/quality_gate.sh

./scripts/install_git_hooks.sh

PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q

uv run --with playwright python -m playwright install chromium
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

注：`scripts/check_test_assertions.py` 默认禁止 `toBeDefined()`；仅在特例场景下允许用注释标记 `allow-low-value-assertion: toBeDefined` 显式豁免。

测试与门禁口径更新（2026-02）：

- CI 预检拆分为 `preflight-fast` + `preflight-heavy`，多数 job 先依赖 fast 以减少起跑阻塞，最终由 aggregate gate 同时约束两者成功。
- `quality-gate-pre-push` 在 `main/schedule` 采用 `--ci-dedupe 1` 并透传 `--changed-*` 标记，避免与独立 lint/unit/coverage 作业重复执行。
- Web E2E 默认轻量化：trace 默认 `off`、video 默认 `retain-on-failure`，并仅在失败时上传重工件。
- 测试分层主责明确：API 负责字段级契约断言，Web E2E 聚焦用户旅程，MCP 聚焦工具语义与路由动作。

## Git Hooks 与 pre-commit 协同（初始化与保养）

默认执行链路（当前仓库真相）：

- `.githooks/pre-commit`、`.githooks/pre-push`、`.githooks/commit-msg` 是 Git 生命周期入口。
- 以上 hook 通过 `scripts/quality_gate.sh` 与 `commitlint` 执行强制门禁。
- `.pre-commit-config.yaml` 定义的是可复用检查集合，默认不由 `.githooks` 直接调用。

首次初始化（推荐）：

```bash
./scripts/install_git_hooks.sh
```

可选：如果你要直接启用 pre-commit framework hook（会写入当前 `core.hooksPath` 的 hook 文件）：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Big Bang 全量清洗（建议在大改前执行一次）：

```bash
pre-commit run --all-files
```

detect-secrets baseline（可选补充；当前强制 secrets 门禁仍是 gitleaks）：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

月度保养（建议每月一次）：

```bash
pre-commit autoupdate
pre-commit run --all-files
```

测试口径补充（与 CI 对齐）：

- `web-e2e` 默认是 Playwright + mock API，不是“真实外部网站 smoke”。
- `external-playwright-smoke` 是独立作业，会在 CI 里真实访问外部站点（当前为 `https://example.com`），用于验证浏览器外网可达性。
  默认参数：`browser=chromium`、`expect_text="Example Domain"`、`timeout_ms=45000`、`retries=2`。
- `pr-llm-real-smoke` 只在 PR 场景按条件运行：同仓 PR 且配置了 `GEMINI_API_KEY`；否则允许 `skipped` 不阻塞 aggregate gate。
  触发表达式与 CI 一致：`pull_request && same-repo-pr && GEMINI_API_KEY != ''`。
- 若要复用外部 Web 实例，可用：`WEB_BASE_URL='http://127.0.0.1:3000' uv run --with pytest --with playwright pytest apps/web/tests/e2e -q`。
- PR 不强制 `live-smoke`；`main` push 与 nightly schedule 强制 `live-smoke=success`。
- `live-smoke` 为真实 LLM/provider 链路，CI 需要：`GEMINI_API_KEY`、`RESEND_API_KEY`、`RESEND_FROM_EMAIL`、`YOUTUBE_API_KEY`、`LIVE_SMOKE_API_BASE_URL`。
- `scripts/smoke_full_stack.sh` 是本地联调用 smoke，不等同于 CI 强制 `live-smoke` 门禁。
- 两类真实 smoke 的本地复现命令见 `docs/testing.md` 的“本地复现两类真实 Smoke（CI 同口径）”。

## API 路由与管理端点契约

系统与业务路由（FastAPI）：

- `GET /healthz`
- `GET /api/v1/subscriptions`
- `POST /api/v1/subscriptions`
- `POST /api/v1/subscriptions/batch-update-category`
- `DELETE /api/v1/subscriptions/{id}`
- `GET /api/v1/feed/digests`
- `POST /api/v1/ingest/poll`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/videos`
- `POST /api/v1/videos/process`
- `GET /api/v1/notifications/config`
- `PUT /api/v1/notifications/config`
- `POST /api/v1/notifications/test`
- `POST /api/v1/notifications/category/send`
- `POST /api/v1/reports/daily/send`
- `GET /api/v1/artifacts/markdown`
- `GET /api/v1/artifacts/assets`
- `GET /api/v1/health/providers`
- `POST /api/v1/workflows/run`
- `POST /api/v1/retrieval/search`
- `POST /api/v1/computer-use/run`
- `POST /api/v1/ui-audit/run`
- `GET /api/v1/ui-audit/{run_id}`
- `GET /api/v1/ui-audit/{run_id}/findings`
- `GET /api/v1/ui-audit/{run_id}/artifacts`
- `GET /api/v1/ui-audit/{run_id}/artifact`
- `POST /api/v1/ui-audit/{run_id}/autofix`

管理端点鉴权（由 `VD_API_KEY` + `VD_ALLOW_UNAUTH_WRITE` 控制）：

- 默认安全模式：即使 `VD_API_KEY` 为空或未设置，写操作也要求令牌。
- 仅当 `VD_ALLOW_UNAUTH_WRITE=true` 且 `VD_API_KEY` 为空时，才允许无令牌写操作（本地兼容开关）。
- 以下端点必须携带令牌，否则返回 `401/403`：
  - `POST /api/v1/subscriptions`
  - `POST /api/v1/subscriptions/batch-update-category`
  - `DELETE /api/v1/subscriptions/{id}`
  - `POST /api/v1/ingest/poll`
  - `POST /api/v1/videos/process`
  - `PUT /api/v1/notifications/config`
  - `POST /api/v1/notifications/test`
  - `POST /api/v1/notifications/category/send`
  - `POST /api/v1/reports/daily/send`
  - `POST /api/v1/workflows/run`
  - `POST /api/v1/computer-use/run`
  - `POST /api/v1/ui-audit/run`
  - `POST /api/v1/ui-audit/{run_id}/autofix`
- 支持两种传递方式：
  - `Authorization: Bearer <VD_API_KEY>`
  - `X-API-Key: <VD_API_KEY>`

## P1 新增能力（2026-02-23）

- Subscriptions 支持分类与标签：
  - 字段：`category`（`tech|creator|macro|ops|misc`）、`tags`（字符串数组）
  - API：
    - `GET /api/v1/subscriptions?category=tech`
    - `POST /api/v1/subscriptions` 支持 `category/tags`
- Notifications 支持分类规则与按分类发送：
  - 配置字段：`category_rules`（JSON）
  - 新接口：`POST /api/v1/notifications/category/send`

## P2 新增能力（2026-02-23）

- 来源适配器化（Subscriptions）：
  - 新字段：`adapter_type`（`rsshub_route|rss_generic`）、`source_url`
  - 行为：
    - `adapter_type=rsshub_route`：沿用 `rsshub_route`（兼容旧行为）
    - `adapter_type=rss_generic`：直接使用 `source_url` 拉取 RSS
  - 目标：从平台硬编码输入逐步迁移到 `adapter + source_url` 模式。

## 可选：Reader Stack（Miniflux + Nextflux）

如果你要“AI 处理流水线 + 漂亮阅读器 UI + 多端访问”，仓库已内置可选部署栈：

- Compose: `infra/compose/miniflux-nextflux.compose.yml`
- 脚本: `scripts/deploy_reader_stack.sh`
- GCE 指南: `docs/deploy/miniflux-nextflux-gce.md`

快速启动：

```bash
# 编辑 env/profiles/reader.env，至少设置 MINIFLUX_DB_PASSWORD / MINIFLUX_ADMIN_PASSWORD / MINIFLUX_BASE_URL
./scripts/deploy_reader_stack.sh up --env-file env/profiles/reader.env
./scripts/deploy_reader_stack.sh status --env-file env/profiles/reader.env
```

## 可选：实时稳定推送 workflow

仓库内置 `scripts/start_ops_workflows.sh`，用于一次性启动/确保以下长期运行 workflow：

- `daily_digest`
- `notification_retry`
- `provider_canary`
- `cleanup_workspace`

基础用法：

```bash
./scripts/start_ops_workflows.sh
```

常用参数：

```bash
OPS_DAILY_LOCAL_HOUR=9 \
OPS_DAILY_TIMEZONE=Asia/Shanghai \
OPS_NOTIFICATION_INTERVAL_MINUTES=5 \
OPS_NOTIFICATION_RETRY_BATCH_LIMIT=100 \
OPS_CANARY_INTERVAL_HOURS=1 \
OPS_CANARY_TIMEOUT_SECONDS=8 \
OPS_CLEANUP_INTERVAL_HOURS=6 \
OPS_CLEANUP_OLDER_THAN_HOURS=24 \
./scripts/start_ops_workflows.sh
```

完整参数说明见 `docs/runbook-local.md`。

## 文档导航

- 1 分钟入口：`docs/start-here.md`
- 总入口：`docs/index.md`
- 本地运维：`docs/runbook-local.md`
- 状态机：`docs/state-machine.md`
- 环境治理：`ENVIRONMENT.md`
- 环境分层与优先级：`ENVIRONMENT.md`（`Core/Profile Overlay Architecture`）
- 旧环境迁移指引：`ENVIRONMENT.md`（`Migration Guide: Legacy .env.example -> Core/Profile Overlay`）
- 引用文档：`docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`
- MCP 路由：`docs/reference/mcp-tool-routing.md`（13 工具、action 路由、组合示例）
- 仓库完善蓝图：`Repo_Next_Step_Plan.md`
- 证据链审计报告：`Repo完善与证据链报告.md`
