# 视频分析提取 (Phase3)

本仓库是本地优先的视频分析系统，包含 `API + Worker + MCP + Web` 四层：
- `apps/api`：FastAPI 控制面，提供 `/api/v1/*`
- `apps/worker`：Temporal worker，执行 poll + pipeline
- `apps/mcp`：FastMCP 工具层，转发 API 能力
- `apps/web`：Next.js 管理台

## 处理流程（统一口径）

`ProcessJobWorkflow` 由 3 个阶段组成：
1. `mark_running`
2. `run_pipeline_activity`（固定 8 steps）
3. `mark_succeeded` 或 `mark_failed`

8-step pipeline：
1. `fetch_metadata`
2. `download_media`
3. `collect_subtitles`
4. `collect_comments`
5. `extract_frames`
6. `llm_outline`
7. `llm_digest`
8. `write_artifacts`

状态机细节见 `docs/state-machine.md`。

## 模型策略（Gemini-only）

- Provider 固定为 `gemini`，`llm_outline`/`llm_digest` 不支持其他 provider。
- 结构化输出固定为 JSON：`response_mime_type=application/json` + schema 校验（严格 `extra=forbid`）。
- Function calling：
  - `llm_outline` / `llm_digest` 启用工具（证据引用与帧选择）。
  - 翻译回退路径关闭 function calling。
- Thinking 策略：
  - 默认由 `GEMINI_THINKING_LEVEL` 控制。
  - 请求级可通过 `overrides.llm.thinking_level` 覆盖。
- Context cache：
  - 由 `GEMINI_CONTEXT_CACHE_ENABLED/TTL_SECONDS/MIN_CHARS` 控制。
- Media resolution 入口：
  - `PIPELINE_LLM_INPUT_MODE`（`auto|text|video_text|frames_text`）
  - `PIPELINE_MAX_FRAMES` 与 `overrides.frames.max_frames`
  - 运行态 `llm_media_input`（`video_available`, `frame_count`）

### Embedding / Retrieval 入口

- Embedding 配置入口：`GEMINI_EMBEDDING_MODEL`
- Retrieval 入口（当前阶段）：`GET /api/v1/jobs/{job_id}` 的 `artifacts_index`（MCP `vd.jobs.get` 同步暴露）

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
python scripts/check_env_contract.py --strict
set -a; source .env; set +a
```

说明：`scripts/dev_*.sh` 和 `scripts/run_*.sh` 会优先自动加载仓库根目录 `.env`；仅当 `.env` 缺失时才回退 `.env.local`。

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

### 6) 最小验收
```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 5}'
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
PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q

uv run --with playwright python -m playwright install chromium
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

## 文档导航
- 总入口：`docs/index.md`
- 本地运维：`docs/runbook-local.md`
- 状态机：`docs/state-machine.md`
- 环境治理：`ENVIRONMENT.md`
- 引用文档：`docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`
