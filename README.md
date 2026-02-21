# 视频分析提取 (Phase3)

一个本地优先的多进程系统：
- `API` 负责订阅/任务编排入口（FastAPI）
- `Worker` 负责 RSS 拉取与 8-step 处理流水线（Temporal + 本地状态账本）
- `MCP` 负责对 API 的工具化封装（FastMCP）

## 架构概览

- `apps/api`: 控制面，暴露 `/api/v1/*`。
- `apps/worker`: `PollFeedsWorkflow` + `ProcessJobWorkflow`，执行 pipeline。
- `apps/mcp`: MCP tools，转发 API。
- `PostgreSQL`: 业务真相（subscriptions/videos/ingest_events/jobs）。
- `SQLite`: 运行账本（`step_runs`, `locks`, `checkpoints`）。

流程主链路：
1. `POST /api/v1/ingest/poll` 触发 `PollFeedsWorkflow`
2. 生成并去重 `jobs`
3. 为每个新 job 启动 `ProcessJobWorkflow`
4. Worker 执行 8-step pipeline
5. `jobs` 写回 `artifact_root` / `artifact_digest_md`
6. `GET /api/v1/artifacts/markdown` 读取产物

`GET /api/v1/jobs/{job_id}` / `vd.jobs.get` 统一返回：
- `step_summary`
- `steps`
- `degradations`
- `pipeline_final_status`
- `artifacts_index`
- `mode`

更多细节见：
- `docs/phase3-architecture.md`
- `docs/state-machine.md`
- `docs/runbook-local.md`

## 本地运行

### 1) 依赖

- Python 3.11+
- `uv`（推荐）
- PostgreSQL 16+
- Temporal dev server
- (可选) Redis

macOS 示例：

```bash
brew install postgresql@16 temporal redis
```

### 2) 启动基础服务

```bash
brew services start postgresql@16
brew services start redis

temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3) 环境变量

最小必填：

```bash
export DATABASE_URL='postgresql+psycopg://localhost:5432/video_analysis'
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'
export TEMPORAL_NAMESPACE='default'
export TEMPORAL_TASK_QUEUE='video-analysis-worker'

export SQLITE_PATH="$HOME/.video-digestor/state/worker_state.db"
export SQLITE_STATE_PATH="$HOME/.video-digestor/state/worker_state.db"
export PIPELINE_WORKSPACE_DIR="$HOME/.video-digestor/workspace"
export PIPELINE_ARTIFACT_ROOT="$HOME/.video-digestor/artifacts"

export RSSHUB_BASE_URL='https://rsshub.app'
export REQUEST_TIMEOUT_SECONDS='15'
export REQUEST_RETRY_ATTEMPTS='3'
export REQUEST_RETRY_BACKOFF_SECONDS='0.5'

export VD_API_BASE_URL='http://127.0.0.1:8000'
export VD_API_TIMEOUT_SEC='20'
```

通知相关（可选）：

```bash
export RESEND_API_KEY='<optional>'
export RESEND_FROM_EMAIL='noreply@example.com'
```

### 4) 初始化数据库

```bash
createdb video_analysis || true
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000001_init.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000002_phase3_artifacts.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000003_phase4_observability.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000004_notifications.sql
# 000005 / 000006 请按实际文件名替换占位符，并保持顺序
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000005_<name>.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000006_<name>.sql
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

### 5) 启动应用

三个终端分别执行：

```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

## 测试

> 当前仓库未固定 Python 依赖清单，命令默认使用 `uv run --with ...` 注入测试依赖。

先安装 Playwright 浏览器（仅首次，E2E 需要）：

```bash
uv run --with playwright playwright install chromium
```

### Worker + API + MCP 测试

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
  pytest \
  apps/worker/tests \
  apps/api/tests \
  apps/mcp/tests -q
```

### Web E2E (pytest + Playwright)

```bash
WEB_BASE_URL='http://127.0.0.1:8000/healthz' \
WEB_E2E_EXPECT_TEXT='ok' \
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

- `WEB_BASE_URL` 未设置时，E2E 用例会 `skip`。
- `WEB_BASE_URL` 不可访问时，E2E 用例会 `skip`。

## 测试目录

- `apps/worker/tests`: RSS 解析与标准化
- `apps/api/tests`: API 路由关键行为（healthz / ingest / process）
- `apps/mcp/tests`: API client 错误映射与工具 payload 归一化
- `apps/web/tests/e2e`: Playwright 冒烟链路

## 常用验收命令

```bash
curl -s http://127.0.0.1:8000/healthz
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 5}'
```

## 说明

- 本仓库为非 Docker 本地运行路径，详见 `docs/runbook-local.md`。
- 若需要完整发布门禁，可在后续补 `pyproject.toml` / 锁定依赖版本 / CI 测试工作流。
