# Local Runbook (Non-Docker, Phase3)

本文是本仓库本地运行的权威步骤文档，和 `README.md` 保持同一套 6 步口径。

## 标准环境约束（AI/自动化必须）

- AI 执行 lint/test/live smoke 必须在标准环境完成：`.devcontainer/devcontainer.json`。
- 基础设施编排真相源固定为：`infra/compose/core-services.compose.yml`（使用 `pgvector/pgvector:pg16` 镜像支持向量检索扩展）与 `infra/compose/miniflux-nextflux.compose.yml`。
- 若不使用 DevContainer，必须提供等价隔离环境（依赖版本、工具链、Compose 服务拓扑一致），否则验证结果不具备门禁效力。

进入标准环境：

```bash
devcontainer up --workspace-folder .
```

## 环境分层与优先级（Core/Profile Overlay）

- Core baseline：`.env`（API/Worker/MCP/Web 默认运行配置）
- Profile overlay：
  - 通过 `--profile local|gce` 选择脚本运行画像
  - `env/profiles/reader.env`（reader profile 模板）
- Secret injection policy：密钥仅允许来自 `.env` 或进程环境；禁止依赖 shell 登录配置。

变量优先级（按当前脚本实现）：

1. 脚本内显式保留/覆盖逻辑（如 `e2e_live_smoke.sh` 对 API 路由变量的保留）
2. 继承自父 shell 的同名变量（`load_repo_env` 最后恢复 shell 快照）
3. `.env`/`env/core.env`/`env/profiles/<profile>.env`（`load_repo_env` 加载）
4. 代码默认值（仅可选项）

Reader overlay 规则：

- reader env 不会全局生效，仅在 reader 栈命令路径生效（`deploy_reader_stack.sh`、reader 检查/同步链路）。
- 启用 reader 栈时，建议显式指定 `--env-file env/profiles/reader.env`。

## 标准启动链路（6 步）

### 1) 安装依赖与前置

前置：PostgreSQL 16、Temporal dev server、Python 3.11+、`uv`、(可选) Redis。

macOS 示例：

```bash
brew update
brew install postgresql@16 redis temporal
```

安装依赖：

```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

### 1.1) 初始化 Git 质量门禁（建议首次 clone 后执行）

```bash
./scripts/install_git_hooks.sh
```

可选：安装 pre-commit framework hooks（会写入当前 `core.hooksPath`）：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

协同关系（当前实现）：

- `.githooks/*` 是默认强制入口，负责调用 `quality_gate` 与 `commitlint`。
- `.pre-commit-config.yaml` 是可复用检查清单，主要用于手动执行全量检查与依赖版本保养。
- 因此本仓库口径是：`.githooks` 负责“提交/推送阻断”，`pre-commit` 负责“批量清洗与工具链维护”。

质量门禁提速口径（2026-02）：

- `quality_gate.sh` 支持 `--changed-backend|web|deps|migrations` 与 `--ci-dedupe`。
- pre-commit 的 `auto` 使用 staged diff；pre-push 的 `auto` 优先使用 upstream merge-base diff，失败回退 `HEAD~1..HEAD`，无法可靠识别时保守回退为全量检查。
- 本地 pre-push 默认使用变更感知门禁：后端变更命中时强制 mutation，无后端变更时跳过 mutation 以避免无效本地消耗。
- 在 CI 的 dedupe 模式中，`quality-gate-pre-push` 作为远端最重门禁执行（后端变更命中时含 mutation），lint/unit/coverage 由独立 CI job 并行交叉验证。
- 本地 pre-push 会额外执行 `api cors preflight smoke (OPTIONS DELETE)` 与 `contract diff local gate (base vs head)`，用于在推送前发现跨端 CORS 与接口契约回归。
- 成本治理约束：重跑远程 CI 前，必须先本地通过 pre-push；若远程失败，先本地复现修复再重跑，禁止连续重跑碰运气。

Big Bang 全量清洗（可选）：

```bash
pre-commit run --all-files
```

detect-secrets baseline（可选补充；默认强制 secrets 门禁仍是 gitleaks）：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

月度保养（建议）：

```bash
pre-commit autoupdate
pre-commit run --all-files
```

### 2) 启动基础服务

```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3) 初始化环境变量（统一流程）

```bash
./scripts/init_env_example.sh
cp .env.example .env
python3 scripts/check_env_contract.py --strict
set -a; source .env; set +a
```

说明：

- `scripts/dev_api.sh`、`scripts/dev_worker.sh`、`scripts/dev_mcp.sh`、`scripts/run_daily_digest.sh`、`scripts/run_failure_alerts.sh` 均会优先自动加载 `.env`。
- 运行脚本会加载 repo env 文件；若需覆盖，以当前 shell 中显式导出的环境变量为准。
- 环境契约真相源：`ENVIRONMENT.md` + `infra/config/env.contract.json`。

### 4) 初始化数据库（统一迁移命令）

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

说明：`20260222_000010_phase4_status_contract.sql` 在加新约束前会先归一化历史脏状态（含旧 `partial` 语义），用于避免历史库迁移失败。

### 5) 启动应用进程

分别在 3 个终端运行：

```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

### 6) 最小验收

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll \
  -H 'Content-Type: application/json' \
  -d '{"max_new_videos": 20}'
```

可选：查询 job 详情（稳定字段）

```bash
curl -sS http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

## 可选操作

### 发布前证据与回滚清单

```bash
python3 scripts/release/generate_release_prechecks.py
python3 scripts/build_release_readiness_report.py \
  --kpi-json reports/release-readiness/ci-kpi-summary.json \
  --check-json .runtime-cache/temp/release-readiness/prechecks.json

scripts/release/capture_release_manifest.sh <release-tag>

python3 scripts/release/verify_db_rollback_readiness.py \
  --release-tag <release-tag> \
  --output reports/releases/<release-tag>/rollback/db-rollback-readiness.json
```

说明：该门禁会同时检查 `missing_policy`、`blocked_without_down` 与 `invalid_down_sql`，任一大于 0 都会阻断发版。

### 手动触发日报与失败告警

```bash
./scripts/run_daily_digest.sh
./scripts/run_failure_alerts.sh
```

常用覆盖参数：

```bash
./scripts/run_daily_digest.sh --date 2026-02-21 --to-email 'you@example.com'
./scripts/run_failure_alerts.sh --lookback-hours 6 --limit 10 --to-email 'you@example.com'
```

### 清理 workflow（媒体与缓存）

```bash
./scripts/dev_worker.sh --command start-cleanup-workflow --run-once --older-than-hours 24
```

缓存策略细节见 `docs/reference/cache.md`。

### 调度（cron）

注意：`cron` 与下方“实时稳定推送（常驻 workflow）”必须二选一，避免重复触发同类任务。

```cron
0 9 * * * /bin/bash -lc 'cd "<repo-path>" && ./scripts/run_daily_digest.sh >> ./logs/daily_digest.log 2>&1'
*/30 * * * * /bin/bash -lc 'cd "<repo-path>" && ./scripts/run_failure_alerts.sh >> ./logs/failure_alerts.log 2>&1'
```

### 实时稳定推送（生产建议）

仓库内置了 `scripts/start_ops_workflows.sh`，用于一次性启动/确保以下长期运行 workflow：

- `daily_digest`（日报）
- `notification_retry`（失败投递重试）
- `provider_canary`（上游可用性探针）
- `cleanup_workspace`（媒体与缓存清理）

该脚本复用现有 worker CLI（`start-daily-workflow` / `start-notification-retry-workflow` / `start-provider-canary-workflow` / `start-cleanup-workflow`），默认适配本地非 Docker 运行。

1. 基础用法

```bash
./scripts/start_ops_workflows.sh
```

2. 推荐参数（生产）

```bash
mkdir -p logs logs/ops
./scripts/start_ops_workflows.sh \
  --daily-local-hour 9 \
  --daily-timezone Asia/Shanghai \
  --notification-interval-minutes 5 \
  --notification-retry-batch-limit 100 \
  --canary-interval-hours 1 \
  --canary-timeout-seconds 8 \
  --cleanup-interval-hours 6 \
  --cleanup-older-than-hours 24 \
  --daily-workflow-id daily-digest-workflow \
  --notification-workflow-id notification-retry-workflow \
  --canary-workflow-id provider-canary-workflow \
  --cleanup-workflow-id cleanup-workspace-workflow \
  --show-hints >> ./logs/ops/workflows.log 2>&1
```

3. 常用 CLI 参数

- `--daily-workflow-id` / `--notification-workflow-id` / `--canary-workflow-id` / `--cleanup-workflow-id`：固定 workflow id，用于“已运行则不重复启动”。
- `--daily-run-once` / `--notification-run-once` / `--canary-run-once` / `--cleanup-run-once`：改为单次执行（排障时使用，生产常驻建议默认关闭）。
- `--daily-local-hour` / `--daily-timezone`：日报调度时间配置。
- `--notification-interval-minutes` / `--notification-retry-batch-limit`：失败投递重试节流配置。
- `--canary-interval-hours` / `--canary-timeout-seconds`：provider 可用性探针频率与超时。
- `--cleanup-interval-hours` / `--cleanup-older-than-hours`：清理调度与保留窗口。
- `--cleanup-cache-older-than-hours` / `--cleanup-cache-max-size-mb`：可选 cache 细粒度保留。
- `--cleanup-workspace-dir` / `--cleanup-cache-dir`：可选目录覆盖。安全限制：仅允许落在 `${REPO_ROOT}/.runtime-cache`、`${REPO_ROOT}/cache`、`${REPO_ROOT}/.cache`、`/tmp/video-digestor*`、`/tmp/video-analysis*` 前缀下，超出白名单会直接失败。
- `--daily-timezone-offset-minutes`：可选，显式 UTC 偏移分钟。
- `--show-hints` / `--no-show-hints`：开关脚本启动摘要日志（默认显示）。
- `--dry-run`：只打印命令不执行（等价 `./scripts/start_ops_workflows.sh --dry-run`）。

5. 调度互斥策略（必须执行）

- 方案 A：使用 cron（`run_daily_digest.sh` / `run_failure_alerts.sh`），则不要启动对应常驻 workflow。
- 方案 B：使用 `start_ops_workflows.sh` 常驻模式（推荐），则停用上述 cron 条目。
- cleanup 建议统一走常驻 workflow，不建议额外 cron 重复触发 `start-cleanup-workflow`。

4. 脚本可用性快速验证

```bash
bash -n scripts/start_ops_workflows.sh
./scripts/start_ops_workflows.sh --help
./scripts/start_ops_workflows.sh --dry-run
```

5. 告警与重试调优建议（基于现有能力）

- 投递重试策略已内置指数退避：`2/5/15/30/60` 分钟，最多 `5` 次；`auth/config_error` 不会继续重试。
- 建议将 `--notification-interval-minutes` 设为 `3-10` 分钟；高流量场景可配合 `--notification-retry-batch-limit 100-300`，避免 backlog 累积。
- `provider_canary` 每轮会写入 `provider_health_checks`（`rsshub/youtube_data_api/gemini/resend`），建议外部监控以最近 5-10 分钟窗口统计 `status=fail` 或连续 `warn` 触发告警。
- 失败投递会记录在 `notification_deliveries`（含 `attempt_count`、`next_retry_at`、`last_error_kind`），建议对 `status='failed' AND next_retry_at IS NULL` 的记录设置人工告警（通常表示已达上限或配置错误）。

## 一键脚本（Clone 后 80%+ 快速可用）

```bash
./scripts/bootstrap_full_stack.sh
./scripts/full_stack.sh up
./scripts/smoke_full_stack.sh
```

脚本说明：

- `bootstrap_full_stack.sh`：依赖安装、环境校验、数据库迁移、可选 reader stack。
- `full_stack.sh`：统一起停 API/Worker/MCP/Web；`up` 会等待 API health(`GET /healthz`) 与 Web 端口就绪，失败时输出关键服务日志片段。
- `smoke_full_stack.sh`：执行端到端 smoke（含 feed/web 检查，可选 reader 检查）。
- compose 固定默认（不再通过 env 覆盖）：core Postgres `DB/User`、Redis 端口、Temporal 端口；Miniflux `DB/User/DB_NAME` 与 Miniflux 端口。

`full_stack.sh` 运行约束（稳定性修复）：

- `up` 后台拉起 API 时会调用 `./scripts/dev_api.sh --no-reload`，避免 `uvicorn --reload` 父子进程漂移导致 `status`/`down` 误判。
- `status` 会在 PID 文件失真时回退按进程特征探测并自愈 PID 文件。

Live smoke 执行约束（2026-02 更新）：

- 环境变量加载顺序：优先仓库 `.env`，缺失项仅使用当前 shell 环境变量。
- `YOUTUBE_API_KEY` 失效自修复：按 `.env` → 当前 shell 环境变量顺序尝试可用 key；命中后自动回写 `.env`（日志仅输出脱敏片段，不输出完整 key）。
- 若上述来源全部无效：live smoke 会明确失败并提示“需要用户提供有效key”。
- 外部真实交互：`e2e_live_smoke.sh` 会先执行真实外部 API 探测，再执行真实浏览器外站探测（`external_playwright_smoke.sh`）。
- 重试上限：live 脚本网络重试最多 2 次（含首轮）。
- 诊断输出：失败时会写入结构化 JSON，并区分 `code_logic_error` 与 `network_or_environment_timeout`。
- 执行顺序：`short tests first`（health/feed/web/external probe）→ `long tests`（全链路视频处理与同步）→ `teardown`（仅安全清理临时产物）。
- 写操作策略：live 写入仅用于可重复 smoke 验证；诊断 JSON 必须落地 `write_operations[].idempotency_key`、`write_operations[].cleanup_action`、`teardown.steps[]`。

当前默认：

- `bootstrap_full_stack.sh` 默认启用 core services 与 reader stack。
- `smoke_full_stack.sh` 默认执行 reader checks，并会执行 `run_ai_feed_sync.sh` 验证 AI 文本回写 Miniflux。

## 常见故障

- `API health check failed`：确认 `./scripts/dev_api.sh` 已运行，且 `VD_API_BASE_URL` 可访问。
- `RESEND_API_KEY is not configured` / `RESEND_FROM_EMAIL is not configured`：`NOTIFICATION_ENABLED=true` 时需补齐 `.env`（或在当前 shell 中显式导出）。
- 404 报表路由：`run_daily_digest.sh` / `run_failure_alerts.sh` 会按脚本内 fallback 流程回退发送。

## LLM 能力入口（Gemini-only）

- Provider 固定：Gemini（`llm_outline`/`llm_digest`）。
- Thinking：`GEMINI_THINKING_LEVEL` + `overrides.llm.thinking_level`。
- Structured Output：固定 JSON + schema 校验。
- Function Calling：outline/digest 开启，翻译回退关闭。
- Context Cache：`GEMINI_CONTEXT_CACHE_ENABLED`、`GEMINI_CONTEXT_CACHE_TTL_SECONDS`、`GEMINI_CONTEXT_CACHE_MIN_CHARS`。
- Media Resolution：`PIPELINE_LLM_INPUT_MODE`、`PIPELINE_MAX_FRAMES`、`overrides.frames.max_frames`、`llm_media_input`。
- Embedding / Retrieval：`GEMINI_EMBEDDING_MODEL`；检索入口为 `jobs.artifacts_index`。

## Computer Use（函数调用）与安全闸

- 使用入口：`POST /api/v1/videos/process` 的 `overrides.llm*`。
- 安全闸（当前实现）：
  - 仅白名单工具：`select_supporting_frames`、`build_evidence_citations`。
  - 非白名单会记录为 `blocked`，不会执行任意工具。
  - 调用回合上限：`max_function_call_rounds`（默认 `2`）。
  - `computer_use` 开关可配置；当 `enable_computer_use=true` 且未显式提供 handler 时，worker 会默认注入 `build_default_computer_use_handler`。
  - `computer_use_require_confirmation` 默认 `true`，未确认会返回 `computer_use_confirmation_required`。
  - 翻译回退阶段固定关闭 function calling。

示例（限制回合并开启 thought 输出）：

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/videos/process \
  -H 'Content-Type: application/json' \
  -d '{
    "video": {"platform": "youtube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    "mode": "refresh_llm",
    "overrides": {
      "llm": {
        "max_function_call_rounds": 1,
        "include_thoughts": true,
        "enable_computer_use": true
      }
    }
  }'
```

## Thought Metadata / Signatures 可见性

- API：`GET /api/v1/jobs/<job_id>` 的 `steps[].result.llm_meta.thinking` 可见 `thought_signatures` / `thought_signature_digest` / `usage`。
- MCP：`vd.jobs.get` 保留相同结构。
- `steps[].thought_metadata` 为归一化提取字段（含 `llm_meta.thinking`），未命中时返回空结构（非 `null`）。

## 文档联动规则

以下改动必须同步本文件：

- 新增迁移文件（`infra/migrations/*.sql`）
- 环境变量契约调整
- 启动脚本参数或默认值调整

## GCE Instance Scope 最小权限（2026-03）

`scripts/recreate_gce_instance.sh` 已切换为“默认最小权限 scopes”，不再默认 `cloud-platform` 全权限。

- 默认 scopes：
  - `https://www.googleapis.com/auth/devstorage.read_only`
  - `https://www.googleapis.com/auth/logging.write`
  - `https://www.googleapis.com/auth/monitoring.write`
  - `https://www.googleapis.com/auth/service.management.readonly`
  - `https://www.googleapis.com/auth/servicecontrol`
  - `https://www.googleapis.com/auth/trace.append`
- 如需兼容旧行为（全权限），显式传入：
  - `--scopes "https://www.googleapis.com/auth/cloud-platform"`
- 该参数仅用于“已知必须全权限”的运维场景，默认不建议使用。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->


<!-- doc-sync: mcp/web contract and schema alignment (2026-03-03) -->


<!-- doc-sync: mcp api-client redaction fixture adjustment (2026-03-03) -->


<!-- doc-sync: integration smoke uses xfail instead of skip when env unmet (2026-03-03) -->


<!-- doc-sync: ci failure fixes (integration smoke auth + ci_autofix timezone compatibility) (2026-03-03) -->
