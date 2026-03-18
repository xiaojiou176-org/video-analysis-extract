# Newcomer Clean-Room Receipt

这份文档不是 onboarding 摘要，而是一张**执行收据**。你可以先把它理解成“在 integrator 验收阶段，针对下方注明的那次 fresh 运行，官方入口实际跑了哪一步，以及没跑哪一步”的小票。

当前口径必须保持诚实：

- 本仓库对外是 **public source-first + limited-maintenance**，不是“一键可商用产品”。
- 这张收据只证明 **最小可试路径** 在下方记录的那次运行里拿到了 fresh 票据，不证明 full-stack/operator 路径已经 fresh 跑通。
- 更重的 repo-side strict / external lane 仍要看独立收据，不能拿这张票据冒充。

## 本次收据证明了什么

- **已 fresh 证明**：`docs/start-here.md` 中标注的 newcomer 最短路径 `./bin/validate-profile --profile local` 在下方记录的 source commit 上可以执行并产出收据。
- **未 fresh 证明**：`./bin/full-stack up`、`./bin/smoke-full-stack`、`./bin/api-real-smoke-local`、`./bin/repo-side-strict-ci ...`、`./bin/strict-ci ...`。

换句话说，这次像是先确认“钥匙和门牌号对得上”，还**没有**证明“整套厨房、水电、排烟都已经点火运行”。

## 真相源

- 官方 newcomer 入口：`docs/start-here.md`
- operator runbook：`docs/runbook-local.md`
- public/source-first 边界：`docs/reference/public-repo-readiness.md`
- 最短路径入口脚本：`bin/validate-profile`
- 实际执行脚本：`scripts/env/validate_profile.sh`
- 机器可读状态页：`docs/reference/newcomer-result-proof.md`

## Fresh Run Stamp

这部分记录的是**收据来源**，不是“仓库未来所有 commit 的永恒当前态”。当前 live 读数仍应以 `docs/reference/newcomer-result-proof.md` 指向的 runtime report 为准。

| 字段 | 值 |
| --- | --- |
| 日期 | 2026-03-16 America/Los_Angeles |
| 近似时间 | 22:59 PDT |
| commit | `c7ddaed526671b927396063f2812978b9a739a15` |
| 命令 | `./bin/validate-profile --profile local` |
| 退出码 | `0` |
| 耗时 | `0.42s` |

## 环境前提

这条 newcomer 最短路径的门槛比 full-stack 低，实际观察到的前提如下：

- 需要仓库内置的 `env/core.env.example`
- 需要 `env/profiles/local.env`
- 需要 `python3` 与仓库脚本运行能力
- **本次运行时 `.env` 缺失**，但该命令仍然通过；脚本把这件事标成 `risk hint`，没有假装当前机器已经具备完整运行态
- 这条路径**不要求**当前先启动 Docker、Postgres、Temporal，也不证明这些依赖已经可用

## 精确命令

```bash
./bin/validate-profile --profile local
python3 scripts/governance/render_newcomer_result_proof.py
```

第二条命令不是 newcomer 官方入口本身，而是把本轮 fresh 结果渲染成机器可读状态包，方便 integrator 后续挂载。

## 实际产物

### 1. resolved env 快照

路径：

- `.runtime-cache/tmp/.env.local.resolved`

本轮实际内容摘要：

```dotenv
ENV_PROFILE=local
```

解释：

- 这说明 profile 组合至少成功落地成了一份 resolved env 文件。
- 但当前只解析出了 **1 个键**，所以它更像“profile 组合成功”的证明，而不是“应用运行配置已经齐全”的证明。

### 2. 运行 manifest

路径：

- `.runtime-cache/run/manifests/20d2fb35724d4aa89de9f46b04012bff.json`

关键字段摘要：

- `entrypoint=validate-profile`
- `channel=governance`
- `run_id=20d2fb35724d4aa89de9f46b04012bff`
- `argv=["--profile","local"]`
- `repo_commit=c7ddaed526671b927396063f2812978b9a739a15`
- `log_path=.runtime-cache/logs/governance/20d2fb35724d4aa89de9f46b04012bff.jsonl`

### 3. newcomer result proof JSON

路径：

- `.runtime-cache/reports/governance/newcomer-result-proof.json`

本轮 fresh 读数摘要：

- `newcomer_preflight=status=pass`
- `repo_side_strict_receipt=status=missing_current_receipt`
- `governance_audit_receipt=status=missing`

这三个状态合起来的意思是：

- **最小可试路径**已经 freshly proved
- **更重的 repo-side strict 收据**当前 commit 还没有 fresh PASS 收据
- **governance audit 收据**这次也没有一并 fresh 捕获

## 本轮观察到的失败点 / 限制

### 已实际观察到的限制

- `validate-profile` 输出了 `risk hint: .env is missing; validation passed with available files only.`
- 也就是说，这条路径不会替你证明 `.env` 已经准备好，更不会替你证明 API/Worker/Web/Reader 能启动

### 该路径的脚本级 fail-fast 点

来自 `scripts/env/validate_profile.sh` 的实际逻辑，这条 newcomer 路径在以下情况会直接失败：

- `env/profiles/<profile>.env` 缺失
- `compose_env.sh` 组合 env 失败
- resolved env 文件为空
- 发现不到任何可用 env 文件

## 与完整 full-stack 路径的区别

这部分特别容易被误解，所以单独写清楚。

### 最小可试路径

命令：

```bash
./bin/validate-profile --profile local
```

它证明的是：

- newcomer 入口没有写成死文档
- local profile 至少还能被脚本组合出来
- 当前 HEAD 至少有一条低门槛入口是 fresh 的

它**不**证明的是：

- `.env` 已存在且完整
- Docker / DevContainer 可用
- Postgres / Temporal 可用
- API/Worker/Web 能启动
- smoke / real smoke / strict-ci 已 fresh 通过

### 完整 operator / full-stack 路径

参考命令：

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
./bin/api-real-smoke-local
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

这些才是在“真正做饭上桌”的那条路上。它们需要更高 operator 门槛，也更依赖标准环境、基础设施和外部条件。

## Operator 门槛说明

如果你是第一次接触这个仓库，最安全的理解方式是：

- 这不是轻量玩具项目，不要把它当成“clone 后三秒一键开箱 app”
- newcomer 最短路径是**配置与入口真伪检查**
- full-stack/operator 路径才是**运行与验收链**
- 严格验收还要区分 `repo-side` 和 `external lane`，两条都不是这张收据当前证明的内容

## Reviewer 判断标准

如果 reviewer 想判断这页是不是“抄文档”，可以看这几个点：

- 文中给出了 **当前 commit**
- 给出了 **fresh 命令**
- 给出了 **退出码和耗时**
- 给出了 **实际运行产物路径**
- 明确写出 **`.env` 缺失但命令仍通过** 这一限制
- 明确区分了 **最小可试路径** 和 **完整 full-stack 路径**
- 没有把缺失的 strict / governance receipt 包装成通过
