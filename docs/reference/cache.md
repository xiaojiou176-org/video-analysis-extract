# Cache Governance

## Cache Layers

### 1) 业务幂等去重（PostgreSQL）
- `videos(platform, video_uid)` 唯一
- `ingest_events(subscription_id, entry_hash)` 唯一
- `jobs.idempotency_key` 唯一

用途：避免重复入库与重复创建 job。

### 2) 步骤缓存（Worker Workspace）
- 路径根：`$PIPELINE_WORKSPACE_DIR/<job_id>/cache/`
- 每个步骤按 `step + version + signature` 生成缓存 key。
- 命中缓存时，step 状态会标记为 `skipped`，原因可能为：
  - `cache_hit`
  - `legacy_cache_hit`
  - `checkpoint_recovered`
  - `mode_matrix_skip`

实现位置：`apps/worker/worker/pipeline/step_executor.py`（由 runner/orchestrator 调用）。

### 2.1) 缓存自愈（Cache Self-Healing）

- 自愈触发：`resume_hint=true` 且 workspace 缓存未命中时，会尝试从 SQLite `step_runs` 的历史成功记录恢复同 `cache_key` 结果。
- 自愈来源标记：
  - `cache_meta.source=cache_hit|legacy_cache_hit`：命中当前/旧版缓存文件。
  - `cache_meta.source=checkpoint`：命中 SQLite checkpoint 恢复。
  - `reason=checkpoint_recovered`：本次 step 以恢复方式 `skipped`。
- 失败兜底：缓存文件损坏/不可解析会自动忽略并回落到正常执行路径，不会直接中断 pipeline。

### 3) 运行账本（SQLite）
- `step_runs.cache_key` 记录步骤缓存键
- `checkpoints` 记录 job 恢复位点

用途：恢复重跑与审计追踪。

## API / MCP 观测字段

`GET /api/v1/jobs/{job_id}` 与 `vd.jobs.get` 可直接观测：
- `steps[].cache_key`
- `steps[].result.cache_meta`（含 `source/cache_key/signature/version`）
- `steps[].result.retry_meta`（含 `strategy/resume_hint/attempts/retries_used`）
- `degradations[].cache_meta`
- `degradations[].reason`（可见 `cache_hit`、`legacy_cache_hit`、`checkpoint_recovered`、`mode_matrix_skip`）

## Gemini Context Cache 自愈

`llm_outline` / `llm_digest` 的 text 模式会优先使用 Gemini context cache；遇到缓存异常会执行自愈：
- 识别缓存错误（`cache/not found/404/failed_precondition/...`）
- 删除本地缓存名映射并尝试重建 cache
- 重建失败时自动回退到非缓存文本请求

可观测字段（位于 `steps[].result.llm_meta`）：
- `cache_hit`
- `cache_recreate`
- `cache_bypass_reason`

## Cleanup Strategy

`CleanupWorkspaceWorkflow` 会清理两类内容：
- workspace 下过期的媒体文件（`downloads/`、`frames/`）
- 指定 cache 目录中的过期或超额文件

默认 cache 目录：`<PIPELINE_WORKSPACE_DIR>/../cache`。

执行一次清理：
```bash
WORKER_COMMAND=start-cleanup-workflow ./scripts/dev_worker.sh --run-once --older-than-hours 24
```

执行周期清理（每 6 小时）：
```bash
WORKER_COMMAND=start-cleanup-workflow ./scripts/dev_worker.sh --interval-hours 6 --older-than-hours 24
```

通过常驻 ops 启动脚本接入 cleanup（推荐）：
```bash
OPS_CLEANUP_INTERVAL_HOURS=6 \
OPS_CLEANUP_OLDER_THAN_HOURS=24 \
./scripts/start_ops_workflows.sh
```

可选缓存保留参数：
- `OPS_CLEANUP_CACHE_OLDER_THAN_HOURS`：按文件年龄清理 cache。
- `OPS_CLEANUP_CACHE_MAX_SIZE_MB`：清理后按大小阈值继续淘汰最旧文件。
- `OPS_CLEANUP_WORKSPACE_DIR` / `OPS_CLEANUP_CACHE_DIR`：覆盖默认目录。

## Operational Notes
- pipeline 产物目录（`$PIPELINE_ARTIFACT_ROOT`）不在 cleanup 删除范围。
- 如需调整缓存保留窗口，优先修改：
  - `--cache-older-than-hours`
  - `--cache-max-size-mb`
- 修改缓存签名算法、路径或保留策略后，必须同步更新 `docs/state-machine.md`。
- 调度模式必须二选一：使用 `start_ops_workflows.sh` 常驻 workflow 时，不要再用 cron 重复触发 cleanup。
