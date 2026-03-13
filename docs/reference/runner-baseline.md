# Self-Hosted Runner Baseline

本文件定义 self-hosted runner 的最小基线合同。目标不是在 workflow 里“缺什么装什么”，而是让 runner 先满足固定前提，再执行仓库 CI。

## 真相源

- 合同文件：`infra/config/self_hosted_runner_baseline.json`
- 检查脚本：`scripts/check_runner_baseline.py`
- 调用位置：
  - `.github/workflows/_preflight-fast-steps.yml` 使用 `--profile preflight-fast`
  - `.github/workflows/runner-health.yml` 使用 `--profile runner-health`

## 当前 profile

### `preflight-fast`

必须存在：

- `bash`
- `python3`
- `git`
- `docker`
- `rg`
- `docker compose`

### `runner-health`

必须存在：

- `bash`
- `python3`
- `git`
- `docker`
- `gh`
- `gcloud`
- `jq`
- `rg`

## 治理原则

- workflow 不再通过 `apt-get install` 补齐 runner 缺失工具。
- runner 缺少合同要求的工具时，直接在 preflight 或 runner-health 失败。
- `runner-health.yml` 负责 runner 控制面健康检查；主 `ci.yml` 不再承担 runner 运维职责。
