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
  - profile：通过脚本参数 `--profile local|gce` 选择运行画像
- 密钥只允许来自 `.env` 或进程环境注入（CI secrets / 当前 shell export）。
- 禁止把 shell 登录配置作为测试密钥来源。
- 默认最小变量集沿用 `ENVIRONMENT.md` 的 Shared Core；涉及真实 provider 链路时，再追加对应 secrets。

## CI Topology (GitHub Actions)

以下口径按已拍板 D1~D5 执行，旧规则（E2E 默认 mock API）已废止。

- `preflight-fast` + `preflight-heavy`：预检门禁（env contract、schema parity、provider residual、worker line limits、structured log guard、e2e strictness guard、mutation scope guard、mutation test selection guard）。
- `db-migration-smoke` + `python-tests` + `api-real-smoke` + `backend-lint` + `frontend-lint` + `web-test-build` + `web-e2e`：并行执行的主链路测试集合。
- `web-e2e`：CI 主路径使用真实 API（real API）执行完整端到端验证；`mock` 仅允许本地调试，不允许进入 CI gate。
- `web-e2e` real 链路包含 Temporal + API + worker 后台进程，`ingest/poll` 成功路径要求经过 worker 消费。
- `web-e2e` 作业结束会执行 worker 进程清理，并在 `always()` 分支上传 worker 日志 artifact 供排障。
- `live-smoke`：仅 `main` / `release` / nightly 强制执行，且不得 `skip` / `skipped`；PR 由 `pr-llm-real-smoke` 承担真实 LLM 烟测。
- `aggregate-gate`：汇总主链路结果；`api-real-smoke` / `web-e2e` 不允许 `skipped`，`live-smoke` 由 `ci-final-gate` 按触发源做强制校验。
- `ci-final-gate`：最终门禁；`main` / `release` / nightly 要求 `live-smoke=success`，PR 允许 `live-smoke=skipped`。

## Runner 标签策略（维护约定）

- 统一路由标签：所有 CI 作业固定使用 `runs-on: [self-hosted, shared-pool]`。
- 允许精细调度：如需额外分流，只能追加标签，不允许使用 runner 名称直绑。
- 关键约束：组织共享 runner 名称由治理侧统一维护，仓库 workflow 仅通过 label 调度。
- 禁止硬编码 runner 实例名（例如 `github-runner-spot-02`）；统一用标签路由，避免扩缩容后工作流失效。

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

- D2 mutation 硬门禁阈值 `0.62`（并新增结构质量约束）：

```bash
./scripts/quality_gate.sh \
  --mode pre-push \
  --heartbeat-seconds 20 \
  --mutation-min-score 0.62 \
  --mutation-min-effective-ratio 0.25 \
  --mutation-max-no-tests-ratio 0.75 \
  --profile ci \
  --profile live-smoke \
  --ci-dedupe 0
```

说明：上面是本地 pre-push 口径；远端 `.github/workflows/ci.yml` 的 `quality-gate-pre-push` 为避免重复重型检查，使用 `--ci-dedupe 1 --skip-mutation 1`，mutation 由独立 job 执行。

- D3 Web 覆盖硬门禁 `global >=85` 且 `core >=95`：

```bash
npm --prefix apps/web run test -- --coverage
python3 scripts/check_web_coverage_threshold.py \
  --summary-path apps/web/coverage/coverage-summary.json \
  --global-threshold 85 \
  --core-threshold 95
```

- D4 集成 smoke 禁止 skip：PR 为 `api-real-smoke` / `web-e2e`，main/release/nightly 额外包含 `live-smoke`。
- D5 E2E CI 主路径必须全量 real API；`mock API` 仅用于本地 debug，不参与 CI 判定。

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
- Batch B 契约口径：`e2e_live_smoke.sh` 与 `smoke_llm_real_local.sh` 的运行参数改为 CLI 优先；legacy env 仅兼容，不再建议在 `.env` 持久化。
- `YOUTUBE_API_KEY` 失效修复：`e2e_live_smoke.sh` 会按 `.env` → 当前 shell 环境变量自动探测可用 key，并在修复成功后回写 `.env`（日志仅展示脱敏 key 片段）。
- 若所有来源都无效：脚本直接失败，并输出“需要用户提供有效key”。
- 失败分类：诊断 JSON 必须携带 `failure_kind`，取值为 `code_logic_error` 或 `network_or_environment_timeout`。
- `--offline-fallback` 口径（去除假通过）：
  - `scripts/smoke_full_stack.sh` 默认 `--offline-fallback 1`。
  - 标准 `local` / `ci` / `live-smoke` profile 的执行建议显式传 `--offline-fallback 0`，保持 fail-fast（核心服务或 reader 栈异常立即失败）。
  - 当显式启用 `--offline-fallback 1` 且命中 `.runtime-cache/full-stack/offline-fallback.flag` 时，`smoke_full_stack.sh` 会跳过 reader checks 并输出 degraded 信息。
  - 降级路径不改变 `e2e_live_smoke` 的失败分类枚举；`failure_kind` 仍仅使用上述两类值。
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

## 触发差异（PR vs main/release vs nightly）

| 触发源 | 必跑项 | 可跳过项 | 强制门禁 |
|---|---|---|---|
| `pull_request` | `preflight-*`、`db-migration-smoke`、`python-tests`、`api-real-smoke`、`pr-llm-real-smoke`、`backend-lint`、`frontend-lint`、`web-test-build`、`web-e2e(real API)`、`aggregate-gate`、`ci-final-gate` | `live-smoke`（仅 main/release/nightly） | 集成 smoke（`api-real-smoke` / `web-e2e`）禁止 `skip` / `skipped`，必须 `success` |
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
./scripts/quality_gate.sh
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
- 覆盖率阈值：总覆盖率 `>=85%`，核心模块覆盖率 `>=95%`（worker pipeline + api 核心 router/service）。
- Web 覆盖率硬门禁：`global >=85%` 且 `core >=95%`（默认读取 `apps/web/coverage/coverage-summary.json`）。
- 变异测试门禁强制执行（Python 核心模块）：CI/Hook 执行口径为 mutation score `>=0.62`，并要求 `effective_ratio>=0.25`、`no_tests_ratio<=0.75`；`quality_gate.sh` 裸跑默认阈值为 `0.62`，可通过参数覆盖。
- `pre-push` 采用 fail-fast：先短检查，再长测试；长测试并行执行并输出 heartbeat。
- `pre-push` 后端链路新增硬门禁：`api cors preflight smoke (OPTIONS DELETE)` 与 `contract diff local gate (base vs head)`。
- `pre-push` 与远端 CI `preflight-fast`/`web-test-build` 关键阻断项对齐：`check_ci_docs_parity`、`docs env canonical guard`、`provider residual guard`、`worker line limits guard`、`schema parity gate`、`web design token guard`、`web build`、`web button coverage`。
- Env 预算门禁强制执行（防反弹）：`core<=20`、`runtime<=100`、`scripts<=120`、`universe<=216`（`python3 scripts/check_env_budget.py`）。
- 远程 CI 成本治理：任何远程重跑前必须先本地 pre-push 全绿；远程失败后先本地复现修复再重跑。

### 0.1.2) Web 覆盖率硬门禁（Vitest json-summary）

```bash
npm --prefix apps/web run test -- --coverage
python3 scripts/check_web_coverage_threshold.py \
  --summary-path apps/web/coverage/coverage-summary.json \
  --global-threshold 85 \
  --core-threshold 95
```

可选参数：

- `--metric lines|statements|functions|branches`（默认 `lines`）。
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
  - `npm --prefix apps/web run test -- --coverage`
  - `python3 scripts/check_web_coverage_threshold.py --summary-path apps/web/coverage/coverage-summary.json --global-threshold 85 --core-threshold 95`
  - `uv run pytest ... --cov-fail-under=85`
  - `python skip guard`（junit `tests>0` 且 `skipped=0`）
  - `uv run coverage report ... --fail-under=95`（worker core / api core）
  - `python3 scripts/check_ci_docs_parity.py`
  - `bash scripts/guard_provider_residuals.sh .`
  - `python3 scripts/check_worker_line_limits.py`
  - `schema parity gate`（`apps/mcp/schemas/tools.json` vs `packages/shared-contracts/jsonschema/mcp-tools.schema.json`）
  - `python3 scripts/check_design_tokens.py --from-ref <merge_base> --to-ref HEAD apps/web`（回退 `--all-lines`）
  - `npm --prefix apps/web run build`
  - `python3 scripts/check_web_button_coverage.py --threshold 1.0`
  - `DATABASE_URL='sqlite+pysqlite:///:memory:' uv run --extra dev --with mutmut mutmut run`
  - `uv run --extra dev --with mutmut mutmut export-cicd-stats`
  - `python3 -c '...读取 mutants/mutmut-cicd-stats.json 并校验 score/effective_ratio/no_tests_ratio 阈值...'`（CI/Hook 常用阈值 `score>=0.62`；脚本裸跑默认 `0.62`）

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
- CI 缓存策略：`web-test-build`、`web-e2e`、`nightly-flaky-web-e2e`、`dependency-vuln-scan` 都使用 `setup-node` 的 npm 缓存（锁文件 `apps/web/package-lock.json`）；Python 使用 `actions/cache@v4` 缓存 `~/.cache/uv`，Playwright 浏览器二进制使用 `actions/cache@v4` 缓存 `~/.cache/ms-playwright`；测试与 e2e 产物统一写入 `.runtime-cache` 并作为 artifact 上传。


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->


<!-- doc-sync: mcp/web contract and schema alignment (2026-03-03) -->


<!-- doc-sync: mcp api-client redaction fixture adjustment (2026-03-03) -->


<!-- doc-sync: integration smoke uses xfail instead of skip when env unmet (2026-03-03) -->


<!-- doc-sync: ci failure fixes (integration smoke auth + ci_autofix timezone compatibility) (2026-03-03) -->
