# Dependency Governance

## Dependency Sources of Truth

### Python

- 清单：`pyproject.toml`
- 锁文件：`uv.lock`
- 安装命令：`uv sync --frozen --extra dev --extra e2e`
- 测试重试基线：默认 `pytest reruns=0`（仅在专门 flaky/nightly 任务中显式开启重试）
- 测试标记治理：`pyproject.toml` 统一声明 `allow_unauth_write` marker，用于显式标注需要写入白名单的测试。

### Web (Node)

- 清单：`apps/web/package.json`
- 锁文件：`apps/web/package-lock.json`
- 安装命令：`npm --prefix apps/web ci`
- 覆盖率运行依赖：`@vitest/coverage-v8`（`vitest run --coverage` 必需）

## CI Gates

- `ci.yml`：
  - `uv sync --frozen`（锁文件强约束）
  - `bash scripts/guard_provider_residuals.sh .`（Provider 残留防回归）
  - migration smoke
  - python tests
  - web lint/build/e2e
  - web a11y smoke（`npm --prefix apps/web run test:a11y`）
- `env-governance.yml`：
  - `python scripts/check_env_contract.py --strict`
  - `gitleaks detect --source . --verbose --redact`
- `mutation-weekly.yml`：
  - 使用 `pyproject.toml` 的 `[tool.mutmut]` 作为唯一配置源
  - 默认阈值 `--mutation-min-score 0.85`
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
npm --prefix apps/web ci
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run test:a11y
npm --prefix apps/web run build
```

## Constraints

- 禁止提交与清单不一致的锁文件。
- 禁止绕过 `--frozen` 流程在 CI 中安装 Python 依赖。
- 禁止在 CI 中使用“临时 mutmut 参数”覆盖 `pyproject.toml` 的核心范围配置。
- 使用 `allow_unauth_write` marker 的测试必须显式启用开关环境变量：`VD_ALLOW_UNAUTH_WRITE=true`（必要时在 CI 额外设置 `VD_CI_ALLOW_UNAUTH_WRITE=true`）。
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
  - `apps/worker/worker` + `apps/worker/tests`
  - `apps/api/app` + `apps/api/tests`
- 测试选择清单（`pytest_add_cli_args_test_selection`）必须与突变范围同步演进：
  - 新增核心模块时，同步补充目标测试文件，避免“有突变、无断言杀伤”。
- 强制守卫：
  - `python3 scripts/check_mutation_scope.py` 会在 pre-commit/pre-push/CI preflight 运行，防止范围缩水。
  - `python3 scripts/check_mutation_test_selection.py` 会在 pre-commit/pre-push/CI preflight 运行，防止测试选择清单缩水。
  - `quality_gate.sh` 对 mutmut 结果执行三维门禁：`score>=0.62`、`effective_ratio>=0.25`、`no_tests_ratio<=0.75`（CI 参数可显式覆盖）。

## Doc-Drift Enforcement

- Pre-commit / pre-push 会校验依赖治理文档联动：
  - 触发文件：`pyproject.toml`、`uv.lock`、`requirements*.txt`、`requirements/*.txt`、
    `apps/*/package.json`、`apps/*/package-lock.json`、`apps/*/pnpm-lock.yaml`
  - 必须同步更新：`docs/reference/dependency-governance.md`
- 校验脚本：`scripts/ci_or_local_gate_doc_drift.sh`

## Suggested Security Checks

```bash
python scripts/check_env_contract.py --strict
gitleaks detect --source . --verbose --redact
npm --prefix apps/web audit --omit=dev
```
