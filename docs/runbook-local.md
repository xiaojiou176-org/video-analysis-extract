# Local Runbook (Non-Docker, Phase3)

## 1) 本机依赖
先安装并确认以下依赖可用：
- PostgreSQL 16
- Redis
- Temporal CLI / Temporal dev server
- Python 3（建议同一环境下可运行 API + Worker + MCP）

macOS(Homebrew) 示例：
```bash
brew update
brew install postgresql@16 redis temporal
```

Python 运行时最小导入检查（可在你的虚拟环境内执行）：
```bash
python3 - <<'PY'
import fastapi, uvicorn, sqlalchemy, psycopg, temporalio, httpx
print('python deps ok')
PY
```

## 2) 启动本机服务
```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

## 3) Phase3 关键环境变量
建议先从模板生成并编辑：
```bash
./scripts/init_env_example.sh
cp .env.local.example .env.local
```

核心配置示例：
```bash
export DATABASE_URL='postgresql+psycopg://localhost:5432/video_analysis'
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'
export TEMPORAL_NAMESPACE='default'
export TEMPORAL_TASK_QUEUE='video-analysis-worker'

export SQLITE_PATH="$HOME/.video-digestor/state/worker_state.db"
export SQLITE_STATE_PATH="$HOME/.video-digestor/state/worker_state.db"
export PIPELINE_WORKSPACE_DIR="$HOME/.video-digestor/workspace"
export PIPELINE_ARTIFACT_ROOT="$HOME/.video-digestor/artifacts"
export PIPELINE_RETRY_ATTEMPTS='2'
export PIPELINE_RETRY_BACKOFF_SECONDS='1.0'
export PIPELINE_SUBPROCESS_TIMEOUT_SECONDS='180'
export PIPELINE_MAX_FRAMES='6'
export PIPELINE_FRAME_INTERVAL_SECONDS='30'
export GEMINI_API_KEY='<optional>'
export GEMINI_MODEL='gemini-1.5-flash'

# Phase3 pipeline 关键参数（重试 + 锁 + 拉取）
export RSSHUB_BASE_URL='https://rsshub.app'
export REQUEST_TIMEOUT_SECONDS='15'
export REQUEST_RETRY_ATTEMPTS='3'
export REQUEST_RETRY_BACKOFF_SECONDS='0.5'
export LOCK_TTL_SECONDS='90'

export VD_API_BASE_URL='http://127.0.0.1:8000'
export VD_API_TIMEOUT_SEC='20'

# Resend（仅在 NOTIFICATION_ENABLED=true 时必填）
export NOTIFICATION_ENABLED='true'
export RESEND_API_KEY='<required-when-enabled>'
export RESEND_FROM_EMAIL='Video Digestor <noreply@example.com>'
export NOTIFY_TO_EMAIL='you@example.com'
```

说明：
- `scripts/dev_api.sh`、`scripts/dev_worker.sh`、`scripts/dev_mcp.sh`、`scripts/run_daily_digest.sh`、`scripts/run_failure_alerts.sh` 会自动加载 `.env.local`（如果存在）。
- 变量契约见 `ENVIRONMENT.md` 和 `infra/config/env.contract.json`。

## 4) 初始化数据库
```bash
createdb video_analysis || true
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000001_init.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000002_phase3_artifacts.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000003_phase4_observability.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000004_notifications.sql
# 000005 / 000006 请按实际文件名替换占位符，必须按序执行
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000005_<name>.sql
psql postgresql://localhost:5432/video_analysis -f infra/migrations/20260221_000006_<name>.sql
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

## 5) 启动应用进程
分别在 3 个终端启动：
```bash
./scripts/dev_api.sh
./scripts/dev_worker.sh
./scripts/dev_mcp.sh
```

## 6) 最小验收（API + Worker + SQLite 账本）
1. 健康检查：
```bash
curl -s http://127.0.0.1:8000/healthz
```

2. 写入一个订阅（示例）：
```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/subscriptions \
  -H 'Content-Type: application/json' \
  -d '{"platform":"youtube","source_type":"youtube_channel_id","source_value":"UC_x5XG1OV2P6uZZ5FSM9Ttw"}'
```

3. 触发 poll：
```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/ingest/poll \
  -H 'Content-Type: application/json' \
  -d '{"max_new_videos": 20}'
```

4. 取一个 `job_id` 后查询 job：
```bash
curl -sS http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

4.1 触发处理工作流（带 mode 配置）：
```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/videos/process \
  -H 'Content-Type: application/json' \
  -d '{
    "video": {"platform":"youtube","url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    "mode":"text_only",
    "overrides":{"llm":{"temperature":0.2}},
    "force":false
  }'
```

4.2 查询 `jobs.get` 时重点关注字段：
- `step_summary`（步骤摘要）
- `steps`（步骤详情）
- `degradations`（降级记录）
- `pipeline_final_status`（最终流水线状态）
- `artifacts_index`（产物索引）
- `mode`（处理模式）

5. 校验 step 账本与 checkpoint：
```bash
sqlite3 "$SQLITE_PATH" "SELECT job_id, step_name, status, attempt, started_at, finished_at FROM step_runs ORDER BY started_at DESC LIMIT 20;"
sqlite3 "$SQLITE_PATH" "SELECT job_id, last_completed_step, updated_at FROM checkpoints ORDER BY updated_at DESC LIMIT 10;"
```

## 7) Phase3 行为验收（retry / cache / degrade）
- Retry：临时设置 `REQUEST_RETRY_ATTEMPTS=1` 与 `REQUEST_RETRY_BACKOFF_SECONDS=0.1`，观察 worker 日志重试次数变化。
- Cache(去重)：对同一订阅连续触发两次 poll，第二次通常 `enqueued` 更低（常见为 0）。
- Degrade：当 lock 被占用时，poll 返回 `{"ok":true,"skipped":true,"reason":"lock_not_acquired"}`，worker 不崩溃。
- 产物：执行 `POST /api/v1/videos/process` 后，可通过 `GET /api/v1/artifacts/markdown?job_id=...` 读取 digest。

可用以下方式模拟锁占用（可选）：
```bash
sqlite3 "$SQLITE_PATH" "INSERT OR REPLACE INTO locks(lock_key, owner, expires_at) VALUES('phase2.poll_feeds', 'manual-test', datetime('now', '+5 minutes'));"
WORKER_COMMAND=start-poll-workflow ./scripts/dev_worker.sh --max-new-videos 1
```

## 8) 初始化本机 env 示例（推荐）
使用脚本生成可直接修改的模板：

```bash
./scripts/init_env_example.sh
cp .env.local.example .env.local
# 编辑 .env.local，填入 RESEND_API_KEY / RESEND_FROM_EMAIL / NOTIFY_TO_EMAIL
```

## 9) 手动触发每日汇总与失败告警
```bash
# 每日汇总（优先 /api/v1/reports/daily/send，不可用时自动 fallback）
./scripts/run_daily_digest.sh

# 失败告警（优先失败告警专用路由，不可用时自动 fallback）
./scripts/run_failure_alerts.sh
```

常用覆盖变量：
```bash
# Daily digest
DIGEST_DATE=2026-02-21 DIGEST_TO_EMAIL="$NOTIFY_TO_EMAIL" ./scripts/run_daily_digest.sh

# Failure alerts
FAILURE_LOOKBACK_HOURS=6 FAILURE_LIMIT=10 FAILURE_TO_EMAIL="$NOTIFY_TO_EMAIL" ./scripts/run_failure_alerts.sh
```

## 10) cron 示例（本机）
先确认使用绝对路径（下方替换成你的本机路径）：

```bash
crontab -e
```

示例：
```cron
# 每天 09:00 发送每日汇总
0 9 * * * /bin/bash -lc 'cd "/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取" && ./scripts/run_daily_digest.sh >> ./logs/daily_digest.log 2>&1'

# 每 30 分钟发送失败告警汇总
*/30 * * * * /bin/bash -lc 'cd "/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取" && ./scripts/run_failure_alerts.sh >> ./logs/failure_alerts.log 2>&1'
```

> 建议先 `mkdir -p logs`，避免 cron 首次写日志失败。

## 11) launchd 示例（macOS）
创建两个 plist（示例文件名）：

```bash
mkdir -p ~/Library/LaunchAgents
```

`~/Library/LaunchAgents/com.video-digestor.daily-digest.plist`（每日 09:00）核心片段：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.video-digestor.daily-digest</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd "/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取" &amp;&amp; ./scripts/run_daily_digest.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/video_digest_daily.log</string>
  <key>StandardErrorPath</key><string>/tmp/video_digest_daily.err.log</string>
</dict>
</plist>
```

加载/卸载：
```bash
launchctl unload ~/Library/LaunchAgents/com.video-digestor.daily-digest.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.video-digestor.daily-digest.plist
launchctl list | grep video-digestor
```

失败告警可复制一份 plist 并改成 `run_failure_alerts.sh` + `StartInterval`（例如 `1800` 秒）。

## 12) 常见故障排查
- `status=404` 且日志提示 primary route unavailable：当前 API 未暴露对应 reports/alerts 路由，脚本会自动 fallback；如你不想 fallback，设置 `DIGEST_FALLBACK_ENABLED=0` 或 `FAILURE_FALLBACK_ENABLED=0`。
- `notification recipient email is not configured`：先 `PUT /api/v1/notifications/config` 设置 `to_email`，或在脚本里传 `DIGEST_TO_EMAIL/FAILURE_TO_EMAIL`。
- `RESEND_API_KEY is not configured` / `RESEND_FROM_EMAIL is not configured`：当 `NOTIFICATION_ENABLED=true` 时，补齐 `.env.local` 对应变量。
- `API health check failed`：确认 `./scripts/dev_api.sh` 已启动，且 `VD_API_BASE_URL` 指向可访问地址。
- `Fallback send failed` 且返回 503：通常是 Resend 调用失败，检查外网、Key、发件域名配置与 API 响应 body。
