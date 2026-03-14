# Testing Guide (Wave4)

## Scope

本次 Wave4 增加了以下测试骨架：

- `apps/worker/tests`
- `apps/api/tests`
- `apps/mcp/tests`
- `apps/web/tests/e2e`

所有新增测试都包含至少一个真实行为断言（字段或状态码），不使用安慰剂断言。
测试分层口径：API tests 主责路由字段契约，Web E2E 主责关键用户旅程与端到端成功信号，MCP tests 主责工具动作路由与标准化语义（避免逐字段重复 API 契约）。

## 环境分层与密钥注入口径

- 测试配置采用 `core + profile overlay`：
  - core：`.env`
  - overlay：`env/profiles/reader.env`（reader profile 模板，仅 reader 相关 smoke）
  - 严格验收：统一通过 `scripts/strict_ci_entry.sh` 进入仓库标准镜像，不再把宿主机路径当作门禁真相源
- 密钥只允许来自 `.env` 或进程环境注入（CI secrets / 当前 shell export）。
- 禁止把 shell 登录配置作为测试密钥来源。
- 默认最小变量集沿用 `ENVIRONMENT.md` 的 Shared Core；涉及真实 provider 链路时，再追加对应 secrets。

<!-- docs:generated governance-snapshot start -->
## Generated Governance Snapshot

- `docs/testing.md` 现在以**策略解释**为主；高漂移 job inventory 已移到 `docs/generated/ci-topology.md`。
- PR 信任模型：仅同仓 trusted internal PR 允许进入 self-hosted 主链。
- docs gate 现在同时要求：`config/docs/*.json` control plane 一致、render output 新鲜、manual boundary 不越界。
<!-- docs:generated governance-snapshot end -->

## CI Topology (GitHub Actions)

以下口径按已拍板 D1~D5 执行，旧规则（E2E 默认 mock API）已废止。

- `preflight-fast` + `preflight-heavy`：预检门禁（runner baseline、env contract、schema parity、provider residual、worker line limits、structured log guard、e2e strictness guard、mutation scope guard、mutation test selection guard）。
- 严格执行型 job（`preflight-heavy`、`quality-gate-pre-push`、`db-migration-smoke`、`python-tests`、`api-real-smoke`、`pr-llm-real-smoke`、`dependency-vuln-scan`、`backend-lint-hosted`、`backend-lint-fallback`、`frontend-lint-hosted`、`frontend-lint-fallback`、`web-test-build`、`web-e2e`、`web-e2e-perceived`、`live-smoke`）统一运行在仓库自有标准镜像中，并通过仓库脚本/命令调 repo 内部 gate。
- 高漂移 CI job inventory、runner profile inventory、release evidence inventory 不再由本页手工维护；统一参考：
  - `docs/generated/ci-topology.md`
  - `docs/generated/runner-baseline.md`
  - `docs/generated/release-evidence.md`
- `db-migration-smoke` + `python-tests` + `api-real-smoke` + `backend-lint` + `frontend-lint` + `web-test-build` + `web-e2e` + `web-e2e-perceived`：并行执行的主链路测试集合。
- `web-test-build` 现在在 PR/push/schedule 都默认执行（只要 `preflight-fast` 与 `changes` 成功），避免 path-filter 误判导致关键 Web gate 被跳过。
- `web-test-build` 会追加阻断式 `Gemini UI/UX audit`，并上传 `.runtime-cache/ui-audit/gemini-ui-ux-audit-*.{json,log}` 作为审查工件；严格通过条件为 `status=passed`、`reason_code=ok`、`successful_batches==batch_count` 且 `model_attempts>0`。
- 当 Gemini 返回不可解析格式时，脚本会把该批次记为结构化阻断项并继续后续批次；报告中可通过 `reason_code=batch_failures_detected`、`failed_batch_count`、`failed_batches` 精确定位失败批次证据。
- `web-e2e`：CI 主路径使用真实 API（real API）执行完整端到端验证；`mock` 仅允许本地调试，不允许进入 CI gate。
- `web-e2e` 主路径不再忽略 `test_subscriptions.py`，订阅链路与 dashboard/feed/jobs/settings 同属主线回归范围。
- `web-e2e` real 链路包含 Temporal + API + worker 后台进程，`ingest/poll` 成功路径要求经过 worker 消费。
- `web-e2e` 作业结束会执行 worker 进程清理，并在 `always()` 分支上传 worker 日志 artifact 供排障。
- `live-smoke`：仅 `main` / `release` / nightly 强制执行，且不得 `skip` / `skipped`；PR 由 `pr-llm-real-smoke` 承担真实 LLM 烟测。
- `aggregate-gate`：汇总主链路结果；`api-real-smoke` / `web-e2e` 不允许 `skipped`，`live-smoke` 由 `ci-final-gate` 按触发源做强制校验。
- `ci-final-gate`：最终门禁；`main` / `release` / nightly 要求 `live-smoke=success`，PR 允许 `live-smoke=skipped`。
- `ci-kpi`：在 `ci-final-gate` 之后汇总 junit/coverage/mutation/artifact bytes/topology duplication，并输出 `reports/release-readiness/ci-kpi-summary.{json,md}` artifact。
- `build-ci-standard-image.yml` 会产出 strict CI 镜像 SBOM，并对镜像与 SBOM 做 attestation。
- `release-evidence-attest.yml` 会把 release manifest/checksums/rollback 证据打包成可 attestation 的 bundle。
- self-hosted CI 信任边界：当前仓库默认只支持 **trusted internal PR** 进入 privileged runner 主链；fork / untrusted PR 属于拒绝口径，不在支持矩阵内。

## Runner 标签策略（维护约定）

- 统一路由标签：默认 CI 作业使用 `runs-on: [self-hosted, video-analysis-extract]`。
- Docker 依赖型 required 作业（带 `container:` 或 `services:` 的严格路径）当前固定路由到 `core02` 子集：`runs-on: [self-hosted, video-analysis-extract, core02]`，用于绕开已知的 runner Docker daemon 权限不一致。
- 允许精细调度：如需额外分流，只能追加标签，不允许使用 runner 名称直绑。
- 关键约束：组织共享 runner 名称由治理侧统一维护，仓库 workflow 仅通过 label 调度。
- 禁止硬编码 runner 实例名（例如 `github-runner-core-03`）；统一用标签路由，避免扩缩容后工作流失效。
- `runner-health.yml` 负责 `runner-bootstrap` 健康阈值检查：验证 `pool-core..` 命名 runner 在线数量达到最小值，且 `video-analysis-extract` 标签路由目标在线可用；不得要求组织 runner 名单“精确匹配”。
- `ci.yml` 主路径不再承担 runner 运维职责；PR/push 的代码质量门禁从代码与合同真相直接起跑。

## Runner 宿主机健康巡检

- 只读巡检脚本：`scripts/audit_github_runner_host.sh`
- Startup script 真相源：`infra/gce/github-runner-org-startup.sh`
- 同步 metadata 脚本：`scripts/apply_github_runner_startup_metadata.sh`

只读巡检示例：

```bash
scripts/audit_github_runner_host.sh \
  --project project-73ca1c4a-1270-4025-a65 \
  --zone us-central1-a \
  --instance github-runner-core-02 \
  --runner-name pool-core02-03 \
  --repo-name video-analysis-extract
```

作用：

- 记录 instance metadata / serial port / SSH 巡检证据到 `.runtime-cache/temp/runner-health/<instance>/`
- 检查 `_work` 下是否存在 `~/.cache`、`.cache`、异常 `.runtime-cache/ms-playwright`
- 检查 `_work` 和目标 repo 下是否存在非 `ubuntu` owner 文件
- 汇总串口里的 `left-over process` / `Runner listener exited with error code 143` 证据

同步改良版 startup-script 到 runner 实例 metadata：

```bash
scripts/apply_github_runner_startup_metadata.sh \
  --project project-73ca1c4a-1270-4025-a65 \
  --zone us-central1-a \
  --instance github-runner-core-02
```

## D1~D5 决议与执行命令

- D1 `main` / `release` / nightly 强制 live-smoke（不得 skip）：

```bash
scripts/e2e_live_smoke.sh \
  --api-base-url "http://127.0.0.1:18080" \
  --require-api "1" \
  --require-secrets "1" \
  --computer-use-strict "1" \
  --computer-use-skip "0" \
  --timeout-seconds "600" \
  --heartbeat-seconds "30" \
  --diagnostics-json ".runtime-cache/e2e-live-smoke-result.json"
```

说明：`scripts/quality_gate.sh` 的 live-smoke profile gate 会校验 `scripts/e2e_live_smoke.sh` 默认值，其中 secrets requirement 必须保持为强制开启（与 D1 强制 secrets 口径一致）。

- D2 mutation 硬门禁阈值 `0.64`（并新增结构质量约束）：

```bash
./scripts/strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

说明：上面是本地 pre-push 口径；远端 `.github/workflows/ci.yml` 的 `quality-gate-pre-push` 为避免重复重型检查，使用 `--ci-dedupe 1 --skip-mutation 1`，mutation 由独立 job 执行。

- D3 Web 覆盖硬门禁 `global >=95` 且 `core >=95`，并且必须同时满足 `lines/functions/branches` 三个指标：

```bash
npm --prefix apps/web run test:coverage
python3 scripts/check_web_coverage_threshold.py \
  --summary-path apps/web/coverage/coverage-summary.json \
  --global-threshold 95 \
  --core-threshold 95 \
  --metric lines \
  --metric functions \
  --metric branches
```

- D4 集成 smoke 禁止 skip：PR 为 `api-real-smoke` / `web-e2e`，main/release/nightly 额外包含 `live-smoke`。
- D5 E2E CI 主路径必须全量 real API；`mock API` 仅用于本地 debug，不参与 CI 判定。

本地验收口径同步（与 CI 对齐）：

- 默认快速回归仍使用 sqlite 口径；但当 `quality_gate` 判定存在后端改动时，`pre-push` 会强制执行 `scripts/api_real_smoke_local.sh`（真实 Postgres + Temporal + worker）。
- 本地真实 Postgres integration smoke 的真相源是 `./scripts/api_real_smoke_local.sh`。
- `scripts/api_real_smoke_local.sh` 默认使用 `127.0.0.1:18080`；若默认端口已被占用且未显式传 `--api-port`，脚本会自动回退到下一个可用端口并记录诊断日志。
- `scripts/api_real_smoke_local.sh` 会在 cleanup workflow closure probe 前临时拉起一个本地 worker，并在脚本退出时自动回收，因此不再要求调用方先手动启动 worker。
- `scripts/api_real_smoke_local.sh` 现在包含本机 IPv4 loopback preflight；若主机先天无法建立 `127.0.0.1` 自连接，会直接输出 `failure_kind=host_loopback_ipv4_exhausted` 并 fail-fast，这属于环境级阻塞，不应误判为 API/worker 业务回归。
- 当执行 `./scripts/quality_gate.sh --mode pre-push --strict-full-run 1 ...` 时，必须额外跑本地真实 Postgres smoke。
- `strict-full-run=1` 会强制关闭 `--ci-dedupe` 且禁止 `--skip-mutation`，确保本地执行真实全量门禁。
- `scripts/smoke_full_stack.sh` 负责本地联调与 live smoke 相关检查，不是 `api-real-smoke` 的替代品。
- `UI Audit` 结果现会落盘到 `UI_AUDIT_RUN_STORE_DIR`（默认 `.runtime-cache/ui-audit-runs/`），避免 API 重启后审查记录丢失。
- `POST /api/v1/ui-audit/run` 的响应会携带 `gemini_review` 元信息；若返回 `status=completed_with_gemini_failure`，表示证据采集完成但 Gemini 深审失败，不能当作 UI 深审通过。
- UI Audit 高级运行时调优当前仅作为运行时可选覆盖，不属于 `.env.example` 的 strict contract 白名单；如需调整，请以服务端实现与严格 CI 契约为准。
- `POST /api/v1/ui-audit/{run_id}/autofix` 当前只会返回“持久化 dry-run 计划”；即使请求 `mode=apply`，响应中的 `mode` 也会明确回退到 `dry-run`，并在 `guardrails.requested_mode/effective_mode` 里说明。

## 测试类型与依赖边界（避免误解）

| 测试/作业 | 默认依赖类型 | 是否真实外部依赖 | 是否需要 secrets |
|---|---|---|---|
| `python-tests` | 以单测/组件测试为主（含 monkeypatch） | 否 | 否 |
| `api-real-smoke` | 真实 FastAPI + 真实 Postgres + 真实 migration | 否（不打外部 provider） | 否 |
| `pr-llm-real-smoke` | PR 真实 LLM 接口烟测（`/api/v1/computer-use/run`） | 是（调用真实 Gemini） | 是（仅 `GEMINI_API_KEY`） |
| `web-e2e` | Playwright UI 行为验证 + real API | 是（按 CI 主路径执行） | 视目标 API 而定 |
| `web-e2e` + `--web-e2e-base-url` | Playwright 复用外部 Web 实例 | 取决于目标实例 | 通常否 |
| `external-playwright-smoke` | Playwright 直连外部公共站点（`https://example.com`） | 是（真实外网） | 否（默认值由 job 参数提供，可按脚本参数覆盖） |
| `live-smoke` | 真实 `/api/v1/videos/process` + 真实 provider 链路 | 是（YouTube/Bilibili + Gemini/Resend） | 是（仅 main/release/nightly 必需） |

`pr-llm-real-smoke` 触发条件（PR 真实 LLM）：

- 仅 `pull_request` 事件。
- 仅在 `backend_changed == 'true'` 时运行（由 `changes` job 输出判定）。
- 仅同仓 PR（`head.repo.full_name == github.repository`），fork PR 不触发。
- `GEMINI_API_KEY` 不参与触发表达式；它是运行期必需 secret。触发后若缺失，作业失败（不是 `skipped`）。

CI `live-smoke` 必需 secrets（main/release/nightly）：

- `GEMINI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `YOUTUBE_API_KEY`

## 真实 Smoke 默认值与触发边界（与 CI 对齐）

- `pr-llm-real-smoke` 仅在以下条件同时满足时触发：
  - `github.event_name == 'pull_request'`
  - `needs.changes.outputs.backend_changed == 'true'`
  - `github.event.pull_request.head.repo.full_name == github.repository`（同仓 PR，fork PR 不触发）
- `external-playwright-smoke` 仅在 `push(main)` 与 nightly `schedule` 执行；默认参数：
  - `--url https://example.com`
  - `--browser chromium`
  - `--expect-text "Example Domain"`
  - `--timeout-ms 45000`
  - `--output-dir .runtime-cache/external-playwright-smoke`
- `--retries` 由 CI 显式传入 `vars.EXTERNAL_SMOKE_RETRIES || '2'`（默认 `2`，且脚本内部会做上限约束）
- `aggregate-gate` 对 `external-playwright-smoke` 的通过口径为 `success|skipped`（PR 下通常为 `skipped`）。

Live 诊断与执行策略（本地/CI 一致）：

- 环境变量优先级：先读仓库 `.env`，缺失项仅使用当前 shell 环境变量。
- reader 相关 smoke（`smoke_full_stack.sh` / `run_ai_feed_sync.sh`）只会从 `env/profiles/reader.env` 补齐缺失的 `MINIFLUX_*` / `NEXTFLUX_*` 变量，不会覆盖当前 shell 已显式注入的 reader 凭证。
- Batch B 契约口径：`e2e_live_smoke.sh` 与 `smoke_llm_real_local.sh` 的运行参数改为 CLI 优先；legacy env 仅兼容，不再建议在 `.env` 持久化。
- `YOUTUBE_API_KEY` 失效修复：`e2e_live_smoke.sh` 会按 `.env` → 当前 shell 环境变量自动探测可用 key，并在修复成功后回写 `.env`（日志仅展示脱敏 key 片段）。
- 若所有来源都无效：脚本直接失败，并输出“需要用户提供有效key”。
- `scripts/smoke_computer_use_local.sh` 默认严格判定：只有 `status=200` 且响应字段完整才算 `passed`；遇到 provider 未开通能力会失败（不是隐式 skip）。
- 若确需允许 provider 能力未开通时的跳过，必须显式传 `--allow-unsupported-skip=1`，并在日志中出现 `result=skipped`。
- 失败分类：诊断 JSON 必须携带 `failure_kind`，取值为 `code_logic_error` 或 `network_or_environment_timeout`。
- `--offline-fallback` 口径（去除假通过）：
  - `scripts/smoke_full_stack.sh` 默认 `--offline-fallback 0`（fail-fast）。
  - `scripts/bootstrap_full_stack.sh` 默认 `--offline-fallback 1`；core/reader 启动失败时会写入 `.runtime-cache/full-stack/offline-fallback.flag`。
  - 标准 `local` / `ci` / `live-smoke` profile 的执行建议显式传 `--offline-fallback 0`，保持口径固定（核心服务或 reader 栈异常立即失败）。
  - 当显式启用 `--offline-fallback 1` 且命中 `.runtime-cache/full-stack/offline-fallback.flag` 时，`smoke_full_stack.sh` 会跳过 reader checks 并输出 degraded 信息。
  - 降级路径不改变 `e2e_live_smoke` 的失败分类枚举；`failure_kind` 仍仅使用上述两类值。
  - `smoke_full_stack.sh` 是本地联调 smoke，不是 `api-real-smoke` 的替代品。
- 长任务可观测：live 脚本输出 heartbeat 与 phase 进度日志（`phase=short_tests` / `phase=long_tests`）。
- 顺序规则：先 short tests 再 long tests，再执行 `phase=teardown`（仅做安全清理，不做破坏性操作）。
- 写操作约束：live smoke 仅执行可重复验证写入；诊断 JSON 必须包含 `write_operations[].idempotency_key`、`write_operations[].cleanup_action`、`teardown.steps[]`、`youtube_key_resolution[]`。

## 本地复现两类真实 Smoke（CI 同口径）

1. 复现 `external-playwright-smoke`：

```bash
uv sync --frozen --extra dev --extra e2e
uv run --with playwright python -m playwright install --with-deps chromium
uv run --with playwright bash scripts/external_playwright_smoke.sh \
  --url "https://example.com" \
  --browser "chromium" \
  --expect-text "Example Domain" \
  --timeout-ms "45000" \
  --output-dir ".runtime-cache/external-playwright-smoke"
```

2. 复现 `pr-llm-real-smoke`：

```bash
export GEMINI_API_KEY='<your-key>'
export DATABASE_URL='sqlite+pysqlite:////tmp/video-digestor-pr-llm-real-smoke.db'
export TEMPORAL_TARGET_HOST='127.0.0.1:7233'
export TEMPORAL_NAMESPACE='default'
export TEMPORAL_TASK_QUEUE='video-analysis-worker'
export SQLITE_STATE_PATH='/tmp/video-digestor-pr-llm-real-state.db'
export NOTIFICATION_ENABLED='0'
export UI_AUDIT_GEMINI_ENABLED='false'
export VD_API_KEY='local-dev-token'

mkdir -p .runtime-cache
uv run --with uvicorn uvicorn apps.api.app.main:app --host 127.0.0.1 --port 18081 > .runtime-cache/pr-llm-real-smoke.log 2>&1 &
api_pid=$!
trap 'kill ${api_pid} >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:18081/healthz" >/dev/null && break
  sleep 1
done
scripts/smoke_llm_real_local.sh --api-base-url "http://127.0.0.1:18081"
```

3. 复现本地真实 Postgres integration smoke（对齐 CI `api-real-smoke`）：

```bash
export DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:5432/video_analysis'
export API_INTEGRATION_SMOKE_STRICT='1'
./scripts/api_real_smoke_local.sh
```

说明：

- 这条命令会基于当前 `DATABASE_URL` 指向的 Postgres 实例创建隔离 smoke 数据库，补跑 `infra/migrations/*.sql`、真实启动本地 API，并执行 `apps/api/tests/test_api_integration_smoke.py`。这条命令本身不是 CI 等价入口，CI 等价入口是标准镜像内的 `strict_ci_entry`.
- 默认 sqlite 总回归里的 integration smoke `xfail` 只表示“当前是快速回归口径”，不表示真实 Postgres 路径坏掉。
- 标准严格验收唯一入口：`./scripts/strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0`。

## Full-stack 本地自测（稳定性）

```bash
./scripts/full_stack.sh up
./scripts/full_stack.sh status
./scripts/full_stack.sh down
./scripts/full_stack.sh status
```

说明：

- `up` 会等待 API health 与 Web 端口就绪，失败时输出 `logs/full-stack/*.log` 关键片段，便于快速定位。
- 后台 `up` 场景调用 `./scripts/dev_api.sh --no-reload`，避免 `status` 因 reload 父子进程变化误判 `stopped`。
- stronger Temporal readiness 已接入 `./scripts/full_stack.sh up`：在启动 API/Web/Worker 之前，先校验 worker 必需环境，再对 `TEMPORAL_TARGET_HOST` 执行 `host:port` 解析与 TCP 探测；失败会以 `stage=worker_preflight_temporal`、`conclusion=temporal_not_ready` fail-fast，不再等到 worker 启动后才暴露。

## 触发差异（PR vs main/release vs nightly）

| 触发源 | 必跑项 | 可跳过项 | 强制门禁 |
|---|---|---|---|
| `pull_request` | `preflight-*`、按变更触发的 `db-migration-smoke`、`python-tests`、`api-real-smoke`、`pr-llm-real-smoke`、`backend-lint`、`frontend-lint`、`web-test-build`、`web-e2e(real API)`、`quality-gate-pre-push`、`aggregate-gate`、`ci-final-gate` | `live-smoke`（仅 main/release/nightly） | 集成 smoke（`api-real-smoke` / `web-e2e`）禁止 `skip` / `skipped`，必须 `success` |
| `push` 到 `main`/`release` | `pull_request` 全部必跑项 + `profile-governance` + `quality-gate-pre-push` + `external-playwright-smoke` | 无 | `aggregate-gate` 与 `ci-final-gate` 全链路强制 `success` |
| `schedule` nightly | `main/release` 全部必跑项 + `nightly-flaky-*` | 无 | `live-smoke`、`nightly-flaky-*`、集成 smoke 全部必须 `success` |

## Run Commands

### 0) 假断言门禁（全仓）

```bash
python3 scripts/check_test_assertions.py
```

说明：

- 默认禁止 `expect(true).toBe(true)`、`expect("x").toEqual("x")`、`expect(1).toBe(1)` 等左右同字面量断言。
- 默认禁止 `toBeDefined()`；如确有必要，可在同一行或上一行添加注释标记：
  `// allow-low-value-assertion: toBeDefined`

### 0.1) 一键质量门禁（推荐）

```bash
./scripts/strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

### 0.1.A) 本地后端验收分层（必须区分）

- 默认快速回归（sqlite）：用于日常本地回归与速度优先场景。
- 真实集成验收（Postgres）：用于对齐 CI `api-real-smoke`，避免“sqlite 下 xfail 但真实环境已通过”的歧义。
- `API_INTEGRATION_SMOKE_STRICT` 语义：
  - `unset/0`：环境不满足时允许 integration smoke 按约定 `xfail`（默认本地快速回归模式）。
  - `1`：环境不满足或测试失败时直接失败（严格本地验收模式）。

标准严格验收命令（无歧义口径）：

```bash
./scripts/full_stack.sh up
./scripts/api_real_smoke_local.sh
./scripts/smoke_full_stack.sh --offline-fallback 0
./scripts/quality_gate.sh --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

### 0.1.1) 一键最终门禁集成验收（profile -> pre-commit -> pre-push）

```bash
bash scripts/env/final_governance_check.sh
```

如需仅执行到 pre-commit（跳过 pre-push）：

```bash
bash scripts/env/final_governance_check.sh --skip-prepush
```

默认策略（阻断）：

- 全仓 Lint 错误必须为 0（`npm --prefix apps/web run lint` + `uv run --with ruff ruff check apps scripts`）。
- 禁止安慰剂断言（`python3 scripts/check_test_assertions.py --path .`）。
- E2E 严格性守卫必须通过（`python3 scripts/check_e2e_strictness.py`，拦截硬等待与成功/失败混合断言模式）。
- 变异目标范围守卫必须通过（`python3 scripts/check_mutation_scope.py`，防止 `paths_to_mutate` 缩水或丢失核心模块）。
- 变异测试选择守卫必须通过（`python3 scripts/check_mutation_test_selection.py`，防止 `pytest_add_cli_args_test_selection` 缩水导致大量 `no_tests`）。
- Secrets 泄漏扫描必须通过（`sk-*` / `ghp_*` / `AKIA*` / 私钥头模式）。
- 空洞日志文案扫描必须通过（禁止 `Something went wrong` / `unexpected error` / `error occurred` / `unknown error`）。
- 文档漂移门禁强制执行（staged/push）。
- 覆盖率阈值：总覆盖率 `>=95%`，核心模块覆盖率 `>=95%`（worker pipeline + api 核心 router/service）。
- Web 覆盖率硬门禁：`lines/functions/branches` 三指标均需满足 `global >=95%` 且 `core >=95%`（默认读取 `apps/web/coverage/coverage-summary.json`）。
- Web 交互覆盖门禁：`python3 scripts/check_web_button_coverage.py --threshold 1.0 --e2e-threshold 0.6 --unit-threshold 0.93`，分别校验 combined / E2E / unit 三段口径。
  - source 范围默认覆盖 `apps/web/app` + `apps/web/components`（自动排除 `__tests__`、`node_modules`、`.next`）。
  - E2E 口径仅统计 Playwright pytest 中真实 `.click()` 的 `button/link` 交互，不再把仅 `get_by_role` 查询视为覆盖。
  - 当前保留例外：全局错误边界内的 `重试页面` 按钮仍以 unit 覆盖为主（combined 仍需 100%）。
- 变异测试门禁强制执行（Python 核心模块）：CI/Hook 执行口径为 mutation score `>=0.64`，并要求 `effective_ratio>=0.27`、`no_tests_ratio<=0.72`；`quality_gate.sh` 裸跑默认阈值为 `0.64`，可通过参数覆盖。
- Web/依赖变更命中时，CI 会执行阻断式 `Gemini UI/UX audit`：必须同时满足 `status=passed`、`reason_code=ok`、`successful_batches==batch_count` 且 `model_attempts>0`；只有“真的调过模型且所有批次成功”才算真绿。
- `pre-push` 采用 fail-fast：先短检查，再长测试；长测试并行执行并输出 heartbeat。
- `pre-push` 后端链路新增硬门禁：`api cors preflight smoke (OPTIONS DELETE)` 与 `contract diff local gate (base vs head)`。
- `pre-push` 与远端 CI `preflight-fast`/`web-test-build` 关键阻断项对齐：`check_ci_docs_parity`、`docs env canonical guard`、`provider residual guard`、`worker line limits guard`、`schema parity gate`、`web design token guard`、`web build`、`web button coverage`。
- Env 预算门禁强制执行（防反弹）：`core<=20`、`runtime<=100`、`scripts<=120`、`universe<=216`（`python3 scripts/check_env_budget.py`）。
- 远程 CI 成本治理：任何远程重跑前必须先本地 pre-push 全绿；远程失败后先本地复现修复再重跑。

### 0.1.2) Web 覆盖率硬门禁（Vitest json-summary）

```bash
npm --prefix apps/web run test:coverage
python3 scripts/check_web_coverage_threshold.py \
  --summary-path apps/web/coverage/coverage-summary.json \
  --global-threshold 95 \
  --core-threshold 95 \
  --metric lines \
  --metric functions \
  --metric branches
```

可选参数：

- `--metric lines|statements|functions|branches`（可重复，默认 `lines/functions/branches`）。
- `--core-pattern '<glob>'`（可重复传入；默认 core 口径覆盖 `apps/web/lib` 与 `apps/web/components` 的直接文件和递归子目录文件）。
- `--dry-run`（仅打印配置与路径，不读取 coverage 文件）。

artifact 口径：

- 输入：`apps/web/coverage/coverage-summary.json`（Vitest `json-summary` 输出）。
- 输出：stdout 打印 gate 结果与失败原因；失败时返回码 `1`（硬阻断）。

### 0.2) Git Hook 强制门禁（commit-msg / pre-commit / pre-push）

```bash
./scripts/install_git_hooks.sh
```

可选：直接安装 pre-commit framework hooks（会写入当前 `core.hooksPath`）：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

协同口径（与仓库现状一致）：

- 默认强制链路：`.githooks/* -> quality_gate/commitlint`。
- `.pre-commit-config.yaml`：统一可复用 checks（手动执行、全量清洗、版本保养）。
- 当前 `.githooks` 不直接调用 `pre-commit run`，因此 `pre-commit` 在本仓库是“补充工具链”，不是唯一强制入口。

Big Bang 全量清洗（建议在大改前执行）：

```bash
pre-commit run --all-files
```

detect-secrets baseline（可选补充流程，默认强制 secrets 门禁仍为 gitleaks）：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

月度保养（建议每月一次）：

```bash
pre-commit autoupdate
pre-commit run --all-files
```

提交信息本地校验（Conventional Commits）：

```bash
echo "feat(api): add ingest health guard" > /tmp/commit-msg-ok.txt
.githooks/commit-msg /tmp/commit-msg-ok.txt
```

### 0.3) Hooks 与文档联动规则对齐（必须执行）

当前 Git Hooks 的实际检查项：

- `commit-msg`：
  - `npx --yes --package @commitlint/cli commitlint --config <tmp-config> --edit <commit-msg-file>`
  - 规则基于 Conventional Commits（例如 `feat: ...`、`fix(scope): ...`）。
  - 仓库根目录无 `package.json` 时，使用 `npx --yes` 临时拉取 `commitlint` + hook 内置最小规则配置，无需新增根依赖即可运行。
- `pre-commit`：
  - `python3 scripts/check_env_contract.py --strict`
  - `python3 scripts/check_env_budget.py`
  - `python3 scripts/check_test_assertions.py --path .`
  - secrets 泄漏扫描（阻断）
  - `bash scripts/ci_or_local_gate_doc_drift.sh --scope staged`
  - `python3 scripts/check_ci_docs_parity.py`
  - `schema parity gate`（`apps/mcp/schemas/tools.json` vs `packages/shared-contracts/jsonschema/mcp-tools.schema.json`）
  - `python3 scripts/check_mutation_scope.py`
  - `python3 scripts/check_mutation_test_selection.py`
  - `npm --prefix apps/web run lint`
  - `uv run --with ruff ruff check apps scripts`
- `pre-push`：
  - `python3 scripts/check_env_contract.py --strict`
  - `python3 scripts/check_env_budget.py`
  - `bash scripts/ci_or_local_gate_doc_drift.sh --scope push`
  - `python3 scripts/check_test_assertions.py --path .`
  - secrets 泄漏扫描（阻断）
  - `npm --prefix apps/web run lint`
  - `uv run --with ruff ruff check apps scripts`
  - `npm --prefix apps/web run test:coverage`
  - `python3 scripts/check_web_coverage_threshold.py --summary-path apps/web/coverage/coverage-summary.json --global-threshold 95 --core-threshold 95 --metric lines --metric functions --metric branches`
  - `uv run pytest ... --cov-fail-under=95`
  - `python skip guard`（junit `tests>0` 且 `skipped=0`）
  - `uv run coverage report ... --fail-under=95`（worker core / api core）
  - `python3 scripts/check_ci_docs_parity.py`
  - `bash scripts/guard_provider_residuals.sh .`
  - `python3 scripts/check_worker_line_limits.py`
  - `schema parity gate`（`apps/mcp/schemas/tools.json` vs `packages/shared-contracts/jsonschema/mcp-tools.schema.json`）
  - `python3 scripts/check_design_tokens.py --from-ref <merge_base> --to-ref HEAD apps/web`（回退 `--all-lines`）
  - `npm --prefix apps/web run build`
  - `python3 scripts/check_web_button_coverage.py --threshold 1.0 --e2e-threshold 0.6 --unit-threshold 0.93`
  - 交互覆盖脚本默认扫描 `apps/web/app` 与 `apps/web/components`，并要求 E2E 用例使用真实点击断言（`.click()`）。
  - `DATABASE_URL='sqlite+pysqlite:///:memory:' uv run --extra dev --with mutmut mutmut run`
  - `uv run --extra dev --with mutmut mutmut export-cicd-stats`
  - `python3 -c '...读取 mutants/mutmut-cicd-stats.json 并校验 score/effective_ratio/no_tests_ratio 阈值...'`（CI/Hook 常用阈值 `score>=0.64`；脚本裸跑默认 `0.64`）

变异测试工具不可用策略（阻断）：

- 若 `uv` 不可用：直接失败并提示安装 `uv`，禁止静默跳过。
- 若 `mutmut` 安装/执行失败：直接失败并提示执行 `uv sync --frozen --extra dev --extra e2e`。
- 若无有效突变体（`killed + survived == 0`）：直接失败，视为门禁无效配置。

文档联动强制规则（提交时人工校验，hooks 不会自动补）：

- 变更 `infra/migrations/*.sql`：同步 `README.md` 与 `docs/runbook-local.md`。
- 变更 `apps/worker/worker/pipeline/types.py` 的 `PIPELINE_STEPS`：同步 `docs/state-machine.md`。
- 新增/修改环境变量：同步 `.env.example`、`ENVIRONMENT.md`、`infra/config/env.contract.json`。
- 调整 API 行为或签名（`apps/api/app/routers/*.py`、`apps/api/app/services/*.py`、`apps/mcp/**/*.py`）：同步 `README.md`、`docs/runbook-local.md`、`docs/testing.md`。
- 调整 Schema 签名（`apps/mcp/schemas/tools.json`、`packages/shared-contracts/jsonschema/*.json`）：同步 `docs/testing.md`。
- 调整本地启动脚本参数/默认值（`scripts/dev_*.sh`、`scripts/full_stack.sh`、`scripts/bootstrap_full_stack.sh`、`scripts/smoke_full_stack.sh`）：同步 `docs/start-here.md`、`docs/runbook-local.md`、`README.md`。
- 调整日志/缓存/依赖策略：同步 `docs/reference/logging.md`、`docs/reference/cache.md`、`docs/reference/dependency-governance.md`。

### 1) Python tests (worker/api/mcp, xdist=2)

```bash
PYTHONPATH="$PWD:$PWD/apps/worker" \
DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run \
  --with pytest \
  --with pytest-xdist \
  --with fastapi \
  --with httpx \
  --with sqlalchemy \
  --with psycopg \
  --with pydantic \
  --with mcp \
  pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -n 2
```

### 1.1) MCP jobs normalizer（重点）

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
  pytest apps/mcp/tests/test_tool_normalizers.py -q
```

该用例应覆盖 `vd.jobs.get` 归一化后的关键字段保留：

- `steps`
- `degradations`
- `pipeline_final_status`
- `llm_required`
- `llm_gate_passed`
- `hard_fail_reason`
- `artifacts_index`
- `mode`

### 2) Playwright E2E

```bash
uv run --with playwright playwright install chromium

uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

说明：

- E2E CI 主路径必须连接 real API（真实 API），覆盖端到端关键旅程，不允许使用 mock API 作为 CI 默认路径。
- mock API 仅允许本地调试（developer debug）使用，且不得作为 PR/main/release 门禁证据。
- 运行前需确保 `apps/web/node_modules` 已安装（例如先执行 `cd apps/web && npm ci`）。

CI 中 `web-e2e` 的 real API 启动口径（Postgres + migrations + uvicorn）：

```bash
export DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:5432/video_analysis'
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -f "${migration}"
done
export TEMPORAL_CLI_VERSION='1.5.1'
export TEMPORAL_CLI_SHA256_LINUX_AMD64='ddc95e08b0b076efd4ea9733a3f488eb7d2be875f8834e616cd2a37358b4852d'
export TEMPORAL_CLI_SHA256_LINUX_ARM64='bd1b0db9f18b051026de8bf6cc1505f2510f14bbb7a8b9a4a91fff46c77454f5'
arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) temporal_arch="amd64"; expected_sha="$TEMPORAL_CLI_SHA256_LINUX_AMD64" ;;
  aarch64|arm64) temporal_arch="arm64"; expected_sha="$TEMPORAL_CLI_SHA256_LINUX_ARM64" ;;
  *) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
esac
archive="temporal_cli_${TEMPORAL_CLI_VERSION}_linux_${temporal_arch}.tar.gz"
url="https://github.com/temporalio/cli/releases/download/v${TEMPORAL_CLI_VERSION}/${archive}"
curl -fsSL "$url" -o "/tmp/${archive}"
echo "${expected_sha}  /tmp/${archive}" | sha256sum -c -
tar -xzf "/tmp/${archive}" -C /tmp temporal
mkdir -p "$HOME/.local/bin"
install -m 0755 /tmp/temporal "$HOME/.local/bin/temporal"
export PATH="$HOME/.local/bin:$PATH"
temporal server start-dev --ip 127.0.0.1 --port 7233 > .runtime-cache/web-e2e-temporal.log 2>&1 &
uv run --with uvicorn uvicorn apps.api.app.main:app --host 127.0.0.1 --port 18081 \
  > .runtime-cache/web-e2e-real-api.log 2>&1 &
```

顺序必须是先启动并确认 Temporal（`127.0.0.1:7233`）可用，再启动 `uvicorn`，避免 real API 在 Temporal 未就绪时失败。

- stronger Temporal readiness 也已接入 `./scripts/ci_web_e2e.sh`：脚本会先 `start_temporal` 并阻塞到 `wait_for_tcp "$WEB_E2E_TEMPORAL_PORT"` 成功，再依次启动 API 与 worker，避免把 Temporal 未就绪误判成后续 API/worker 启动问题。

`conftest` 参数 `--web-e2e-api-base-url` 用法（将 Web E2E 指向 real API）：

```bash
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q \
  --web-e2e-base-url 'http://127.0.0.1:3000' \
  --web-e2e-api-base-url 'http://127.0.0.1:18081'
```

说明：

- `--web-e2e-api-base-url` 由 `apps/web/tests/e2e/conftest.py` 读取，用于覆盖 E2E 运行时的 API 基地址（默认不应指向 mock）。
- CI 证据必须来自 real API 路径（含 Postgres + migrations + uvicorn）；mock 仅本地调试使用，不能作为 CI 通过依据。

外部 Base URL 模式（复用已有 Web 实例，不启动本地 Next.js）：

```bash
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q \
  --web-e2e-base-url 'http://127.0.0.1:3000'
```

说明：

- `--web-e2e-base-url` 必须是绝对 `http(s)` URL。
- 使用外部模式时，请确保目标 Web 已启动且其 API 指向与测试预期一致。

### 3) Web 静态检查

```bash
cd apps/web
npm run lint
```

## Notes

- `apps/web/tests/e2e/test_smoke_playwright.py` 覆盖关键按钮链路（dashboard / subscriptions / settings / jobs->artifacts），并对重定向提示与请求负载做强断言。
- 由于当前 Web 代码尚未完成 Next.js 16 `searchParams` 异步迁移，`jobs -> artifacts` 用例会先断言查询跳转与页面占位状态（`No artifact loaded yet.`）；迁移后可升级为 markdown/screenshot 区块可见性断言。
- API 路由测试会通过 `monkeypatch` 隔离 Temporal/数据库外部依赖，验证路由层映射行为。
- 需要访问真实依赖（Postgres/Temporal）的端到端链路，可在后续补专门的 integration 套件。
- CI 缓存策略：工具缓存统一收口在 `/tmp/ci-cache` 及其派生路径（如 `UV_CACHE_DIR=/tmp/ci-cache/uv`、`PLAYWRIGHT_BROWSERS_PATH=/tmp/ci-cache/ms-playwright`）；测试与 e2e 产物统一写入 repo 内的 `.runtime-cache` 并作为 artifact 上传。
- 禁止项：`actions/cache` 或工具缓存环境变量不得指向 `~/.cache/**`、`${{ github.workspace }}/**`、相对 repo 路径（如 `.runtime-cache/**`、`.cache/**`、`cache/**`、`.venv`）。这些路径会在 shared self-hosted runner 上制造工作区污染。
- Checkout 规则：所有 workflow 中的 `actions/checkout` 必须显式声明 `with.clean: true`，不能依赖默认值。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->


<!-- doc-sync: mcp/web contract and schema alignment (2026-03-03) -->


<!-- doc-sync: mcp api-client redaction fixture adjustment (2026-03-03) -->


<!-- doc-sync: integration smoke uses xfail instead of skip when env unmet (2026-03-03) -->


<!-- doc-sync: ci failure fixes (integration smoke auth + ci_autofix timezone compatibility) (2026-03-03) -->
