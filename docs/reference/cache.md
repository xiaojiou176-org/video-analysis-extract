# Cache Governance

## Cache Layers

## CI Tool Cache Governance

- Repo 内允许：`.runtime-cache/` 是唯一合法 repo-side 运行时出口，用于日志、Junit/XML、coverage、诊断 JSON、artifact staging 等一次性运行产物。
- 本地严格验收新增产物：
  - `.runtime-cache/logs/tests/api-real-smoke-local.log`
  - `.runtime-cache/reports/tests/e2e-live-smoke-result.json`
  - `.runtime-cache/run/full-stack/` 下的运行时 PID/状态文件
- Repo 内禁止：pre-commit 环境、uv/pip/npm 下载缓存、Playwright 浏览器二进制、其他可复用工具缓存，以及 `apps/web/node_modules`、`apps/web/.next`、`apps/web/.next-e2e-*` 这类直接停留在源码树中的 Web 机器态。
- Self-hosted CI 必须使用 `runner.temp` 作为工具缓存根目录，并通过统一变量收口：
  - `CI_CACHE_ROOT=${{ runner.temp }}/ci-cache`
  - `PRE_COMMIT_HOME=${{ runner.temp }}/ci-cache/pre-commit`
  - `UV_CACHE_DIR=${{ runner.temp }}/ci-cache/uv`
  - `PLAYWRIGHT_BROWSERS_PATH=${{ runner.temp }}/ci-cache/ms-playwright`
- Forbidden 路径：
  - `~/.cache/**`
  - `${{ github.workspace }}/**`
  - `.runtime-cache/**` 作为工具缓存根
  - `.cache/**`
  - `cache/**`
  - repo 内任意 Python venv / browser cache / npm 下载缓存 路径
- 所有 workflow 中的 `actions/checkout` 必须显式声明 `with.clean: true`，避免 shared self-hosted runner 复用旧工作区时把脏残留带进新 job。

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
./scripts/dev_worker.sh --command start-cleanup-workflow --run-once --older-than-hours 24
```

执行周期清理（每 6 小时）：

```bash
./scripts/dev_worker.sh --command start-cleanup-workflow --interval-hours 6 --older-than-hours 24
```

通过常驻 ops 启动脚本接入 cleanup（推荐）：

```bash
./scripts/runtime/start_ops_workflows.sh \
  --cleanup-interval-hours 6 \
  --cleanup-older-than-hours 24
```

可选缓存保留参数（CLI）：

- `--cleanup-cache-older-than-hours`：按文件年龄清理 cache。
- `--cleanup-cache-max-size-mb`：清理后按大小阈值继续淘汰最旧文件。
- `--cleanup-workspace-dir` / `--cleanup-cache-dir`：覆盖默认目录。

## Operational Notes

- pipeline 产物目录（`$PIPELINE_ARTIFACT_ROOT`）不在 cleanup 删除范围。
- 如需调整缓存保留窗口，优先修改：
  - `--cache-older-than-hours`
  - `--cache-max-size-mb`
- 修改缓存签名算法、路径或保留策略后，必须同步更新 `docs/state-machine.md`。
- 调度模式必须二选一：使用 `start_ops_workflows.sh` 常驻 workflow 时，不要再用 cron 重复触发 cleanup。

## Doc-Drift Enforcement

- 触发文件：
  - `scripts/runtime/start_ops_workflows.sh`
  - `scripts/cleanup_workspace.sh`
- 触发后必须同步更新：`docs/reference/cache.md`
- 校验脚本：`scripts/governance/ci_or_local_gate_doc_drift.sh`

## Delivery Retry Claim 窗口说明（2026-03）

通知重试链路新增了“超时 queued 回收”能力后，领取条件已收紧，避免误回收非重试中的记录：

- 仅回收满足以下条件的 queued 记录：
  - `next_retry_at <= NOW()`
  - `updated_at` 超过 `claim_timeout`
  - `attempt_count > 0`

设计意图：

- 保留“领取后异常退出”的恢复能力，避免永久卡在 queued。
- 降低长耗时发送任务被过早回收导致重复执行的概率。

补充：

- 该机制属于“重试状态恢复”，不改变本页已有 cache 路径/保留策略。

## Full-stack / Smoke 运行时缓存边界（2026-03）

- `scripts/ci/smoke_full_stack.sh` 与 `scripts/ci/e2e_live_smoke.sh` 产生的 `.runtime-cache/*` 文件属于一次性诊断产物，不应被当作长期缓存命中来源。
- `scripts/ci/api_real_smoke_local.sh` 创建的隔离 smoke 数据库会在退出时删除；它依赖 `.runtime-cache/run/api-real-smoke-local-state.sqlite3` 作为临时状态文件，不进入长期保留策略。
- Web 依赖工作区与 `.next*` 临时产物统一进入 `.runtime-cache/temp/web-runtime/`，由 `scripts/ci/prepare_web_runtime.sh` 重建与清场。
- smoke / e2e / live-smoke / pr-llm-real-smoke 的输出现在按测试语义分舱：
  - 日志：`.runtime-cache/logs/tests/`
  - JUnit/diagnostics：`.runtime-cache/reports/tests/`
  - 浏览器证据：`.runtime-cache/evidence/tests/`
- 终局治理分舱固定为：`.runtime-cache/run/`、`.runtime-cache/logs/`、`.runtime-cache/reports/`、`.runtime-cache/evidence/`、`.runtime-cache/temp/`。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->
