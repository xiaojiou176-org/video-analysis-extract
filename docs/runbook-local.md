# Local Runbook (Non-Docker, Phase3)

本文是本仓库本地运行的权威步骤文档，和 `README.md` 保持同一套 6 步口径。

## 标准环境约束（AI/自动化必须）

- AI 执行 lint/test/live smoke 必须在标准环境完成：`.devcontainer/devcontainer.json`。
- 基础设施编排真相源固定为：`infra/compose/core-services.compose.yml` 与 `infra/compose/miniflux-nextflux.compose.yml`。
- 若不使用 DevContainer，必须提供等价隔离环境（依赖版本、工具链、Compose 服务拓扑一致），否则验证结果不具备门禁效力。

进入标准环境：
```bash
devcontainer up --workspace-folder .
```

## 环境分层与优先级（Core/Profile Overlay）

- Core baseline：`.env`（API/Worker/MCP/Web 默认运行配置）
- Profile overlay：
  - `PROFILE=local|gce`（决定 bootstrap 运行画像）
  - `.env.reader-stack`（仅 reader 相关命令加载）
- Secret injection policy：密钥仅允许来自 `.env` 或进程环境；禁止依赖 `.env.local` / `.env.bak` / 登录配置。

变量优先级（按当前脚本实现）：
1. 脚本内显式保留/覆盖逻辑（如 `e2e_live_smoke.sh` 对 API 路由变量的保留）
2. `.env`（`load_repo_env` 加载）
3. 继承自父 shell 的同名变量
4. 代码默认值（仅可选项）

Reader overlay 规则：
- `.env.reader-stack` 不会全局生效，仅在 reader 栈命令路径生效（`deploy_reader_stack.sh`、reader 检查/同步链路）。
- 启用 reader 栈时，建议显式指定 `--env-file .env.reader-stack`。

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
- 运行脚本仅自动加载 `.env`；若需覆盖，请在当前 shell 中显式导出环境变量。
- 环境契约真相源：`ENVIRONMENT.md` + `infra/config/env.contract.json`。

### 4) 初始化数据库（统一迁移命令）
```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

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

### 手动触发日报与失败告警
```bash
./scripts/run_daily_digest.sh
./scripts/run_failure_alerts.sh
```

常用覆盖参数：
```bash
DIGEST_DATE=2026-02-21 DIGEST_TO_EMAIL='you@example.com' ./scripts/run_daily_digest.sh
FAILURE_LOOKBACK_HOURS=6 FAILURE_LIMIT=10 FAILURE_TO_EMAIL='you@example.com' ./scripts/run_failure_alerts.sh
```

### 清理 workflow（媒体与缓存）
```bash
WORKER_COMMAND=start-cleanup-workflow ./scripts/dev_worker.sh --run-once --older-than-hours 24
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
OPS_DAILY_LOCAL_HOUR=9 \
OPS_DAILY_TIMEZONE=Asia/Shanghai \
OPS_NOTIFICATION_INTERVAL_MINUTES=5 \
OPS_NOTIFICATION_RETRY_BATCH_LIMIT=100 \
OPS_CANARY_INTERVAL_HOURS=1 \
OPS_CANARY_TIMEOUT_SECONDS=8 \
OPS_CLEANUP_INTERVAL_HOURS=6 \
OPS_CLEANUP_OLDER_THAN_HOURS=24 \
./scripts/start_ops_workflows.sh >> ./logs/ops/workflows.log 2>&1
```

3. 常用环境变量
- `OPS_DAILY_LOCAL_HOUR`：日报触发小时（默认回退 `DIGEST_DAILY_LOCAL_HOUR`，再回退 `9`）。
- `OPS_DAILY_TIMEZONE`：IANA 时区（默认回退 `DIGEST_LOCAL_TIMEZONE`，再回退 `system-local`）。
- `OPS_DAILY_TIMEZONE_OFFSET_MINUTES`：可选，显式 UTC 偏移分钟。
- `OPS_NOTIFICATION_INTERVAL_MINUTES`：重试扫描间隔分钟（默认 `10`）。
- `OPS_NOTIFICATION_RETRY_BATCH_LIMIT`：单次重试批量上限（默认 `50`）。
- `OPS_CANARY_INTERVAL_HOURS`：可用性探针间隔小时（默认 `1`）。
- `OPS_CANARY_TIMEOUT_SECONDS`：探针超时秒数（默认 `8`，最小 `3`）。
- `OPS_CLEANUP_INTERVAL_HOURS`：cleanup 轮询间隔小时（默认 `6`）。
- `OPS_CLEANUP_OLDER_THAN_HOURS`：媒体/帧文件保留小时（默认 `24`）。
- `OPS_CLEANUP_CACHE_OLDER_THAN_HOURS`：可选，cache 文件按年龄清理阈值。
- `OPS_CLEANUP_CACHE_MAX_SIZE_MB`：可选，cache 清理后体积上限。
- `OPS_CLEANUP_WORKSPACE_DIR` / `OPS_CLEANUP_CACHE_DIR`：可选，覆盖默认目录。安全限制：仅允许落在 `${REPO_ROOT}/.runtime-cache`、`${REPO_ROOT}/cache`、`${REPO_ROOT}/.cache`、`/tmp/video-digestor*`、`/tmp/video-analysis*` 前缀下，超出白名单会直接失败。
- `OPS_DAILY_WORKFLOW_ID` / `OPS_NOTIFICATION_WORKFLOW_ID` / `OPS_CANARY_WORKFLOW_ID` / `OPS_CLEANUP_WORKFLOW_ID`：固定 workflow id，用于“已运行则不重复启动”。
- `OPS_DAILY_RUN_ONCE=1` / `OPS_NOTIFICATION_RUN_ONCE=1` / `OPS_CANARY_RUN_ONCE=1` / `OPS_CLEANUP_RUN_ONCE=1`：改为单次执行（排障时使用，生产常驻建议保持 `0`）。
- `OPS_SHOW_HINTS=0`：关闭脚本启动摘要日志（默认 `1`）。
- `OPS_DRY_RUN=1`：只打印命令不执行（等价 `./scripts/start_ops_workflows.sh --dry-run`）。
- `DEV_WORKER_SHOW_HINTS=0`：关闭 `dev_worker.sh` 的大段提示，适合 cron/守护进程日志。

4. 调度互斥策略（必须执行）
- 方案 A：使用 cron（`run_daily_digest.sh` / `run_failure_alerts.sh`），则不要启动对应常驻 workflow。
- 方案 B：使用 `start_ops_workflows.sh` 常驻模式（推荐），则停用上述 cron 条目。
- cleanup 建议统一走常驻 workflow，不建议额外 cron 重复触发 `start-cleanup-workflow`。

5. 脚本可用性快速验证
```bash
bash -n scripts/start_ops_workflows.sh
./scripts/start_ops_workflows.sh --help
./scripts/start_ops_workflows.sh --dry-run
```

6. 告警与重试调优建议（基于现有能力）
- 投递重试策略已内置指数退避：`2/5/15/30/60` 分钟，最多 `5` 次；`auth/config_error` 不会继续重试。
- 建议将 `OPS_NOTIFICATION_INTERVAL_MINUTES` 设为 `3-10` 分钟；高流量场景可配合 `OPS_NOTIFICATION_RETRY_BATCH_LIMIT=100-300`，避免 backlog 累积。
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

`full_stack.sh` 运行约束（稳定性修复）：
- `up` 后台拉起 API 时会强制 `DEV_API_RELOAD=0`，避免 `uvicorn --reload` 父子进程漂移导致 `status`/`down` 误判。
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
- `bootstrap_full_stack.sh` 默认启用 `WITH_CORE_SERVICES=1` 和 `WITH_READER_STACK=1`。
- `smoke_full_stack.sh` 默认启用 `FULL_STACK_REQUIRE_READER=1`，并会执行 `run_ai_feed_sync.sh` 验证 AI 文本回写 Miniflux。

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
- 兼容字段：`steps[].thought_metadata` 为归一化兼容提取位（含 `llm_meta.thinking`），未命中时返回空结构（非 `null`）。

## 文档联动规则
以下改动必须同步本文件：
- 新增迁移文件（`infra/migrations/*.sql`）
- 环境变量契约调整
- 启动脚本参数或默认值调整
