# State Machine (Phase3)

## 运行前置口径（与 README/runbook 一致）
本系统运行前置固定为同一套流程：
1. 安装依赖（`uv sync --frozen --extra dev --extra e2e`）
2. 启动 PostgreSQL / Temporal
3. 初始化 `.env.local` 并校验 env contract
4. 执行全部 SQL 迁移 + SQLite 初始化
5. 启动 API / Worker / MCP
6. 触发最小验收请求

执行命令以 `README.md` 与 `docs/runbook-local.md` 为准。

## Job 状态（`jobs.status`）
- `queued -> running -> succeeded`
- `queued -> running -> partial`
- `queued -> running -> failed`
- `failed -> running`（允许重跑）

## Step Ledger 状态（`sqlite.step_runs.status`）
- `running -> succeeded`
- `running -> failed`
- `running -> skipped`

## Poll Workflow
1. `poll_feeds_activity` 获取锁（`phase2.poll_feeds`）。
2. 拉取订阅 RSS。
3. 标准化 entry（`video_uid` / `entry_hash` / `idempotency_key`）。
4. 写入 `videos` + `ingest_events`，按幂等去重创建 `jobs`。
5. 为每个新 job 启动 `ProcessJobWorkflow`。

## Process Workflow（3 阶段 + 8-step pipeline）

### 阶段 A：运行前标记
- `mark_running`

### 阶段 B：`run_pipeline_activity`（8 steps）
1. `fetch_metadata`
2. `download_media`
3. `collect_subtitles`
4. `collect_comments`
5. `extract_frames`
6. `llm_outline`
7. `llm_digest`
8. `write_artifacts`

### 阶段 C：收敛状态
- 成功/部分成功：`mark_succeeded`
- 致命失败：`mark_failed`

## Process Mode
`POST /api/v1/videos/process` 支持：
- `full`
- `text_only`
- `refresh_comments`
- `refresh_llm`

`mode` 会透传并在 `GET /api/v1/jobs/{job_id}` 与 `vd.jobs.get` 原样返回。

## Process Overrides
`overrides` 当前作用：
- 参与 `jobs.idempotency_key` 计算
- 持久化到 `jobs.overrides_json`
- 调整步骤参数：
  - `comments`: `top_n` / `replies_per_comment` / `sort`
  - `frames`: `method` / `max_frames`
  - `llm`: `model` / `temperature` / `max_output_tokens`

限制：`overrides` 仅调参，不替代 `mode` 的步骤执行矩阵。

## Read Model Contract（API/MCP/Web）
`jobs.get` 稳定字段：
- `step_summary`
- `steps`
- `degradations`
- `pipeline_final_status`
- `artifacts_index`
- `mode`

## Retry Strategy
- RSS 拉取：`REQUEST_RETRY_ATTEMPTS` + `REQUEST_RETRY_BACKOFF_SECONDS`
- 子进程（`yt-dlp`/`ffmpeg`）：`PIPELINE_RETRY_ATTEMPTS` + `PIPELINE_RETRY_BACKOFF_SECONDS`
- Temporal activities：`mark_failed` 最多 1 次，其余按 workflow retry policy
- 通知重试：`NotificationRetryWorkflow` 每 10 分钟扫描失败投递并按退避重试（最多 5 次）

## Daily Digest / Canary / Cleanup
- `DailyDigestWorkflow` 优先使用 IANA `timezone_name`，`timezone_offset_minutes` 仅兜底。
- `ProviderCanaryWorkflow` 默认每小时执行，写入 `provider_health_checks`。
- `CleanupWorkspaceWorkflow` 清理过期媒体与缓存，参数见 `worker.main start-cleanup-workflow`。

## Cache 与 Degrade（摘要）
- 业务层去重：`videos`、`ingest_events`、`jobs.idempotency_key` 唯一约束。
- pipeline step cache：每步基于输入签名命中缓存。
- 可降级失败场景会记录到 `degradations`，最终状态可能为 `partial`。

详细缓存策略见 `docs/reference/cache.md`。
