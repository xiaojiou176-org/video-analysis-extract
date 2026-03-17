# Start Here (1-Minute Onboarding)

这是仓库唯一上手入口。先照抄执行，再按导航 Lazy-Load 到对应模块。

## AI 导航索引（Lazy-Load）

1. 根级治理（先读）

- `AGENTS.md`
- `CLAUDE.md`

2. 模块按需加载（只在改对应模块时再读）

- API：`apps/api/AGENTS.md`、`apps/api/CLAUDE.md`
- Worker：`apps/worker/AGENTS.md`、`apps/worker/CLAUDE.md`
- MCP：`apps/mcp/AGENTS.md`、`apps/mcp/CLAUDE.md`
- Web：`apps/web/AGENTS.md`、`apps/web/CLAUDE.md`

3. 运行与契约（按问题深度继续）

- `docs/runbook-local.md`
- `docs/state-machine.md`
- `docs/testing.md`
- `ENVIRONMENT.md`
- `docs/reference/runner-baseline.md`
- `docs/reference/root-governance.md`
- `docs/reference/architecture-governance.md`
- `docs/reference/runtime-cache-retention.md`
- `docs/reference/evidence-model.md`
- `docs/reference/upstream-governance.md`

## 你需要先知道的 5 件事

1. 流程口径：`ProcessJobWorkflow = 3 阶段 + content_type 分流 pipeline`（video 9-step / article 5-step，详见 `docs/state-machine.md`）。
2. 环境分层：采用 `core + profile overlay` 架构，`.env` 是 core，`env/profiles/reader.env` 是 reader profile 模板；严格验收只认标准环境与标准镜像入口，reader overlay 只补缺失项，不覆盖当前进程里已显式注入的 reader 凭证。
3. 密钥策略：只允许通过 `.env` 或进程环境注入；禁止依赖 shell 登录配置作为密钥来源。
4. Python 命令统一使用 `python3`。
5. AI/自动化执行必须在标准环境：优先 `.devcontainer/devcontainer.json`，基础设施使用 `infra/compose/*.compose.yml`。

<!-- docs:generated governance-snapshot start -->
## Generated Governance Snapshot

- 文档高漂移事实已开始收口到 `docs/generated/*.md`；入口文档只保留 onboarding 必需信息。
- self-hosted CI 只接受 **trusted internal PR**；若 PR 来自 fork，GitHub Actions 会在边界门禁直接阻断。
- repo-side 严格验收入口：`./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`。
- external lane 入口：`./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`。
- external lane truth entry：`docs/generated/external-lane-snapshot.md`（tracked pointer）+ `.runtime-cache/reports/**`（current verdict）。
- 契约主层已迁到 `contracts/`，长期跟踪 artifact 已迁到 `artifacts/`。
<!-- docs:generated governance-snapshot end -->

## 环境文件准备（必做）

```bash
cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
```

说明：

- `.env.example` 现在只保留最小可启动键和少量高频覆盖键，默认足够完成一次本地启动。
- 标准初始化路径是 `.env.example -> .env`；`./bin/init-env-example` 仅作为辅助模板生成工具，不是默认入口。
- 脚本参数全集见 `docs/reference/env-script-overrides.md`（按需覆盖，不必全量写入 `.env`）。

## Public / Internal Boundary

- public-ready/source-first 入口：`README.md`、`docs/start-here.md`
- deeper operator runbook：`docs/runbook-local.md`
- repo-side / external 双层完成模型：`docs/reference/done-model.md`
- repo-side current receipt：`.runtime-cache/reports/governance/newcomer-result-proof.json`
- public readiness 边界：`docs/reference/public-repo-readiness.md`
- 当前文档口径是 **public source-first repo + dual completion lanes**，不是 adoption-grade 开源分发包，也不是 hosted product 发布页。

如果你只是第一次接触这个仓库，先停在 public-ready/source-first 入口，不要一上来把 `docs/runbook-local.md` 当成公共 onboarding 文档。

## 一键验证（最短路径）

```bash
./bin/validate-profile --profile local
```

如果这一步提示存在 forbidden workspace runtime residue，先执行：

```bash
./bin/workspace-hygiene --apply
./bin/validate-profile --profile local
```

补充判断：

- `validate-profile` 通过，只说明 newcomer preflight 已拿到。
- `governance-audit` 通过，只说明 repo-side 控制面站稳。
- 只有 fresh strict receipt 也拿到，repo-side 终局收据才算闭环。

## 初始化质量门禁（建议在首次 clone 后执行）

```bash
./bin/install-git-hooks
```

可选：如果你希望把 `pre-commit` framework 也直接挂到 Git 生命周期（除仓库默认 `.githooks` 外），执行：

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

说明：

- 仓库当前默认强制链路是 `.githooks/* -> bin/quality-gate`。
- `.pre-commit-config.yaml` 用于统一定义可复用检查集合，适合手动全量清洗与依赖更新。
- 若执行 `pre-commit install`，会写入当前 `core.hooksPath` 下的 hook 文件；执行前请确认团队约定。

## Big Bang 全量清洗（可选）

```bash
pre-commit run --all-files
```

用途：在大规模重构前、长期分支回收前，先把格式/拼写/基础静态问题一次性清干净。

## detect-secrets baseline（可选补充，与当前强制门禁并行）

当前仓库强制 secrets 门禁来自 `gitleaks + quality_gate`；`detect-secrets` 不是默认强制项。若你希望补充 baseline 工作流，可执行：

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

三步含义：

- 初始化：`scan > .secrets.baseline`
- 审核：`audit .secrets.baseline`（标记真实风险 vs 误报）
- 更新：`scan --baseline ... > .secrets.baseline`（代码变更后重算基线）

## pre-commit 月度保养（可选）

```bash
pre-commit autoupdate
pre-commit run --all-files
```

建议频率：每月一次；更新后至少跑一轮全量检查再提交。

可选排障命令：

```bash
./bin/compose-env --profile local --write .runtime-cache/tmp/.env.resolved
```

迁移规则：

- `.env`：放 core/runtime 与 provider 密钥。
- `env/profiles/reader.env`：只放 Miniflux/Nextflux 相关变量。

## 标准环境入口（AI 必须）

```bash
# VS Code: Dev Containers: Reopen in Container
# CLI:
devcontainer up --workspace-folder .
```

标准环境是强制前置；未先进入标准环境的结果，不算 CI 等价证据。

DevContainer 启动拓扑补充（2026-03）：

- `.devcontainer/post-create.sh` 已移除 `curl|sh` 安装模式，改为 `python3 -m pip install --user --upgrade "uv>=0.10,<1.0"`；当前会直接校验 strict contract 里的 Chromium 是否可启动，失败时直接报 drift，不再 `playwright install ... || true`。
- 并发 Web E2E 场景可通过 `WEB_E2E_NEXT_DIST_DIR` 隔离 Next.js `distDir`，避免 `.next/dev/lock` 冲突（默认常规开发无需设置）。
- `infra/config/strict_ci_contract.json` 现在是标准镜像真相源；`bin/strict-ci` / `./bin/run-in-standard-env` 只接受 digest-pinned 标准镜像，拉取失败会直接终止，不再静默回退到旧本地镜像。
- `build-ci-standard-image.yml` 现在会先显式准备 Docker Buildx，再调用 `scripts/ci/build_standard_image.sh` 做多架构标准镜像构建，避免 self-hosted runner 在构建入口阶段因为 buildx 环境未准备好而直接失败。
- 标准镜像构建链会对 NodeSource signing key 使用显式重试，并先落临时 key 文件再 `gpg --dearmor`；这是为了降低 ARM64/QEMU buildx 路径里“HTTP/2 中断导致空 key 响应”的瞬时失败率。
- 关键 correctness gates（`preflight-heavy`、`db-migration-smoke`、`dependency-vuln-scan`、`web-e2e-perceived`、后端/前端 lint hosted/fallback）已经跟 `python-tests` / `api-real-smoke` / `web-e2e` 一样迁入标准镜像执行，因此宿主 Docker 可用性现在是 CI 等价本地验收的前提。
- self-hosted runner 基线合同已独立成 `infra/config/self_hosted_runner_baseline.json`；主 `ci.yml` 不再预热/拉起 runner，runner 健康检查改由 `runner-health.yml` 负责。
- self-hosted runner 进入 `build-ci-standard-image.yml` 前会先用 `scripts/governance/runner_workspace_maintenance.sh` 清理 `.runtime-cache`、`mutants/` 与 `/tmp/video-digestor-*` 的目录/单文件残留，避免镜像工作流在 runner hygiene 阶段就被陈旧 `.db` / `.db-shm` / `.db-wal` 文件卡住。
- DevContainer 现在固定挂载到 `/workspace`，并通过 `post-create.sh` 校验 `uv` / `node` / cache 路径是否与 strict contract 一致。
- Web 依赖树统一进入 `.runtime-cache/tmp/web-runtime/workspace/apps/web`，不再把 `apps/web/node_modules` 作为仓库源码树中的合法长期状态。
- CI/release 生成式参考页：
  - `docs/generated/ci-topology.md`
  - `docs/generated/runner-baseline.md`
  - `docs/generated/release-evidence.md`

## 6 步启动（Host Fallback，仅排障时使用）

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.cache/video-digestor/project-venv" uv sync --frozen --extra dev --extra e2e
./bin/prepare-web-runtime

brew services start postgresql@16
brew services start redis
temporal server start-dev --ip 127.0.0.1 --port 7233

cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
set -a; source .env; set +a

createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql

./bin/dev-api
./bin/dev-worker
./bin/dev-mcp

curl -sS http://127.0.0.1:9000/healthz
curl -sS -X POST http://127.0.0.1:9000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 20}'
```

补充：`./bin/prepare-web-runtime` 是 wrapper，真正执行的是 `scripts/ci/prepare_web_runtime.sh`。如果入口报 `Permission denied`，先检查目标 helper 是否仍保留执行位。

## 一键路径（推荐）

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
```

默认行为：

- `./bin/bootstrap-full-stack` 会先运行 `./bin/workspace-hygiene --apply`，清掉根目录 `.venv`、源码树 `apps/web/node_modules`、以及 `apps/**/__pycache__` 这类非法运行态。
- `./bin/bootstrap-full-stack` 会拉起 core services + Miniflux + Nextflux。
- `./bin/bootstrap-full-stack` 除首次 `.env` 不存在时复制模板外，不再持久化改写 `.env`；端口冲突与运行时路由决策会写入 `.runtime-cache/run/full-stack/resolved.env`，仅对当前运行生效。
- `core-services.compose.yml` 现在使用 digest-pinned service 镜像（Postgres/Redis/Temporal），并优先接受 strict contract 导出的 `STRICT_CI_SERVICE_IMAGE_*` 值；端口与 Postgres `DB/User` 仍收口为固定默认（`6379` / `7233` / `video_analysis` / `postgres`）。
- `miniflux-nextflux.compose.yml` 的 Miniflux 端口与 `DB/User/DB_NAME` 已收口为固定默认（`8080` / `miniflux` / `miniflux`）。
- 本地路由真相源是 `API_PORT/WEB_PORT`；`VD_API_BASE_URL` 与 `NEXT_PUBLIC_API_BASE_URL` 属于派生目标地址。
- `./bin/full-stack up` 会按 `API health -> Web -> Worker` 顺序启动；Worker 启动前会先做 Temporal preflight（`TEMPORAL_TARGET_HOST`，默认 `localhost:7233`），不通时直接 fail-fast。
- `bin/dev-mcp` 为交互式 stdio 入口，不作为 `full_stack.sh` 的后台守护进程管理；需要 MCP 本地调试时单独开一个终端运行。
- `bin/dev-api` 在检测到 `uv` 时会调用 `uv run python -m uvicorn ...`，避免某些 self-hosted/隔离环境缺少 `uvicorn` console entry 时启动失败。
- `./bin/smoke-full-stack` 会执行本地联调烟测并覆盖 reader 栈检查；core/reader 任一异常都会直接 fail-fast，不再保留 offline fallback 降级路径。
- `./bin/smoke-full-stack` 不是 `api-real-smoke` 替代；后端真实 Postgres integration smoke 必须单独执行 `./bin/api-real-smoke-local`。
- `./bin/api-real-smoke-local` 现在会先做本机 IPv4 loopback 预检；若命中 `failure_kind=host_loopback_ipv4_exhausted`（常见于当前机器本地 127.0.0.1 临时端口池被大量 MCP/Codex 连接占满），脚本会直接 fail-fast，而不是继续启动 API/worker/Temporal 后才深处报错。
- 本地脚本排障时优先看 `.runtime-cache/logs/components/full-stack/*.log`、`.runtime-cache/run/full-stack/resolved.env` 与 `.runtime-cache/logs/tests/api-real-smoke-local.log`，这样能先区分“端口/路由漂移”还是“业务失败”。
- `pr-llm-real-smoke`、`live-smoke`、`web-e2e` 的日志统一看 `.runtime-cache/logs/tests/`；对应 diagnostics/JUnit 看 `.runtime-cache/reports/tests/`。

边界说明：

- 这里的一键 smoke 指本地联调烟测，不等同于 CI 的 live-smoke，也不能替代严格验收。
- 本地测试口径必须区分：sqlite 口径用于默认快速回归；真实 Postgres 口径用于 integration smoke 的最终验收。
- CI `live-smoke` 仅在 `main` push / nightly schedule 强制执行，且要求外部 provider secrets 完整（详见 `docs/testing.md`）。
- CI 信任边界：当前仓库默认只支持 **trusted internal PR** 进入 self-hosted 主链；fork / untrusted PR 不作为支持口径。
- PR 阶段仅有条件触发真实 LLM 烟测（`pr-llm-real-smoke`）；`web-e2e` 在 CI 主路径默认走 real API，mock API 仅用于本地调试。

标准严格验收（唯一权威入口）：

```bash
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

源码优先公开口径下的 repo-side 权威入口：

```bash
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

门禁口径补充：总覆盖率硬门禁 `>=95%`，Web `lines/functions/branches` 必须同时满足 `global >=95%` 且 `core >=95%`；`strict-full-run=1` 还会强制执行 mutation `score>=0.64 / effective_ratio>=0.27 / no_tests_ratio<=0.72`，并禁止 `ci-dedupe` 与 `skip-mutation`。本地 smoke 与 strict 验收统一采用 fail-fast，不再保留 offline fallback。

本地执行正式 pinned-image 严格验收时，必须满足以下其一：

- 已显式导出 `GHCR_USERNAME` + `GHCR_TOKEN`
- `gh auth` 当前登录态可用（仓库脚本会自动复用该身份）

`--debug-build` 只用于排障标准环境构建问题，不计入 CI 等价完成信号。

可选阅读栈（Miniflux + Nextflux）：

```bash
./bin/bootstrap-full-stack --with-reader-stack 1 --reader-env-file env/profiles/reader.env
```

## 下一步看哪里

- 本地运维与参数细节：`docs/runbook-local.md`
- 状态机与处理契约：`docs/state-machine.md`
- 环境变量契约：`ENVIRONMENT.md`
- 协作与文档漂移规则：`AGENTS.md`
- 全文档索引：`docs/index.md`
