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

实现位置：`apps/worker/worker/pipeline/runner.py`。

### 3) 运行账本（SQLite）
- `step_runs.cache_key` 记录步骤缓存键
- `checkpoints` 记录 job 恢复位点

用途：恢复重跑与审计追踪。

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

## Operational Notes
- pipeline 产物目录（`$PIPELINE_ARTIFACT_ROOT`）不在 cleanup 删除范围。
- 如需调整缓存保留窗口，优先修改：
  - `--cache-older-than-hours`
  - `--cache-max-size-mb`
- 修改缓存签名算法、路径或保留策略后，必须同步更新 `docs/state-machine.md`。
