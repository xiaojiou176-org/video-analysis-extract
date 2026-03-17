# Done Model

本仓库的完成信号分成两层，不能混用。

## Layer A: Repo-side Done

这层先讲人话，就是“代码库自己能不能站稳”。它不要求外部平台、镜像仓库或 provider 平台也同步完美，只要求仓库内的控制面、源码树、文档、测试与本地标准环境形成可信闭环。

| 维度 | Repo-side Done 标准 |
| --- | --- |
| Root / source hygiene | 根目录通过 allowlist；repo-owned source roots 没有 `__pycache__` / `*.pyc` / runtime residue |
| Governance | `./bin/governance-audit --mode audit` fresh 通过，且 canonical current-proof artifact 的 `source_commit` 与当前 HEAD 对齐；这只是 repo-side done 的必要条件，不单独构成 repo-side done |
| Docs truth | generated docs 新鲜且关键语义与 control plane 一致 |
| Strict path | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 对当前 HEAD 拿到 fresh PASS 收据；repo-side done 需要这张 strict receipt，而不是只要求命令存在或曾经启动过 |
| Compat | `upstream-compat-matrix` 中 repo-side required rows 达到期望状态 |
| Public/source-first onboarding | 源码优先入口可解释、可执行、可区分 public docs 与 internal runbook |
| Public governance pack | `README.md`、`SECURITY.md`、`SUPPORT.md`、`.github/CODEOWNERS`、`docs/reference/public-repo-readiness.md` 与 `docs/reference/public-artifact-exposure.md` 不含 placeholder routing，且 public-safe surface、policy allowlist 与 tracked 文件一致 |

补充硬规则：

- `governance-audit` fresh PASS 不等于 repo-side done；它只证明控制面和制度面站稳了。
- repo-side done 必须同时满足：governance PASS + strict current receipt + docs truth + current-proof 对齐。
- 若 `newcomer-result-proof.json` 里 `repo_side_strict_receipt=status=missing_current_receipt`，则当前 HEAD 还不能宣称 repo-side done。

## Layer B: External Done

这层先讲人话，就是“外部世界也能证明你说的话”。它包括 GHCR pinned image、provider 真实链路、public release 资产、远端 workflow 等。

| 维度 | External Done 标准 |
| --- | --- |
| Image distribution | GHCR pinned image 可拉取、可证明，而且 external lane 只有 `verified` 才能计入 External Done |
| Public release | Release bundle / attestation / public distribution 文案一致 |
| Provider verification | provider/live rows 有 fresh same-run proof |
| Remote platform | 远端 workflow 与平台配置能复现外部闭环 |

补充硬规则：

- remote workflow 就算成功，只要 `headSha` 不是当前 HEAD，也只能算历史证据，不能计入 External Done
- `ready` / `queued` / `in_progress` 只代表“外层前置条件或执行过程存在”，不代表 external closure

## Not In Scope For Repo-side Completion

- GHCR 发布权限问题
- 外部 provider 配额与平台账号状态
- 未公开的私有部署拓扑
- 不在当前 source-first 公开形态中的镜像优先交付

## Canonical Commands

Repo-side canonical commands:

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

External lane commands:

```bash
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
./bin/upstream-verify
```

External lane state tracking:

- `docs/reference/external-lane-status.md`
- `docs/reference/newcomer-result-proof.md`
- `docs/generated/external-lane-snapshot.md` 现在只是 tracked pointer / reading rule
- `.runtime-cache/reports/governance/current-state-summary.md` 是 runtime-owned 当前状态汇总
- `.runtime-cache/reports/governance/newcomer-result-proof.json` 是 repo-side newcomer / strict 收据入口
- current-state 文档和 runtime reports 只能消费 current-commit-aligned canonical artifacts；历史 examples 只能当 examples，不能冒充 current verdict
