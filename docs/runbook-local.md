# Local Runbook (Non-Docker, Phase3)

本文是本仓库本地运行的权威步骤文档，和 `README.md` 保持同一套 6 步口径。

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
python scripts/check_env_contract.py --strict
set -a; source .env; set +a
```

说明：
- `scripts/dev_api.sh`、`scripts/dev_worker.sh`、`scripts/dev_mcp.sh`、`scripts/run_daily_digest.sh`、`scripts/run_failure_alerts.sh` 均会优先自动加载 `.env`。
- 只有 `.env` 不存在时才回退加载 `.env.local`（兼容路径）。
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
DIGEST_DATE=2026-02-21 DIGEST_TO_EMAIL="$NOTIFY_TO_EMAIL" ./scripts/run_daily_digest.sh
FAILURE_LOOKBACK_HOURS=6 FAILURE_LIMIT=10 FAILURE_TO_EMAIL="$NOTIFY_TO_EMAIL" ./scripts/run_failure_alerts.sh
```

### 清理 workflow（媒体与缓存）
```bash
WORKER_COMMAND=start-cleanup-workflow ./scripts/dev_worker.sh --run-once --older-than-hours 24
```

缓存策略细节见 `docs/reference/cache.md`。

### 调度（cron）
```cron
0 9 * * * /bin/bash -lc 'cd "<repo-path>" && ./scripts/run_daily_digest.sh >> ./logs/daily_digest.log 2>&1'
*/30 * * * * /bin/bash -lc 'cd "<repo-path>" && ./scripts/run_failure_alerts.sh >> ./logs/failure_alerts.log 2>&1'
```

## 常见故障
- `API health check failed`：确认 `./scripts/dev_api.sh` 已运行，且 `VD_API_BASE_URL` 可访问。
- `RESEND_API_KEY is not configured` / `RESEND_FROM_EMAIL is not configured`：`NOTIFICATION_ENABLED=true` 时需补齐 `.env`（或仅在兼容模式下补齐 `.env.local`）。
- 404 报表路由：`run_daily_digest.sh` / `run_failure_alerts.sh` 会按脚本内 fallback 流程回退发送。

## LLM 能力入口（Gemini-only）

- Provider 固定：Gemini（`llm_outline`/`llm_digest`）。
- Thinking：`GEMINI_THINKING_LEVEL` + `overrides.llm.thinking_level`。
- Structured Output：固定 JSON + schema 校验。
- Function Calling：outline/digest 开启，翻译回退关闭。
- Context Cache：`GEMINI_CONTEXT_CACHE_ENABLED`、`GEMINI_CONTEXT_CACHE_TTL_SECONDS`、`GEMINI_CONTEXT_CACHE_MIN_CHARS`。
- Media Resolution：`PIPELINE_LLM_INPUT_MODE`、`PIPELINE_MAX_FRAMES`、`overrides.frames.max_frames`、`llm_media_input`。
- Embedding / Retrieval：`GEMINI_EMBEDDING_MODEL`；检索入口为 `jobs.artifacts_index`。

## 文档联动规则
以下改动必须同步本文件：
- 新增迁移文件（`infra/migrations/*.sql`）
- 环境变量契约调整
- 启动脚本参数或默认值调整
