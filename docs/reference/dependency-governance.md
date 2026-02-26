# Dependency Governance

## Dependency Sources of Truth

### Python

- 清单：`pyproject.toml`
- 锁文件：`uv.lock`
- 安装命令：`uv sync --frozen --extra dev --extra e2e`

### Web (Node)

- 清单：`apps/web/package.json`
- 锁文件：`apps/web/package-lock.json`
- 安装命令：`npm --prefix apps/web ci`

## CI Gates

- `ci.yml`：
  - `uv sync --frozen`（锁文件强约束）
  - `bash scripts/guard_provider_residuals.sh .`（Provider 残留防回归）
  - migration smoke
  - python tests
  - web lint/build/e2e
- `env-governance.yml`：
  - `python scripts/check_env_contract.py --strict`
  - `gitleaks detect --source . --verbose --redact`

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
npm --prefix apps/web run build
```

## Constraints

- 禁止提交与清单不一致的锁文件。
- 禁止绕过 `--frozen` 流程在 CI 中安装 Python 依赖。
- 依赖升级若影响运行命令或环境变量，必须同步更新：
  - `README.md`
  - `docs/runbook-local.md`
  - `ENVIRONMENT.md`（如涉及 env）

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
