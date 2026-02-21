# State Machine (Phase3)

## Job State (`jobs.status`)
- `queued -> running -> succeeded`
- `queued -> running -> partial`
- `queued -> running -> failed`
- `failed -> running`（允许重跑）

## Step Ledger State (`sqlite.step_runs.status`)
- `running -> succeeded`
- `running -> failed`
- `running -> skipped`

## Poll Workflow
1. `poll_feeds_activity` 加锁（`phase2.poll_feeds`）。
2. 拉取订阅 RSS。
3. 标准化 entry（`video_uid` / `entry_hash` / `idempotency_key`）。
4. 写入 `videos` + `ingest_events`，按幂等去重创建 `jobs`。
5. 为每个新 job 启动 `ProcessJobWorkflow`。

## Process Workflow (10-Step)
1. `mark_running`
2. `fetch_metadata`
3. `download_media`
4. `collect_subtitles`
5. `collect_comments`
6. `extract_frames`
7. `llm_outline`
8. `llm_digest`
9. `write_artifacts`
10. `mark_succeeded` / `mark_failed`

## Process Mode
- `POST /api/v1/videos/process` 允许 `mode`:
  - `full`
  - `text_only`
  - `refresh_comments`
  - `refresh_llm`
- `mode` 进入 job 读模型后，`GET /api/v1/jobs/{job_id}` / `vd.jobs.get` 应原样返回。

## Job Read Model (API/MCP/Web)
`jobs.get` 的稳定字段集合：
- `step_summary`
- `steps`
- `degradations`
- `pipeline_final_status`
- `artifacts_index`
- `mode`

## Retry Strategy
- RSS 拉取：`REQUEST_RETRY_ATTEMPTS` + `REQUEST_RETRY_BACKOFF_SECONDS`。
- 子进程（`yt-dlp`/`ffmpeg`）：`PIPELINE_RETRY_ATTEMPTS` + `PIPELINE_RETRY_BACKOFF_SECONDS`。
- Temporal activities：`mark_failed` 最多 1 次，其余按 workflow 内 retry policy。

## Cache Strategy
- 业务层去重：
  - `videos(platform, video_uid)` 唯一。
  - `ingest_events(subscription_id, entry_hash)` 唯一。
  - `jobs.idempotency_key` 唯一。
- Pipeline 步骤缓存：
  - `${work_dir}/cache/{step}.json` 命中后标记 `skipped`。

## Degrade Strategy
- 下载失败：降级 `text_only`，后续仍可执行。
- 字幕缺失：写空 transcript，继续。
- 评论采集失败/未实现：空 comments，继续。
- 抽帧失败：空 frames，继续。
- LLM 不可用：回退本地规则摘要，状态可能为 `partial`。
