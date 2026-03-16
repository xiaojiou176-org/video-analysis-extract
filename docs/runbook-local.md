# Local Runbook (Container-First, Phase3)

本文是本仓库本地运行的权威步骤文档。标准镜像路径是 CI 等价验收真相源，宿主机路径仅作为故障应急。

边界提醒：

- public/source-first onboarding 先看 `README.md` 与 `docs/start-here.md`
- 本文更偏 operator runbook 与本地排障，不应直接当成公共入门页
- repo-side / external 双层完成模型见 `docs/reference/done-model.md`

## 标准环境约束（AI/自动化必须）

- AI 执行 lint/test/live smoke 必须在标准环境完成：`.devcontainer/devcontainer.json`。
- 基础设施编排真相源固定为：`infra/compose/core-services.compose.yml`（核心服务镜像已收口为 digest-pinned service images，并优先接受 strict contract 导出的 `STRICT_CI_SERVICE_IMAGE_*` 值）与 `infra/compose/miniflux-nextflux.compose.yml`。
- 严格 CI 标准镜像真相源固定为：`infra/config/strict_ci_contract.json`。`./bin/run-in-standard-env` 现在要求 contract 中的标准镜像必须是 digest-pinned，且拉取失败时直接报错，不再回退到旧本地镜像。
- self-hosted runner 基线真相源固定为：`infra/config/self_hosted_runner_baseline.json`。`_preflight-fast-steps.yml` 与 `runner-health.yml` 都通过 `scripts/governance/check_runner_baseline.py` 验证 runner 前提，缺失工具直接失败，不再在 workflow 中临时安装。
- 若不使用 DevContainer，必须提供等价隔离环境（依赖版本、工具链、Compose 服务拓扑一致），否则验证结果不具备门禁效力。

进入标准环境：

```bash
devcontainer up --workspace-folder .
```

补充说明：

- 宿主 Docker daemon 必须可用；`strict_ci_entry.sh`、`run_in_standard_env.sh` 与 DevContainer 都共享这一前提。
- 当前关键 correctness jobs 已统一按标准镜像口径对齐，包括 `preflight-heavy`、`db-migration-smoke`、`dependency-vuln-scan`、`web-e2e-perceived`、`backend-lint` hosted/fallback、`frontend-lint` hosted/fallback。
- DevContainer 工作目录已固定为 `/workspace`，并复用 strict contract 的 `UV_CACHE_DIR` / `PLAYWRIGHT_BROWSERS_PATH` 等标准缓存路径约定。
- Web runtime workspace 固定收口到 `.runtime-cache/tmp/web-runtime/workspace/apps/web`；`apps/web/node_modules` 与 `apps/web/.next*` 不再视为仓库内合法长期机器态。
- `.devcontainer/post-create.sh` 现在会直接校验 strict contract 的 Chromium 是否可启动；若浏览器缺失，标准环境初始化会直接失败，而不是继续用 best-effort 安装掩盖漂移。

<!-- docs:generated governance-snapshot start -->
## Generated Governance Snapshot

- 运行说明文档只解释执行与排障语义；高漂移 CI/runner/release 清单见 `docs/generated/*.md`。
- runner baseline 参考页：`docs/generated/runner-baseline.md`。
- CI 主链与 aggregate gate 清单：`docs/generated/ci-topology.md`。
- release evidence 结构与 canonical 规则：`docs/generated/release-evidence.md`。
- external lane current snapshot：`docs/generated/external-lane-snapshot.md`。
- repo-side / external 双层完成模型：`docs/reference/done-model.md`。
<!-- docs:generated governance-snapshot end -->

## 环境分层与优先级（Core/Profile Overlay）

- Core baseline：`.env`（API/Worker/MCP/Web 默认运行配置）
- Profile overlay：
  - 通过 `--profile local|gce` 选择脚本运行画像
  - `env/profiles/reader.env`（reader profile 模板）
- Secret injection policy：密钥仅允许来自 `.env` 或进程环境；禁止依赖 shell 登录配置。

变量优先级（收口后口径）：

1. 路由真相源（`API_PORT`/`WEB_PORT`）：`CLI > .runtime-cache/run/full-stack/resolved.env > .env > 默认值`
2. 派生地址（`VD_API_BASE_URL`/`NEXT_PUBLIC_API_BASE_URL`）：默认由路由真相源派生，若显式传 `--api-base-url` 等 CLI 参数则以 CLI 为准。
3. 密钥类键：当前进程显式注入优先，再回退到 `.env`。
4. reader overlay：仅补齐缺失 `MINIFLUX_*`/`NEXTFLUX_*`，不覆盖当前进程已有值。

Reader overlay 规则：

- reader env 不会全局生效，仅在 reader 栈命令路径生效（`deploy_reader_stack.sh`、reader 检查/同步链路）。
- 启用 reader 栈时，建议显式指定 `--env-file env/profiles/reader.env`。
- reader overlay 只补齐缺失的 `MINIFLUX_*` / `NEXTFLUX_*` 变量；当前 shell 中显式导出的 reader 凭证优先级更高，不会被模板值覆盖。

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
UV_PROJECT_ENVIRONMENT="$PWD/.runtime-cache/tmp/uv-project-env" uv sync --frozen --extra dev --extra e2e
./bin/prepare-web-runtime
```

说明：`./bin/prepare-web-runtime` 只是稳定入口层，真正执行的是 `scripts/ci/prepare_web_runtime.sh`。这个 helper 必须保持可执行位；如果 wrapper 报 `Permission denied`，那是入口契约损坏，不是 Web runtime 内容本身坏掉。

- `build-ci-standard-image.yml` 现在会先显式准备 Docker Buildx，再调用 `scripts/ci/build_standard_image.sh` 做多架构标准镜像构建；如果镜像工作流仍在构建入口阶段立刻失败，先检查 runner 的 buildx 准备步骤是否成功，而不是先怀疑 GHCR 权限。
- 标准镜像构建链依赖 `.devcontainer/Dockerfile`；当前约定会对 NodeSource signing key 做显式重试，并先写入临时 key 文件再 `gpg --dearmor`，这样 ARM64/QEMU buildx 路径遇到短暂 HTTP/2 抖动时，不会把空响应直接当成有效 key。
- self-hosted runner 在进入 `build-ci-standard-image.yml` 之前，会用 `scripts/governance/runner_workspace_maintenance.sh` 统一清理 `.runtime-cache`、`mutants/` 和 `/tmp/video-digestor-*` 下的目录/单文件 stale residue；如果 workflow 再次在 runner hygiene 阶段失败，先看是否出现新的不可写残留，而不是先怀疑 GHCR 权限。

### 1.1) 初始化 Git 质量门禁（建议首次 clone 后执行）

```bash
./bin/install-git-hooks
```

可选：安装 pre-commit framework hooks（会写入当前 `core.hooksPath`）：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

协同关系（当前实现）：

- `.githooks/*` 是默认强制入口，负责调用 `quality_gate` 与 `commitlint`。
- `.pre-commit-config.yaml` 是可复用检查清单，主要用于手动执行全量检查与依赖版本保养。
- 因此本仓库口径是：`.githooks` 负责“提交/推送阻断”，`pre-commit` 负责“批量清洗与工具链维护”。

质量门禁提速口径（2026-02）：

- `quality_gate.sh` 支持 `--changed-backend|web|deps|migrations` 与 `--ci-dedupe`。
- pre-commit 的 `auto` 使用 staged diff；pre-push 的 `auto` 优先使用 upstream merge-base diff，失败回退 `HEAD~1..HEAD`，无法可靠识别时保守回退为全量检查。
- 本地 pre-push 默认使用变更感知门禁：后端变更命中时强制 mutation，并默认执行 `api_real_smoke_local.sh`（真实 Postgres + Temporal + worker）；无后端变更时跳过 mutation 与 real smoke 以避免无效本地消耗。
- 在 CI 的 dedupe 模式中，`quality-gate-pre-push` 作为远端最重门禁执行（显式 `--skip-mutation 1`）；mutation 由独立 `mutation-testing` job 执行，lint/unit/coverage 由独立 CI job 并行交叉验证。
- 本地 `strict-full-run=1` 会强制关闭 `ci-dedupe` 并禁用 `skip-mutation`，同时执行 repo-wide `>=95%` 覆盖率与 mutation `score>=0.64 / effective_ratio>=0.27 / no_tests_ratio<=0.72` 的完整全量门禁。
- 本地 pre-push 会额外执行 `api cors preflight smoke (OPTIONS DELETE)` 与 `contract diff local gate (base vs head)`，用于在推送前发现跨端 CORS 与接口契约回归。
- 成本治理约束：重跑远程 CI 前，必须先本地通过 pre-push；若远程失败，先本地复现修复再重跑，禁止连续重跑碰运气。
- PR 信任边界约束：self-hosted CI 只接受 **trusted internal PR**。若 PR 来自 fork / 非同仓分支，主链应在 trusted boundary gate 直接终止，而不是继续占用 privileged runner。

Big Bang 全量清洗（可选）：

```bash
pre-commit run --all-files
```

detect-secrets baseline（可选补充；默认强制 secrets 门禁仍是 gitleaks）：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

月度保养（建议）：

```bash
pre-commit autoupdate
pre-commit run --all-files
```

### 2) 启动基础服务（Host Fallback，仅故障应急）

```bash
brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3) 初始化环境变量（统一流程）

```bash
cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
set -a; source .env; set +a
```

说明：

- `./bin/dev-api`、`./bin/dev-worker`、`./bin/dev-mcp`、`./bin/run-daily-digest`、`./bin/run-failure-alerts` 均会优先自动加载 `.env`。
- 标准初始化路径是 `.env.example -> .env`；`./bin/init-env-example` 仅用于按需生成辅助模板。
- 环境契约真相源：`ENVIRONMENT.md` + `infra/config/env.contract.json`。

### 4) 初始化数据库（统一迁移命令）

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

说明：`20260222_000010_phase4_status_contract.sql` 在加新约束前会先归一化历史脏状态（含旧 `partial` 语义），用于避免历史库迁移失败。

### 5) 启动应用进程

分别在 3 个终端运行：

```bash
./bin/dev-api
./bin/dev-worker
./bin/dev-mcp
```

补充说明：

- `./bin/dev-api` 会委托内部启动脚本在检测到 `uv` 时使用 `uv run python -m uvicorn ...`；这是为了避免 self-hosted runner 或最小化环境中缺少 `uvicorn` console entry 时 API 无法拉起。

### 6) 最小验收

```bash
curl -sS http://127.0.0.1:9000/healthz
curl -sS -X POST http://127.0.0.1:9000/api/v1/ingest/poll \
  -H 'Content-Type: application/json' \
  -d '{"max_new_videos": 20}'
```

可选：查询 job 详情（稳定字段）

```bash
curl -sS http://127.0.0.1:9000/api/v1/jobs/<job_id>
```

## 可选操作

### 发布前证据与回滚清单

```bash
python3 scripts/release/generate_release_prechecks.py
python3 scripts/release/build_readiness_report.py \
  --kpi-json .runtime-cache/reports/release-readiness/ci-kpi-summary.json \
  --check-json .runtime-cache/reports/release-readiness/prechecks.json

scripts/release/capture_release_manifest.sh <release-tag>

python3 scripts/release/verify_db_rollback_readiness.py \
  --release-tag <release-tag> \
  --output artifacts/releases/<release-tag>/rollback/db-rollback-readiness.json
```

说明：该门禁会同时检查 `missing_policy`、`blocked_without_down` 与 `invalid_down_sql`，任一大于 0 都会阻断发版。

### 手动触发日报与失败告警

```bash
./bin/run-daily-digest
./bin/run-failure-alerts
```

常用覆盖参数：

```bash
./bin/run-daily-digest --date 2026-02-21 --to-email 'you@example.com'
./bin/run-failure-alerts --lookback-hours 6 --limit 10 --to-email 'you@example.com'
```

### 清理 workflow（媒体与缓存）

```bash
./bin/dev-worker --command start-cleanup-workflow --run-once --older-than-hours 24
```

缓存策略细节见 `docs/reference/cache.md`。

### 调度（cron）

注意：`cron` 与下方“实时稳定推送（常驻 workflow）”必须二选一，避免重复触发同类任务。

```cron
0 9 * * * /bin/bash -lc 'cd "<repo-path>" && ./bin/run-daily-digest >> ./.runtime-cache/logs/app/daily_digest.log 2>&1'
*/30 * * * * /bin/bash -lc 'cd "<repo-path>" && ./bin/run-failure-alerts >> ./.runtime-cache/logs/app/failure_alerts.log 2>&1'
```

### 实时稳定推送（生产建议）

仓库内置了 `./bin/start-ops-workflows`，用于一次性启动/确保以下长期运行 workflow：

- `daily_digest`（日报）
- `notification_retry`（失败投递重试）
- `provider_canary`（上游可用性探针）
- `cleanup_workspace`（媒体与缓存清理）

该脚本复用现有 worker CLI（`start-daily-workflow` / `start-notification-retry-workflow` / `start-provider-canary-workflow` / `start-cleanup-workflow`），默认适配本地非 Docker 运行。

1. 基础用法

```bash
./bin/start-ops-workflows
```

2. 推荐参数（生产）

```bash
mkdir -p .runtime-cache/logs/app .runtime-cache/logs/governance
./bin/start-ops-workflows \
  --daily-local-hour 9 \
  --daily-timezone Asia/Shanghai \
  --notification-interval-minutes 5 \
  --notification-retry-batch-limit 100 \
  --canary-interval-hours 1 \
  --canary-timeout-seconds 8 \
  --cleanup-interval-hours 6 \
  --cleanup-older-than-hours 24 \
  --daily-workflow-id daily-digest-workflow \
  --notification-workflow-id notification-retry-workflow \
  --canary-workflow-id provider-canary-workflow \
  --cleanup-workflow-id cleanup-workspace-workflow \
  --show-hints >> ./.runtime-cache/logs/governance/workflows.log 2>&1
```

3. 常用 CLI 参数

- `--daily-workflow-id` / `--notification-workflow-id` / `--canary-workflow-id` / `--cleanup-workflow-id`：固定 workflow id，用于“已运行则不重复启动”。
- `--daily-run-once` / `--notification-run-once` / `--canary-run-once` / `--cleanup-run-once`：改为单次执行（排障时使用，生产常驻建议默认关闭）。
- `--daily-local-hour` / `--daily-timezone`：日报调度时间配置。
- `--notification-interval-minutes` / `--notification-retry-batch-limit`：失败投递重试节流配置。
- `--canary-interval-hours` / `--canary-timeout-seconds`：provider 可用性探针频率与超时。
- `--cleanup-interval-hours` / `--cleanup-older-than-hours`：清理调度与保留窗口。
- `--cleanup-cache-older-than-hours` / `--cleanup-cache-max-size-mb`：可选 cache 细粒度保留。
- `--cleanup-workspace-dir` / `--cleanup-cache-dir`：可选目录覆盖。安全限制：repo 内只允许落在 `${REPO_ROOT}/.runtime-cache`；repo 外 operator 路径只允许 `/tmp/video-digestor*`、`/tmp/video-analysis*` 前缀下，超出白名单会直接失败。
- `--daily-timezone-offset-minutes`：可选，显式 UTC 偏移分钟。
- `--show-hints` / `--no-show-hints`：开关脚本启动摘要日志（默认显示）。
- `--dry-run`：只打印命令不执行（等价 `./bin/start-ops-workflows --dry-run`）。

5. 调度互斥策略（必须执行）

- 方案 A：使用 cron（`run_daily_digest.sh` / `run_failure_alerts.sh`），则不要启动对应常驻 workflow。
- 方案 B：使用 `start_ops_workflows.sh` 常驻模式（推荐），则停用上述 cron 条目。
- cleanup 建议统一走常驻 workflow，不建议额外 cron 重复触发 `start-cleanup-workflow`。

4. 脚本可用性快速验证

```bash
bash -n scripts/runtime/start_ops_workflows.sh
./bin/start-ops-workflows --help
./bin/start-ops-workflows --dry-run
```

5. 告警与重试调优建议（基于现有能力）

- 投递重试策略已内置指数退避：`2/5/15/30/60` 分钟，最多 `5` 次；`auth/config_error` 不会继续重试。
- 建议将 `--notification-interval-minutes` 设为 `3-10` 分钟；高流量场景可配合 `--notification-retry-batch-limit 100-300`，避免 backlog 累积。
- `provider_canary` 每轮会写入 `provider_health_checks`（`rsshub/youtube_data_api/gemini/resend`），建议外部监控以最近 5-10 分钟窗口统计 `status=fail` 或连续 `warn` 触发告警。
- 失败投递会记录在 `notification_deliveries`（含 `attempt_count`、`next_retry_at`、`last_error_kind`），建议对 `status='failed' AND next_retry_at IS NULL` 的记录设置人工告警（通常表示已达上限或配置错误）。

## 一键脚本（Clone 后 80%+ 快速可用）

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
```

脚本说明：

- `./bin/bootstrap-full-stack`：依赖安装、环境校验、数据库迁移、可选 reader stack。
- `./bin/bootstrap-full-stack` 除首次 `.env` 不存在时复制模板外，不再持久化改写 `.env`；端口冲突和运行时路由决策会写入 `.runtime-cache/run/full-stack/resolved.env`，仅对当前运行生效。
- `./bin/full-stack`：统一起停 API/Worker/Web；`up` 会等待 API health(`GET /healthz`) 与 Web 端口就绪，失败时输出关键服务日志片段。
- `./bin/dev-mcp`：交互式 stdio MCP 入口，不由 `./bin/full-stack` 作为后台守护进程管理。
- `./bin/full-stack` 启动 Web 时会显式注入 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${API_PORT}`，避免开发日志继续回落到 `127.0.0.1:9000`。
- 本地路由真相源是 `API_PORT/WEB_PORT`；`VD_API_BASE_URL` 与 `NEXT_PUBLIC_API_BASE_URL` 为派生地址。
- `./bin/full-stack` 的启动顺序是“API health -> Web -> Worker”；Worker 启动前会先做 stronger Temporal readiness：先校验 worker 必需环境，再对 `TEMPORAL_TARGET_HOST`（默认 `localhost:7233`）做 `host:port` 解析与 TCP 探测；不可达时直接以 `stage=worker_preflight_temporal` / `conclusion=temporal_not_ready` fail-fast，不会先把 API/Web 拉起来。
- `./bin/smoke-full-stack`：执行端到端 smoke（含 feed/web 检查，可选 reader 检查）。
- `./bin/smoke-full-stack` 不是 `api-real-smoke` 替代；后端真实 Postgres integration smoke 需单独执行 `./bin/api-real-smoke-local`。
- `./bin/api-real-smoke-local` 默认监听 `127.0.0.1:18080`；若该默认端口被其他本地服务占用且未显式传 `--api-port`，脚本会自动选择下一个空闲端口。
- `./bin/api-real-smoke-local` 会在 cleanup workflow closure probe 前临时启动 worker；脚本退出时会一并清理 API/worker 与隔离数据库。
- `./bin/api-real-smoke-local` 现在会先检测本机 IPv4 loopback 是否健康；如果一开始就报 `failure_kind=host_loopback_ipv4_exhausted`，优先处理主机环境（减少本地 MCP/Codex bridge 长连接、换更干净 runner），而不是继续追 API/Temporal 业务日志。
- 运行时排障优先顺序：先看 `.runtime-cache/run/full-stack/resolved.env` 与 `.runtime-cache/logs/components/full-stack/*.log`，再看 `.runtime-cache/logs/tests/api-real-smoke-local.log`，最后才下钻到 API/worker 业务栈日志。
- `pr-llm-real-smoke` / `live-smoke` / `web-e2e` 证据统一收口到：
  - `.runtime-cache/logs/tests/`
  - `.runtime-cache/reports/tests/`
  - `.runtime-cache/evidence/tests/`
- compose 固定默认（不再通过 env 覆盖）：core Postgres `DB/User`、Redis 端口、Temporal 端口；Miniflux `DB/User/DB_NAME` 与 Miniflux 端口。

`full_stack.sh` 运行约束（稳定性修复）：

- `up` 后台拉起 API 时会调用 `./bin/dev-api --no-reload`，避免 `uvicorn --reload` 父子进程漂移导致 `status`/`down` 误判。
- `status` 会在 PID 元数据失真时按进程特征探测并自愈 PID 文件。

Live smoke 执行约束（2026-02 更新）：

- 环境变量加载顺序：优先仓库 `.env`，缺失项仅使用当前 shell 环境变量。
- reader 检查/同步链路会额外读取 `env/profiles/reader.env` 补齐缺失 reader 变量，但会保留当前 shell 已显式注入的 reader 凭证优先级。
- `YOUTUBE_API_KEY` 失效自修复：按 `.env` → 当前 shell 环境变量顺序尝试可用 key；命中后自动回写 `.env`（日志仅输出脱敏片段，不输出完整 key）。
- 若上述来源全部无效：live smoke 会明确失败并提示“需要用户提供有效key”。
- 外部真实交互：`e2e_live_smoke.sh` 会先执行真实外部 API 探测，再执行真实浏览器外站探测（`external_playwright_smoke.sh`）。
- 重试上限：live 脚本网络重试最多 2 次（含首轮）。
- 诊断输出：失败时会写入结构化 JSON，并区分 `code_logic_error` 与 `network_or_environment_timeout`。
- 执行顺序：`short tests first`（health/feed/web/external probe）→ `long tests`（全链路视频处理与同步）→ `teardown`（仅安全清理临时产物）。
- 写操作策略：live 写入仅用于可重复 smoke 验证；诊断 JSON 必须落地 `write_operations[].idempotency_key`、`write_operations[].cleanup_action`、`teardown.steps[]`。

当前默认：

- `bootstrap_full_stack.sh` 默认启用 core services 与 reader stack。
- `smoke_full_stack.sh` 默认执行 reader checks，并会执行 `bin/run-ai-feed-sync` 验证 AI 文本回写 Miniflux。
- `smoke_full_stack.sh` 默认就是 fail-fast；reader/core 服务异常会直接停止，不再保留 offline fallback marker 与降级跳过 reader checks 的路径。

## 本地验收口径分层（sqlite vs 真实 Postgres）

- 默认快速回归：`sqlite+pysqlite:///:memory:`，用于全仓快速测试与日常 pre-push。
- 真实后端集成验收：`postgresql+psycopg://...` + `API_INTEGRATION_SMOKE_STRICT=1`，用于对齐 CI `api-real-smoke`。

推荐命令：

```bash
./bin/quality-gate --mode pre-push --profile ci --profile live-smoke --ci-dedupe 0
./bin/api-real-smoke-local
./bin/quality-gate --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

标准严格验收命令（固定顺序）：

```bash
./bin/full-stack up
./bin/api-real-smoke-local
./bin/smoke-full-stack
./bin/quality-gate --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

如果 `api_real_smoke_local.sh` 在最开始就失败并输出 `host_loopback_ipv4_exhausted`：

```bash
# 先确认是不是当前主机的 127.0.0.1 环境本身不健康
python3 - <<'PY'
import socket
s = socket.socket()
try:
    s.settimeout(2)
    s.connect(("127.0.0.1", 80))
    print("loopback-ok")
except Exception as exc:
    print(f"loopback-failed: {exc}")
finally:
    s.close()
PY
```

出现 `Errno 49` 时，优先减少本机高连接占用进程（尤其是大量 MCP/Codex bridge），再重跑真实 smoke。

## 常见故障

- `API health check failed`：确认 `./bin/dev-api` 已运行，且 `VD_API_BASE_URL` 可访问。
- `RESEND_API_KEY is not configured` / `RESEND_FROM_EMAIL is not configured`：`NOTIFICATION_ENABLED=true` 时需补齐 `.env`（或在当前 shell 中显式导出）。
- 404 报表路由：`run_daily_digest.sh` / `run_failure_alerts.sh` 会按脚本内 fallback 流程回退发送。

## LLM 能力入口（Gemini-only）

- Provider 固定：Gemini（`llm_outline`/`llm_digest`）。
- Thinking：`GEMINI_THINKING_LEVEL` + `overrides.llm.thinking_level`。
- Structured Output：固定 JSON + schema 校验。
- Function Calling：outline/digest 开启，翻译回退关闭。
- Context Cache：`GEMINI_CONTEXT_CACHE_ENABLED`、`GEMINI_CONTEXT_CACHE_TTL_SECONDS`、`GEMINI_CONTEXT_CACHE_MIN_CHARS`。
- Media Resolution：`PIPELINE_LLM_INPUT_MODE`、`PIPELINE_MAX_FRAMES`、`overrides.frames.max_frames`、`llm_media_input`。
- Embedding / Retrieval：`GEMINI_EMBEDDING_MODEL`；检索入口为 `jobs.artifacts_index`。

## Computer Use（函数调用）与安全闸

- 使用入口：`POST /api/v1/videos/process` 的 `overrides.llm*`。
- 安全闸（当前实现）：
  - 仅白名单工具：`select_supporting_frames`、`build_evidence_citations`。
  - 非白名单会记录为 `blocked`，不会执行任意工具。
  - 调用回合上限：`max_function_call_rounds`（默认 `2`）。
  - `computer_use` 开关可配置；当 `enable_computer_use=true` 且未显式提供 handler 时，worker 会默认注入 `build_default_computer_use_handler`。
  - `computer_use_require_confirmation` 默认 `true`，未确认会返回 `computer_use_confirmation_required`。
  - 翻译回退阶段固定关闭 function calling。

示例（限制回合并开启 thought 输出）：

```bash
curl -sS -X POST http://127.0.0.1:9000/api/v1/videos/process \
  -H 'Content-Type: application/json' \
  -d '{
    "video": {"platform": "youtube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    "mode": "refresh_llm",
    "overrides": {
      "llm": {
        "max_function_call_rounds": 1,
        "include_thoughts": true,
        "enable_computer_use": true
      }
    }
  }'
```

## Thought Metadata / Signatures 可见性

- API：`GET /api/v1/jobs/<job_id>` 的 `steps[].result.llm_meta.thinking` 可见 `thought_signatures` / `thought_signature_digest` / `usage`。
- MCP：`vd.jobs.get` 保留相同结构。
- `steps[].thought_metadata` 为归一化提取字段（含 `llm_meta.thinking`），未命中时返回空结构（非 `null`）。

## 文档联动规则

以下改动必须同步本文件：

- 新增迁移文件（`infra/migrations/*.sql`）
- 环境变量契约调整
- 启动脚本参数或默认值调整

## GCE Instance Scope 最小权限（2026-03）

`./bin/recreate-gce-instance` 已切换为“默认最小权限 scopes”，不再默认 `cloud-platform` 全权限。

- 默认 scopes：
  - `https://www.googleapis.com/auth/devstorage.read_only`
  - `https://www.googleapis.com/auth/logging.write`
  - `https://www.googleapis.com/auth/monitoring.write`
  - `https://www.googleapis.com/auth/service.management.readonly`
  - `https://www.googleapis.com/auth/servicecontrol`
  - `https://www.googleapis.com/auth/trace.append`
- 如需显式启用全权限模式，传入：
  - `--scopes "https://www.googleapis.com/auth/cloud-platform"`
- 该参数仅用于“已知必须全权限”的运维场景，默认不建议使用。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->


<!-- doc-sync: mcp/web contract and schema alignment (2026-03-03) -->


<!-- doc-sync: mcp api-client redaction fixture adjustment (2026-03-03) -->


<!-- doc-sync: integration smoke uses xfail instead of skip when env unmet (2026-03-03) -->


<!-- doc-sync: ci failure fixes (integration smoke auth + ci_autofix timezone compatibility) (2026-03-03) -->
