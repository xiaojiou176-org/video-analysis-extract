# Dependency Governance

## Dependency Sources of Truth

### Python

- 清单：`pyproject.toml`
- 锁文件：`uv.lock`
- 安装命令：`uv sync --frozen --extra dev --extra e2e`
- 测试重试基线：默认 `pytest reruns=0`（仅在专门 flaky/nightly 任务中显式开启重试）
- 测试标记治理：`pyproject.toml` 统一声明 `allow_unauth_write` marker，用于显式标注需要写入白名单的测试。
- 安全关键传递依赖若命中阻断级漏洞，允许在 `pyproject.toml` 中显式加直接约束钉住安全版本；当前示例：`pyjwt[crypto]>=2.12.0,<3` 用于覆盖上游传递依赖中的已知 CVE。

### Web (Node)

- 清单：`apps/web/package.json`
- 锁文件：`apps/web/package-lock.json`
- 安装命令：`bash scripts/ci/prepare_web_runtime.sh`
- 覆盖率运行依赖：`@vitest/coverage-v8`（`vitest run --coverage` 必需）
- UI 基座依赖：当前 Web shell 使用 `tailwindcss@4` + `@tailwindcss/postcss` + `radix-ui` + `next-themes` + `geist`；
  若继续扩展 UI primitives，优先复用现有 shadcn/radix 风格组件，不要并行引入第二套组件体系。

## CI Gates

- `ci.yml`：
  - `uv sync --frozen`（锁文件强约束）
  - `bash scripts/governance/guard_provider_residuals.sh .`（Provider 残留防回归）
  - migration smoke
  - python tests
  - web lint/build/e2e
  - web a11y smoke（`npm --prefix apps/web run test:a11y`）
  - runner 策略：所有 CI Job 必须运行在当前仓库专用 self-hosted runner 池（`[self-hosted, video-analysis-extract]`），避免被组织内其他仓库挤占
- `governance_gate.sh`：
  - `python3 scripts/governance/check_root_allowlist.py --strict-local-private`
  - `python3 scripts/governance/check_root_semantic_cleanliness.py`
  - `python3 scripts/governance/check_root_layout_budget.py`
  - `python3 scripts/governance/check_root_zero_unknowns.py`
  - `python3 scripts/governance/check_runtime_outputs.py`
  - `python3 scripts/governance/check_runtime_cache_retention.py`
  - `python3 scripts/governance/check_runtime_cache_freshness.py`
  - `python3 scripts/governance/check_governance_language.py`
  - `python3 scripts/governance/check_dependency_boundaries.py`
  - `python3 scripts/governance/check_module_ownership.py`
  - `python3 scripts/governance/check_contract_locality.py`
  - `python3 scripts/governance/check_no_cross_app_implementation_imports.py`
  - `python3 scripts/governance/check_logging_contract.py`
  - `python3 scripts/governance/check_log_correlation_completeness.py`
  - `python3 scripts/governance/check_log_retention.py`
  - `python3 scripts/governance/check_no_unindexed_evidence.py`
  - `python3 scripts/governance/check_contract_surfaces.py`
  - `python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py`
  - `python3 scripts/governance/check_upstream_governance.py`
  - `python3 scripts/governance/check_unregistered_upstream_usage.py`
  - `python3 scripts/governance/check_upstream_compat_freshness.py`
  - `python3 scripts/governance/check_active_upstream_evidence_fresh.py`
  - `python3 scripts/governance/check_upstream_failure_classification.py`
- `env-governance.yml`：
  - `python scripts/governance/check_env_contract.py --strict`
  - `gitleaks detect --source . --verbose --redact`
- `mutation-weekly.yml`：
  - 使用 `pyproject.toml` 的 `[tool.mutmut]` 作为唯一配置源
  - 默认阈值 `--mutation-min-score 0.64`
  - 周期审计要求 `survived=0`（无存活突变体）

## Upgrade Workflow

### Python 依赖升级

1. 修改 `pyproject.toml`
2. 生成新锁：`uv lock`
3. 安装验证：`uv sync --frozen --extra dev --extra e2e`
4. 回归测试：`uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q`

### Web 依赖升级

1. 修改 `apps/web/package.json`
2. 重新锁定：`npm --prefix apps/web install`
3. 校验：

```bash
bash scripts/ci/prepare_web_runtime.sh
eval "$(bash scripts/ci/prepare_web_runtime.sh --shell-exports)"
npm --prefix "$WEB_RUNTIME_WEB_DIR" run lint
npm --prefix "$WEB_RUNTIME_WEB_DIR" run test
npm --prefix "$WEB_RUNTIME_WEB_DIR" run test:a11y
npm --prefix "$WEB_RUNTIME_WEB_DIR" run build
```

当前本地推荐口径补充：

- Web 覆盖率统一使用 runtime workspace 中的 `npm run test:coverage`，不再把 `apps/web/node_modules` 当作仓库内长期默认依赖面。
- 若依赖升级影响到本地严格验收链路，还必须验证：

```bash
./scripts/ci/api_real_smoke_local.sh
./bin/quality-gate --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

## Constraints

- 禁止提交与清单不一致的锁文件。
- 禁止新增未登记顶级项、未登记外部上游、未登记 repo-side 运行时输出路径。
- 禁止绕过 `--frozen` 流程在 CI 中安装 Python 依赖。
- 禁止在 CI 中使用“临时 mutmut 参数”覆盖 `pyproject.toml` 的核心范围配置。
- 使用 `allow_unauth_write` marker 的测试必须显式启用开关环境变量：`VD_ALLOW_UNAUTH_WRITE=true`，且仅允许在 `pytest` 上下文中生效；CI smoke/发布路径不得再依赖 `VD_CI_ALLOW_UNAUTH_WRITE` 旁路。
- 依赖边界以 `config/governance/dependency-boundaries.json` 为真相源；共享 packages 不得反向依赖 `apps/*`。
- 外部系统 inventory 与兼容矩阵以 `config/governance/active-upstreams.json`、`config/governance/upstream-templates.json`、`config/governance/upstream-compat-matrix.json` 为真相源。
- 上游分层注册表以 `config/governance/upstream-registry.json` 为真相源；`template` 不计入现役成熟度。
- future vendor/fork/patch 一旦现役，必须同步通过 `python3 scripts/governance/check_vendor_registry_integrity.py`。
- 依赖升级若影响运行命令或环境变量，必须同步更新：
  - `README.md`
  - `docs/runbook-local.md`
  - `ENVIRONMENT.md`（如涉及 env）

## Mutation Scope Governance

- 突变测试范围以核心业务路径为主，不追求全仓库蛮力扫描，优先覆盖“缺陷逃逸高风险”模块：
  - `apps/worker/worker/pipeline/*`（编排/策略/执行）
  - `apps/worker/worker/state/sqlite_store.py`（并发锁与状态持久化）
  - `apps/api/app/services/*`（服务层核心逻辑）
  - `apps/api/app/routers/*`（接口分发与契约路径）
- `paths_to_mutate` 当前最小治理要求：
  - 核心必含 `orchestrator/policies/runner/types/step_executor/sqlite_store`
  - API 必含 `ingest/jobs/subscriptions/videos` 的 `service + router`
  - 总目标数不得低于 `16`
- `also_copy` 必须同时包含被测代码与对应测试目录，确保 mutmut 在隔离沙箱内可复现实测路径：
  - `integrations/`（当核心路径已迁入 integration layer 时，mutation 沙箱必须同步带上外部转接层）
  - `apps/worker/worker` + `apps/worker/tests`
  - `apps/api/app` + `apps/api/tests`
- 测试选择清单（`pytest_add_cli_args_test_selection`）必须与突变范围同步演进：
  - 新增核心模块时，同步补充目标测试文件，避免“有突变、无断言杀伤”。
- 强制守卫：
  - `python3 scripts/governance/check_mutation_scope.py` 会在 pre-commit/pre-push/CI preflight 运行，防止范围缩水。
  - `python3 scripts/governance/check_mutation_test_selection.py` 会在 pre-commit/pre-push/CI preflight 运行，防止测试选择清单缩水。
  - `quality_gate.sh` 对 mutmut 结果执行三维门禁：`score>=0.64`、`effective_ratio>=0.27`、`no_tests_ratio<=0.72`（CI 参数可显式覆盖）。

## Doc-Drift Enforcement

- Pre-commit / pre-push 会校验依赖治理文档联动：
  - 触发文件：`pyproject.toml`、`uv.lock`、`requirements*.txt`、`requirements/*.txt`、
    `apps/*/package.json`、`apps/*/package-lock.json`、`apps/*/pnpm-lock.yaml`
  - 必须同步更新：`docs/reference/dependency-governance.md`
- 校验脚本：`scripts/governance/ci_or_local_gate_doc_drift.sh`

## Suggested Security Checks

```bash
python scripts/governance/check_env_contract.py --strict
gitleaks detect --source . --verbose --redact
npm --prefix apps/web audit --omit=dev
```


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->
