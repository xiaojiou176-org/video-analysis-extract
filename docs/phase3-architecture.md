# Phase3 Architecture

## Scope
- RSSHub 订阅拉取与去重入库。
- Temporal 编排 Poll + Process 两层 workflow。
- Worker 端 9-step pipeline（metadata/下载/字幕/评论/抽帧/LLM/embedding/产物写入）。
- MCP 薄封装暴露订阅、拉取、处理、产物读取。

## Components
- `apps/api`: FastAPI 控制面（`/api/v1/*`）。
- `apps/worker`: Temporal worker + pipeline executor。
- `apps/mcp`: FastMCP（转发 API）。
- PostgreSQL：业务真相（subscriptions/videos/ingest_events/jobs）。
- SQLite：运行账本（step_runs/locks/checkpoints）。

## Data Flow
1. `POST /api/v1/ingest/poll` 启动 `PollFeedsWorkflow`。
2. `poll_feeds_activity` 生成新 job（幂等键去重）。
3. 每个新 job 触发 `ProcessJobWorkflow(job_id)`。
4. `run_pipeline_activity` 执行 9-step，并将产物写到：
   - `${PIPELINE_ARTIFACT_ROOT}/{platform}/{video_uid}/{job_id}/`
5. `mark_succeeded_activity` 把 `artifact_digest_md` 和 `artifact_root` 落库到 `jobs`。
6. `GET /api/v1/artifacts/markdown` 根据 `job_id` 或 `video_url` 读取 digest。

## Job Contract Synchronization
- API `GET /api/v1/jobs/{job_id}`、MCP `vd.jobs.get`、Web `Job` 类型共享同一组字段：
  - `step_summary`
  - `steps`
  - `degradations`
  - `pipeline_final_status`
  - `llm_required`
  - `llm_gate_passed`
  - `hard_fail_reason`
  - `artifacts_index`
  - `mode`
- `mode` 来源于 `POST /api/v1/videos/process` 的入参，要求在读取链路中保持透传。

## Failure Model
- 可降级步骤失败不会直接终止 workflow，最终会标记 `pipeline_final_status=degraded`。
- 只有关键路径失败（无法写产物等）才标记 `failed`。
- `mark_failed_activity` 统一收口错误写库，保证状态可追踪。

## Non-Docker Runtime
- 本地直接运行（brew + python venv/uv）。
- 不依赖容器路径，文件引用均为绝对路径。

## MCP Mapping
- `vd.subscriptions.manage(action=list|upsert|remove)` -> `/api/v1/subscriptions*`
- `vd.ingest.poll` -> `/api/v1/ingest/poll`
- `vd.jobs.get` -> `/api/v1/jobs/{job_id}`
- `vd.videos.list` -> `/api/v1/videos`
- `vd.videos.process` -> `/api/v1/videos/process`
- `vd.artifacts.get(kind=markdown|asset)` -> `/api/v1/artifacts/markdown|/api/v1/artifacts/assets`
- `vd.health.get(scope=system|providers|all)` -> `/healthz|/api/v1/health/providers`
- `vd.workflows.run` -> `/api/v1/workflows/run`
- `vd.retrieval.search` -> `/api/v1/retrieval/search`
- `vd.computer_use.run` -> `/api/v1/computer-use/run`
- `vd.notifications.manage(action=...)` -> `/api/v1/notifications/*|/api/v1/reports/daily/send`
- `vd.ui_audit.run|vd.ui_audit.read(action=...)` -> `/api/v1/ui-audit/*`

`vd.jobs.get` 规范化输出必须保留 `steps/degradations/pipeline_final_status/llm_required/llm_gate_passed/hard_fail_reason/artifacts_index/mode`，不能裁剪为仅 `step_summary`。
