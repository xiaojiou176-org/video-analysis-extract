# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-18 23:11:47 America/Los_Angeles`
- Last Updated: `2026-03-19 01:21:00 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `In Progress`
- Authoritative Plan: `this file is the only execution source of truth for the current run`
- Current Phase: `Phase-4 local-capability closure completed; current-head WS2 remote proof attempted and narrowed`
- Current Workstream: `WS2`
- Current Workspace Note: `all repo-side and provider-side tasks that are executable from this machine have now been re-proven; the remaining local fail-close condition is the dirty worktree created by this run's verified tracked patch set plus the validated diff in apps/worker/tests/test_external_proof_semantics.py`

## [一] 3 分钟人话版

这个仓库现在最真实的状态，不是“还很乱”，也不是“已经完美”，而是：

- **repo-side 控制面已经很强**
- **external 分发链还没闭环**
- **current proof 的最后一张重收据已经补齐，但当前工作区仍因 dirty worktree fail-close 到 `partial`**

你可以把它理解成一家已经把后厨、仓库、值班表、消防通道都搭好的餐厅：

- 后厨很强：`governance-audit`、root allowlist、runtime output contract、docs control plane、upstream inventory 都已经接线。
- 前台也不差：`README.md`、`SECURITY.md`、`CONTRIBUTING.md`、`THIRD_PARTY_NOTICES.md`、`remote-platform-truth.json` 都在。
- 但最关键的两件事还没闭环：
  1. **当前 HEAD 的 repo-side strict PASS 收据已经拿到**，但 `newcomer-result-proof.json` 和 `current-state-summary.md` 仍然只能诚实地给出 `partial`，因为工作区还没干净到可以把 current verdict 升成 `pass`。
  2. **GHCR standard image external lane 仍然 blocked**，所以 external/public distribution 不能被诚实宣称为已闭环。

为什么不能继续靠表面成熟度自我感觉良好？

- 因为 **“规章齐全” 不等于 “本轮考试已经完全交卷”**。现在 `governance-audit PASS` 和 strict receipt 都在，但 dirty worktree 仍让 current workspace verdict fail-close。
- 因为 **“有发布流水线” 不等于 “已经能发布”**。SBOM、attestation、workflow 存在，不等于 GHCR 写权限已经打通。
- 因为 **“仓库 public” 不等于 “全球开发者能顺滑接手”**。深水区中文仍留在治理脚本、运行时文案和部分源码里。

改完以后，仓库应变成：

- **repo-side done 与 external done 分层极清楚**
- **current-state 只能 fail-close，不再让旧票据冒充 current truth**
- **GHCR / external image lane 有 current-head verified 证据**
- **深水区 contributor-facing / runtime-facing surface 英文化，降低全球协作门槛**

哪些旧东西必须被硬切：

- 任何把 `governance-audit PASS` 说成 repo-side done 的说法
- 任何把 `remote-required-checks=pass` 说成 terminal closure 的说法
- 任何把 old-head remote workflow 说成 current external verification 的说法
- 任何继续把中文留在治理脚本、错误语义、CI/运行时诊断面的做法

为什么必须这么硬：

- 不硬切，未来 agent 还会被“强治理外观”误导。
- 不硬切，repo 会长期停在“看起来像 Final Form，实际上还差最后两张收据”的状态。
- 不硬切，repo 会长期停在“局部都很强，但当前工作区判词和远端分发判词都还不够诚实”的状态。
- 不硬切，开源 readiness、外部分发、招聘信号都会被混成一锅。

## [二] Plan Intake

### 输入材料范围

- 上游 `超级Review` 审计报告
- 上游 `## [十三] 机器可读问题账本` YAML
- 当前 repo fresh 验证结果
- 当前 repo tracked docs / runtime reports / workflows / governance control plane
- `.agents/Plans/` 下历史 Plan

### 验证范围

- repo structure
- configs
- workflows
- scripts
- docs
- tests
- outputs
- integration surfaces

### 置信边界

- **高置信**
  - `git status --short --branch` 显示 clean，`HEAD == origin/main == e13b047e2686943481aeec5d25e5025b7083c77e`
  - `python3 scripts/governance/check_current_proof_commit_alignment.py` PASS
  - `python3 scripts/governance/check_newcomer_result_proof.py` PASS
  - `newcomer-result-proof.json` 当前仍是 `partial`
  - `current-state-summary.md` 当前仍是 `partial`
  - fail-close blocker 是 `repo_side_strict_missing_current_receipt`
  - `.runtime-cache/run/manifests/` 下当前 commit 没有 `strict-ci` manifest
  - `ghcr-standard-image` 当前仍是 `blocked/registry-auth-failure`
  - `release-evidence-attestation` 当前是 `ready`，但 remote workflow 仍是 old head historical
- **中置信**
  - 当前 HEAD 跑 `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 是否会直接通过，还是会撞到新的 deeper gate
  - GitHub 平台侧 `allowed_actions=all` / `sha_pinning_required=false` 是否完全可由本仓单独落地
- **低置信**
  - provider/live lane 在执行当刻的外部额度与账号状态

### Repo archetype

- `hybrid-repo`

### 当前最真实定位

- `public source-first`
- `limited-maintenance`
- `repo-side strong`
- `external distribution not closed`
- `strong governance repo, not adoption-grade public delivery system yet`

### 最危险误判

- 把 `governance-audit PASS + current-proof alignment PASS + public repo + generated docs` 误判成“整个仓库已经 Final Form”

### 结构化输入已就位

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
    - 当前 Repo fresh gate 结果
    - 当前 Repo tracked docs / runtime reports / workflows / governance control plane
  </input_material_types>
  <validation_scope>
    - repo structure
    - configs
    - workflows
    - scripts
    - docs
    - tests
    - outputs
    - integration surfaces
  </validation_scope>
  <initial_claims>
    - repo-side 控制面很强
    - 当前 repo-side done 仍未被 strict current receipt 证明
    - external GHCR lane 仍是唯一主外部 blocker
    - 开源基础包已成立，但全球协作边界仍未清到位
  </initial_claims>
  <known_conflicts>
    - 旧计划中“only external GHCR remains”这句话已被当前 newcomer/current-state 票据推翻；repo-side strict receipt 仍缺
    - 旧 dirty-worktree 叙事已过时；当前 live worktree 是 clean
    - 当前 current-state-summary 已正确 fail-close，不应再把“summary stale seam”当主 blocker
  </known_conflicts>
  <confidence_boundary>
    - strict receipt 缺失、GHCR blocker、deep-water English boundary 为高置信
    - 平台策略收紧和 current strict pass 的具体修复量需在执行期二次验证
  </confidence_boundary>
</plan_intake>
```

### 统一问题账本

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | 当前 HEAD 缺少 repo-side strict fresh PASS receipt | 上游 YAML + 当前 runtime reports + fresh manifest scan | 已验证 | A | fact | blocker | 直接阻断 repo-side done 结论 | 当前 commit 下未产生 `strict-ci` manifest / PASS receipt | 采纳 |
| `ISS-002` | GHCR standard image external lane blocked | 上游 YAML + `.runtime-cache/reports/governance/standard-image-publish-readiness.json` + current summary | 已验证 | A | fact | blocker | 直接阻断 external/public distribution 闭环 | registry auth / packages write 未闭环 | 采纳 |
| `ISS-003` | 深水区中文残留仍阻断全球协作 | 上游 YAML + fresh `rg` 命中 | 已验证 | A | fact | structural | 伤开源 readiness、全球贡献与排障搜索 | 中文仍存在于治理脚本、运行时文案、部分源码/模板 | 采纳 |
| `ISS-004` | current-state fail-close seam 是当前主问题 | 上游 YAML | 被部分推翻 | A | fact | important | 若误保留会让主路线失焦 | current-state-summary 当前已经正确 fail-close | 不作为主 workstream，降级为守护项 |
| `ISS-005` | docs / CI 控制面成熟，仍可继续强化 | 上游 YAML + fresh docs/CI checks | 已验证 | B | fact | important | 决定路线要“补最重票据”，不是“大修控制面” | docs/CI 已强，不再是主战场 | 采纳，作为支撑项 |
| `ISS-006` | release-evidence-attestation 已 external verified | 上游散文旧说法 | 被推翻 / 已过时 | A | fact | unknown | 会夸大 external maturity | 当前只有 readiness `ready`，remote workflow 仍是 old-head historical | 不采纳 |
| `ISS-007` | remote-integrity 未进入主链 required lane | 历史计划旧说法 | 过时 | A | fact | unknown | 会误导路线 | 当前 `remote-required-checks` 已 pass，expected=18 actual=18 | 不采纳 |
| `ILL-001` | `governance-audit PASS` 被误读成 repo-side done | 上游幻觉账本 + current newcomer proof | 已验证 | A | risk | structural | 制造“控制面绿=整个 repo 绿”幻觉 | 轻 gate 与重 receipt 被混读 | 采纳 |
| `ILL-002` | `remote-required-checks=pass` 被误读成 terminal closure | 上游幻觉账本 + current-state summary | 已验证 | A | risk | structural | 夸大 external/CI 成熟度 | required-check integrity 与 terminal closure 被混读 | 采纳 |
| `ILL-003` | `public repo + LICENSE + SECURITY pack` 被误读成 adoption-grade 开源 | 上游幻觉账本 + public docs + Chinese residue scan | 已验证 | A | risk | structural | 夸大开源 readiness | legal/public 包齐全不等于全球协作友好 + external distribution 闭环 | 采纳 |

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 / 含金量 | 强工程项目，owner-level 候选 | 保持 source-first 强项目定位，消除“已经全部闭环”的误读 | A | 是 | 不再做漂亮化叙事工作 |
| 开源边界 / public surface | 可安全公开源码，公共治理包齐 | 让 global contributor surface 和 external distribution 也说得过去 | A | 是 | 当前不是 license 缺失问题 |
| 文档事实源 | control plane + generated + runtime reports 已分层 | 保持 fail-close，不再回到“tracked docs 承载 current state” | A | 是 | 当前已基本成立 |
| CI 主链与 Gate 可信度 | 强 | 保持强，避免 required checks 被误读 | A | 是 | 当前不是 mega-job 问题 |
| 架构治理 | 强 | 不做无关重构，只补真实 blocker | A | 是 | hybrid 边界清楚 |
| 缓存治理 | 强 | 继续守住单出口与可重建原则 | A | 是 | 当前非主 blocker |
| 日志治理 | 中强 | 保持 schema/correlation，并减少 contributor-facing 中文 | B | 是 | 当前非第一波动作 |
| 根目录洁净 | 强 | 冻结新增顶级项，防回潮 | A | 是 | 当前健康 |
| 外部依赖治理 | inventory/matrix 强 | pending row 继续向 verified 收口 | A | 是 | 主要受 GHCR lane 牵引 |
| 总成熟度 | 强，但仍半闭环 | repo-side done 与 external done 都拿到 current-head 重收据 | A | 是 | 关键在两张票据 |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `R1` repo-side strict current receipt 缺失 | governance-audit PASS、worktree clean、current-proof alignment pass | 没有当前 commit 的 strict entry manifest / PASS receipt，所以 repo-side done 还不能成立 | `WS1` | `newcomer-result-proof` + `current-state-summary` + strict manifest presence |
| `R2` external GHCR lane blocked | build-ci-standard-image workflow 在、SBOM/attestation 在、current summary 也能读到 lane | current-head external distribution 没有 verified 证据，GHCR readiness 直接 blocked | `WS2` | readiness artifact + current-head remote workflow + digest pull/provenance |
| `R3` 深水区英文边界没切干净 | README/public docs 看起来像开源项目 | 治理脚本、运行时模板、部分源码仍残留大量中文，全球开发者难以自排障 | `WS3` | language boundary gate + allowlist |
| `ILL-1` 轻 gate 幻觉 | `governance-audit PASS` | 这只是“教务系统正常”，不是“毕业考试已过” | `WS1` | `docs/reference/done-model.md`, `newcomer-result-proof.json` |
| `ILL-2` required checks 幻觉 | `remote-required-checks=pass` | 这只是“监考名单对齐”，不是“所有考试已经考完” | `WS2` | `docs/reference/external-lane-status.md`, `current-state-summary.md` |
| `ILL-3` 开源外观幻觉 | public repo、MIT、SECURITY、CONTRIBUTING、THIRD_PARTY_NOTICES 都在 | 仍不能诚实宣称 external distribution 和 global contributor friendliness 已闭环 | `WS3` | public readiness docs + language gate + current external proof |

## [五] 绝不能妥协的红线

- 不再把 `governance-audit PASS` 写成 repo-side done。
- 不再把 `remote-required-checks=pass` 写成 terminal closure。
- 不再把 old-head remote workflow 说成 current external verification。
- 不再在治理脚本、错误信息、日志诊断和 contributor-facing runtime surface 中新增中文。
- 不再把 tracked docs / generated docs 当成 current-state payload 存放处。
- 不再新增 repo 根运行时输出路径；所有新输出必须进入 `.runtime-cache/{run,logs,reports,evidence,tmp}`。
- 不再以“先继续补 repo-side 漂亮治理”为主路线，除非它直接改变 WS1/WS2/WS3 的成立条件。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` Repo-side Strict Current Receipt Closure | 把当前 `partial` 拉成 repo-side current PASS 或得到最深失败位置 | `bin/repo-side-strict-ci`, `bin/strict-ci`, `scripts/ci/strict_entry.sh`, `.runtime-cache/reports/governance/newcomer-result-proof.json`, `.runtime-cache/reports/governance/current-state-summary.md` | “governance-audit PASS 就够了”的读法 | 当前 HEAD 拿到 strict manifest + PASS receipt，`newcomer-result-proof.status=pass` | `P0` |
| `WS2` GHCR External Distribution Closure | 把 `ghcr-standard-image` 从 blocked 拉到 current-head verified，并带动 external compat row 收口 | `.github/workflows/build-ci-standard-image.yml`, `scripts/ci/check_standard_image_publish_readiness.sh`, `scripts/ci/build_standard_image.sh`, `infra/config/strict_ci_contract.json`, `.runtime-cache/reports/governance/external-lane-workflows.json` | 任何 old-head workflow 冒充 current external proof 的说法 | current-head GHCR workflow 成功，digest 可证实，`strict-ci-compose-image-set` 不再 pending behind GHCR | `P0` |
| `WS3` Deep-Water English / Global Contributor Boundary Hard-Cut | 把治理脚本、诊断面、贡献者表面英文化，只把中文保留在产品内容允许面 | `scripts/governance/*`, `apps/worker/worker/pipeline/runner_rendering.py`, `apps/worker/worker/pipeline/steps/artifacts.py`, `apps/worker/worker/pipeline/steps/llm_prompts.py`, `scripts/governance/check_governance_language.py`, `docs/reference/public-repo-readiness.md` | “public source-first 就等于全球协作友好”的错觉 | governance/runtime/contributor-facing surface 英文化并有 allowlist gate | `P1` |
| `WS4` Public / Platform Trust Hardening | 把 repo-side 强治理进一步映射到 GitHub 平台侧信任边界 | `.runtime-cache/reports/governance/remote-platform-truth.json`, `.github/workflows/ci.yml`, GitHub repo settings, `docs/reference/public-repo-readiness.md` | 默认接受 `allowed_actions=all` / `sha_pinning_required=false` 的宽松状态 | repo settings 收紧或例外被显式建账并被远端 probe 断言 | `P1` |
| `WS5` Residual Evidence / Upstream Hygiene Closure | 收口 GHCR 解封后的 dependent rows、残余日志/缓存/证据负债 | `config/governance/upstream-compat-matrix.json`, `.runtime-cache/reports/governance/upstream-compat-report.json`, `docs/reference/logging.md`, `docs/reference/cache.md` | “inventory 完整=全部 verified”的读法 | only real blockers remain blocked，所有 verified row 都有 current same-run proof | `P2` |

### Workstream 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` | `Partially Completed` | `P0` | `L1 Coordinator` | strict current receipt 已 fresh PASS，并已重拍 newcomer/current-state | 将 WS1 剩余问题降级为 dirty-worktree blocker 并停止再追 repo-side 结构性修复 | `Verified at receipt level` |
| `WS2` | `Partially Completed` | `P0` | `L1 Coordinator` | local capability is now strongly established: `terryyifeng` can make readiness `READY`, `xiaojiou176` can dispatch current-head workflow runs, the latest current-head run `23287211899` still fails at `Standard image publish preflight`, and a local hosted-token workflow patch plus contract test are ready-to-ship | wait for commit/push authorization so the hosted-token workflow fix can actually run remotely on current HEAD | `Current-head remote failure reproduced; local fix ready-to-ship` |
| `WS3` | `Partially Completed` | `P1` | `L1 Coordinator` | maintainer-surface-first English hard cut has landed for renderers and core governance reference docs; docs/current-proof gates still pass | decide whether to extend the English boundary gate and whether to move into product-content-layer review | `Verified for first batch` |
| `WS4` | `Not Started` | `P1` | `L1` | 平台 trust hardening 尚未动手 | 等 WS2 现态明确后再推进 | `Not Started` |
| `WS5` | `Completed` | `P2` | `L1 + debugger` | stale-proof refresh work is fully closed for current local capabilities: API status false-negative is fixed, runtime web dependency completeness is repaired, `smoke-full-stack` passes, `run-daily-digest` has refreshed the Resend proof, and `governance-audit` is green again | no further local action unless freshness expires again or a new runtime bug appears | `Verified` |

## [七] 详细 Workstreams

### `WS1` Repo-side Strict Current Receipt Closure

#### 目标

把当前最重、最诚实的 repo-side blocker 解决掉：

- 当前 `worktree` clean
- 当前 `current-proof alignment` pass
- 当前 `governance-audit` pass
- 但当前 `repo_side_strict_receipt` 仍是 `missing_current_receipt`

换句话说，**厨房卫生合格，但最重那张营业执照复核单还没打出来**。

#### 为什么它是结构性动作

- 它决定 repo-side done 能不能被诚实宣称。
- 它直接打掉 `ILL-1`。
- 它会改变一切上层判断：招聘信号、完成判断、后续是否该把火力全转向 external lane。

#### 输入

- [bin/repo-side-strict-ci](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/repo-side-strict-ci)
- [bin/strict-ci](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/strict-ci)
- [scripts/ci/strict_entry.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/strict_entry.sh)
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [scripts/governance/render_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_newcomer_result_proof.py)
- [scripts/governance/check_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_newcomer_result_proof.py)

#### 输出

- fresh strict manifest
- fresh strict PASS or deepest failing gate
- refreshed newcomer result proof
- refreshed current-state summary

#### 改哪些目录 / 文件 / 配置 / Gate

- 主执行入口：
  - `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- 若失败，按 deepest honest stop 修复：
  - `scripts/quality_gate.sh`
  - `scripts/ci/*`
  - 相关 `docs/reference/*` / `docs/testing.md` / `README.md`
  - 受影响的 gate 脚本与契约文件
- 运行态刷新：
  - `.runtime-cache/run/manifests/*.json`
  - `.runtime-cache/logs/governance/strict-ci-entry.jsonl`
  - `.runtime-cache/reports/governance/newcomer-result-proof.json`
  - `.runtime-cache/reports/governance/current-state-summary.md`

#### 删除哪些旧结构

- 不删除代码结构。
- 但要删除一种**叙事结构**：把 governance PASS 冒充 repo-side done。

#### 迁移哪些旧路径

- 无路径迁移。
- 语义迁移：所有“repo-side 已完成”的说法必须迁移到 strict receipt 驱动。

#### 哪些兼容桥可临时存在

- `current_workspace_verdict=partial` 可以短期存在，直到 strict PASS 收据被 fresh 捕获。
- `governance-audit PASS` 可以继续作为必要不充分条件存在。

#### 兼容桥删除条件与时点

- 一旦当前 HEAD 产生 strict PASS receipt 并刷新 newcomer/current-state，所有 `repo-side current proof missing` 相关临时说明都应删除或降为 historical note。

#### Done Definition

- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 对当前 HEAD fresh 通过
- `.runtime-cache/run/manifests/` 下出现当前 commit 的 `strict-ci` manifest
- `newcomer-result-proof.json` 中 `repo_side_strict_receipt.status=pass`
- `newcomer-result-proof.json` 顶层 `status=pass`
- `current-state-summary.md` 中 `current workspace verdict=pass`

#### Fail Fast 检查点

- 若命令未生成当前 commit manifest：先查 entrypoint/bootstrap，不做 docs 修改
- 若 manifest 生成但无 PASS：只修 deepest gate，不并行做开源/翻译/平台策略
- 若 strict pass 但 newcomer 仍 partial：先查 render/check proof 逻辑，再谈其他问题

#### 它会打掉什么幻觉

- `ILL-1 governance-audit PASS = repo-side done`

#### 它会改变哪个上层判断

- repo-side 完成度判断
- 整体“半闭环还是只剩 external”判断
- 下一轮是否应 100% 转火到 GHCR external lane

---

### `WS2` GHCR External Distribution Closure

#### 目标

把 `ghcr-standard-image` 从 current `blocked` 拉到 current-head `verified`，并顺带推进 `strict-ci-compose-image-set`。

#### 为什么它是结构性动作

- 这是当前 external lane 的主 blocker。
- 它决定仓库能不能从“源码公开”升级到“外部分发也可信”。
- 它直接决定 public/open-source 叙事能不能再往前走一步。

#### 输入

- [build-ci-standard-image.yml](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.github/workflows/build-ci-standard-image.yml)
- [scripts/ci/check_standard_image_publish_readiness.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/check_standard_image_publish_readiness.sh)
- [scripts/ci/build_standard_image.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/build_standard_image.sh)
- [infra/config/strict_ci_contract.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/infra/config/strict_ci_contract.json)
- [standard-image-publish-readiness.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/governance/standard-image-publish-readiness.json)
- [current-state-summary.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/governance/current-state-summary.md)
- [config/governance/upstream-compat-matrix.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/config/governance/upstream-compat-matrix.json)

#### 输出

- current-head successful remote GHCR workflow
- verified readiness artifact
- published digest and refreshed strict contract if needed
- refreshed external-lane-workflows artifact
- `strict-ci-compose-image-set` no longer pending behind GHCR

#### 改哪些目录 / 文件 / 配置 / workflow / gate

- Workflow:
  - `.github/workflows/build-ci-standard-image.yml`
- Local/CI scripts:
  - `scripts/ci/check_standard_image_publish_readiness.sh`
  - `scripts/ci/build_standard_image.sh`
  - `scripts/governance/probe_external_lane_workflows.py`
- Contracts / reports:
  - `infra/config/strict_ci_contract.json`
  - `config/governance/upstream-compat-matrix.json`
  - `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
  - `.runtime-cache/reports/governance/external-lane-workflows.json`

#### 删除哪些旧结构

- 任何 old-head workflow 成功记录被当成 current external verification 的读法

#### 迁移哪些旧路径

- 无路径迁移
- 语义迁移：GHCR readiness 从 “historical blocked but maybe close enough” 迁到 “current-head verified or explicitly blocked”

#### 哪些兼容桥可临时存在

- `release-evidence-attestation=ready` 可以暂时继续存在
- `strict-ci-compose-image-set=pending` 可暂时存在，但只能明确挂在 GHCR blocker 之后

#### 兼容桥删除条件与时点

- 当前 HEAD 的 GHCR workflow 成功并产出 current digest 后
- dependent compat row 被 same-run 证据升级后

#### Done Definition

- `standard-image-publish-readiness.json` 对当前 HEAD 为 `verified` 或等价成功态
- `.runtime-cache/reports/governance/external-lane-workflows.json` 记录 current-head workflow success
- 当前 digest 可被 remote attestation / registry query 证实
- `strict-ci-compose-image-set` 从 `pending` 升级为 `verified` 或被更精确 blocker 重新分类

#### Fail Fast 检查点

- 若 readiness 仍报 `no token path with packages write capability detected`：停在 secrets/ACL，不改 repo 其他结构
- 若 build 成功但 push 403：停在 registry ownership / package ACL
- 若 workflow success 但 contract digest 未刷新：先修 contract / receipt refresh，再谈 downstream row

#### 它会打掉什么幻觉

- `workflow 存在/SBOM 存在/attestation 存在 = external lane 已闭环`

#### 它会改变哪个上层判断

- external distribution 能不能被诚实宣称
- public/open-source readiness 能否从 source-first 继续上台阶
- upstream compat pending row 是否还能继续拖尾

---

### `WS3` Deep-Water English / Global Contributor Boundary Hard-Cut

#### 目标

把深水区协作面英文化，只把中文保留在真正应该保留的产品内容层。

这里的“深水区”指的是：

- governance scripts
- runtime diagnostics
- CI / gate output
- contributor-facing public docs
- exception / failure wording

不是所有中文都必须消灭。  
比如视频摘要产物如果本来就是中文用户内容，可以保留；但 **“报错、排障、贡献、门禁、策略” 这些面不该继续主要靠中文承载**。

#### 为什么它是结构性动作

- 它决定这个 public repo 到底是“别人能看”还是“别人能接”。
- 它直接影响 global contributor ability、Google/GitHub 搜索可达性、issue/PR 协作效率。
- 它打掉 `ILL-3`。

#### 输入

- `rg` 命中的中文重区：
  - [apps/worker/worker/pipeline/steps/artifacts.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/steps/artifacts.py)
  - [apps/worker/worker/pipeline/runner_rendering.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/runner_rendering.py)
  - [apps/worker/worker/pipeline/steps/llm_prompts.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/steps/llm_prompts.py)
  - [scripts/governance/render_current_state_summary.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_current_state_summary.py)
  - [scripts/governance/check_runtime_outputs.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_runtime_outputs.py)
  - [scripts/governance/render_docs_governance.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_docs_governance.py)
  - [AGENTS.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/AGENTS.md)
  - [CLAUDE.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/CLAUDE.md)

#### 输出

- 明确 language boundary policy
- 中文 allowlist
- governance/runtime/contributor-facing surface 英文化
- 对应 gate

#### 改哪些目录 / 文件 / 配置 / task / gate

- 新增或调整 language boundary truth source：
  - `config/governance/language-boundary.json` 或等价契约文件
- 强化 gate：
  - `scripts/governance/check_governance_language.py`
- 迁移 contributor-facing public docs：
  - `README.md`
  - `CONTRIBUTING.md`
  - `SUPPORT.md`
  - `SECURITY.md`
  - 必要时根级 `AGENTS.md` / `CLAUDE.md` 区分“内部协作记忆”与“公共协作文档”
- 清理治理脚本输出与错误文案：
  - `scripts/governance/*`
  - `scripts/ci/*`
  - `scripts/runtime/*`

#### 删除哪些旧结构

- 默认允许中文落在 governance/runtime/contributor-facing 面的旧习惯

#### 迁移哪些旧路径

- 无路径迁移
- 语义迁移：中文从“治理与排障主语言”迁到“产品内容或明确 allowlisted 区域”

#### 哪些兼容桥可临时存在

- 产品内容层的中文模板可暂存
- docs 中对中文用户的说明可存在，但公共协作入口必须有英文主版本

#### 兼容桥删除条件与时点

- language boundary gate 落地后
- contributor-facing public docs 完成英文主路径后

#### Done Definition

- governance/runtime/contributor-facing surface 不再出现未 allowlist 的中文
- language gate 对该边界 fail-close
- public/open-source readiness 文档明确声明允许与禁止的中文面

#### Fail Fast 检查点

- 若某段中文实为产品输出契约，先登记 allowlist，不要粗暴翻译坏行为
- 若某文件是内部协作记忆面，不要误当 public contributor surface

#### 它会打掉什么幻觉

- `public repo + 开源文档齐全 = 全球开发者可顺滑协作`

#### 它会改变哪个上层判断

- 开源 readiness
- 招聘信号中的“能不能让陌生团队接手”
- public/source-first 到 global collaborator-friendly 的升级空间

---

### `WS4` Public / Platform Trust Hardening

#### 目标

把 repo-side 强治理向 GitHub 平台侧再推进一步：  
如果平台设置能收紧，就收紧；如果受组织级限制，就**显式建账**，不要默默接受“平台比 repo 松很多”。

#### 为什么它是结构性动作

- 仓库已经 public，平台侧策略就是供应链的一部分。
- 如果 `allowed_actions=all`、`sha_pinning_required=false` 一直不动，repo-side 再严也会留下“平台边界偏软”的口子。

#### 输入

- [remote-platform-truth.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/governance/remote-platform-truth.json)
- `.github/workflows/*.yml`
- `docs/reference/public-repo-readiness.md`
- GitHub repo settings / branch protection

#### 输出

- 收紧后的平台策略，或
- 明确的 platform exception ledger

#### 改哪些目录 / 文件 / 配置 / task / gate

- GitHub repo settings
- remote probe / docs：
  - `scripts/governance/probe_remote_platform_truth.py`
  - `docs/reference/public-repo-readiness.md`
  - 如需要，新建 `docs/reference/public-platform-exceptions.md`

#### 删除哪些旧结构

- “平台侧先不管，只看 repo-side” 的默认心态

#### 迁移哪些旧路径

- 无路径迁移

#### 哪些兼容桥可临时存在

- 如果组织策略暂时不允许修改平台设置，可用 exception ledger 暂时承接

#### 兼容桥删除条件与时点

- 一旦平台设置可改，立即去掉 exception 并改为实际策略

#### Done Definition

- `remote-platform-truth.json` 中平台策略达到目标，或例外被显式建账且被 probe/文档消费
- `public readiness` 文档与远端 truth 一致

#### Fail Fast 检查点

- 若某项平台策略受组织级约束，不要在 repo 里假装已经开启

#### 它会打掉什么幻觉

- `repo-side 很严 = GitHub 平台侧同样很严`

#### 它会改变哪个上层判断

- 公开仓供应链可信度
- external/public 审计里的平台边界成熟度

---

### `WS5` Residual Evidence / Upstream Hygiene Closure

#### 目标

在 WS1/WS2/WS3 完成后，把剩余 dependent rows、日志/缓存/证据卫生问题收口，不让 repo 再被“只差一点点”的尾巴拖住。

#### 为什么它是结构性动作

- 它防止完成后又因 stale receipts、pending rows、未清语言残留重新回到“半成熟”。

#### 输入

- `config/governance/upstream-compat-matrix.json`
- `.runtime-cache/reports/governance/upstream-compat-report.json`
- `docs/reference/logging.md`
- `docs/reference/cache.md`
- `config/governance/runtime-outputs.json`

#### 输出

- only-real-blockers remain
- verified rows are current
- residual hygiene debt has explicit owner

#### 改哪些目录 / 文件 / 配置 / task / workflow / gate

- `config/governance/upstream-compat-matrix.json`
- `scripts/governance/check_upstream_compat_freshness.py`
- `scripts/governance/check_upstream_same_run_cohesion.py`
- `scripts/governance/check_logging_contract.py`
- `scripts/governance/check_runtime_outputs.py`
- `docs/reference/logging.md`
- `docs/reference/cache.md`

#### 删除哪些旧结构

- “inventory 完整=已经验证”的读法

#### 迁移哪些旧路径

- 无路径迁移

#### 哪些兼容桥可临时存在

- 明确 blocker 的 pending row 可以保留

#### 兼容桥删除条件与时点

- 当前 row 拿到 same-run verified 证据后

#### Done Definition

- 所有 verified row 都有 current same-run proof
- 所有 pending row 都有诚实 blocker 原因
- logging/cache/runtime outputs contract 与 docs 同步

#### Fail Fast 检查点

- 若 WS2 未完成，不要提前强行把 `strict-ci-compose-image-set` 升级为 verified

#### 它会打掉什么幻觉

- `inventory / matrix / report 很全 = 外部依赖治理全部闭环`

#### 它会改变哪个上层判断

- upstream 健康度
- 长期维护税
- 后续 audit 稳定度

## [八] 硬切与迁移方案

### 立即废弃项

- 把 `governance-audit PASS` 当 repo-side done 的表述
- 把 `remote-required-checks=pass` 当 terminal closure 的表述
- 把 old-head remote workflow 当 current external proof 的表述
- 在治理脚本 / 诊断面新增中文

### 迁移桥

- `current_workspace_verdict=partial`：在 WS1 完成前临时保留
- `release-evidence-attestation=ready`：在 WS2 完成前临时保留
- 中文产品输出 allowlist：在 WS3 完成前临时保留
- 平台策略 exception ledger：在 WS4 完成前按需保留

### 禁写时点

- 从本 Plan 生效起，禁止给新 docs / scripts / runtime diagnostics 添加中文
- 从本 Plan 生效起，禁止新增 repo 根运行时输出路径
- 从本 Plan 生效起，禁止新增“current-state” tracked docs

### 只读时点

- 历史 release evidence 样例：继续只读，不得冒充 current verdict
- old-head external workflow receipts：只读 historical，不得参与 current closure 判定

### 删除时点

- WS1 完成后，删除所有“repo-side 其实差不多了”的临时说明
- WS2 完成后，删除所有“GHCR blocked but maybe close enough”的临时叙述
- WS3 完成后，删除 governance/runtime/contributor surface 的中文遗留

### 防永久兼容机制

- 每个兼容桥都必须有：
  - owner
  - 退出条件
  - 退出时点
  - 对应 gate

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| Repo-side strict receipt | 当前 HEAD 是否有 strict PASS 重收据 | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` + manifest/log scan | 当前 commit 出现 strict manifest 且 PASS | repo-side done 仍不能宣称 |
| Repo-side current proof | newcomer / summary 是否从 partial 变 pass | `python3 scripts/governance/check_newcomer_result_proof.py`; `python3 scripts/governance/check_current_state_summary.py` | 两者均为 `pass` 且 blockers 为空 | 仍有 current receipt 缺口 |
| GHCR readiness | 标准镜像发布前置是否通过 | `bash scripts/ci/check_standard_image_publish_readiness.sh` | readiness 为 verified/ok | external lane 仍 blocked |
| GHCR current-head workflow | 远端 current-head 是否真正 publish 成功 | `build-ci-standard-image.yml` + `external-lane-workflows.json` | current HEAD workflow success | old-head 历史成功不能算 current proof |
| Release evidence | release lane 是否只是 ready 还是 verified | `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` + workflow probe | readiness 正确 + current-head remote verified | external release 仍未闭环 |
| Open-source safety freshness | 当前 HEAD 的安全/secret proof 是否 current | `./bin/open-source-audit-refresh`; `python3 scripts/governance/check_open_source_audit_freshness.py` | pass 且 source_commit 对齐当前 HEAD | 旧 gitleaks 收据仍在冒充 current |
| Docs truth | 文档控制面是否与当前 repo 真相一致 | `python3 scripts/governance/check_docs_governance.py` | pass | docs 与 control plane 漂移 |
| Current-proof alignment | 外部 current-proof artifact 是否对齐当前 HEAD | `python3 scripts/governance/check_current_proof_commit_alignment.py` | pass | runtime reports 不能当 current state 使用 |
| Root cleanliness | 根目录是否仍受 allowlist 治理 | `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | pass | repo 根重新脏化 |
| Runtime outputs | 输出路径是否合法 | `python3 scripts/governance/check_runtime_outputs.py` | pass | runtime noise 逃出合法分舱 |
| Logging governance | 日志 schema / correlation 是否成立 | `python3 scripts/governance/check_logging_contract.py` | pass | 诊断面不可追踪 |
| Global contributor boundary | 深水区是否已英文化 | `python3 scripts/governance/check_governance_language.py` + allowlist | governance/runtime/contributor-facing surface 无未允许中文 | public/open-source 协作边界仍不成立 |
| Upstream compat | dependent rows 是否 current same-run verified | `python3 scripts/governance/check_upstream_compat_freshness.py`; `check_upstream_same_run_cohesion.py` | verified row current，pending row honest | inventory 仍在冒充 closure |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| `Phase 0` | 冻结叙事红线：不再把 governance/required-checks 写成 done | 无 | 可并行写文档守则 | 红线明确写入相关 docs / plan | 若跳过，后续又会被表面绿灯误导 |
| `Phase 1` | 执行 `WS1`，获取 strict current receipt 或最深失败点 | clean worktree | 串行 | strict manifest + PASS 或最深 blocker 定位 | 若并行做其他 WS，容易浪费修复火力 |
| `Phase 2` | 执行 `WS2`，攻 GHCR external lane | `WS1` 至少拿到 repo-side current truth | 串行主路径 | GHCR current-head verified 或最深平台 blocker 固定 | 若 strict 仍未收口，会混淆 repo-side 与 external 问题 |
| `Phase 3` | 执行 `WS3`，硬切 deep-water English boundary | `WS1` / `WS2` 主 blocker 已定型 | 可与 `WS4` 部分并行 | language boundary gate 成立 | 若太早做，可能在 blocker 修复中反复重写文案 |
| `Phase 4` | 执行 `WS4`，收紧平台策略或显式建账 | `WS2` blocker 真实边界已知 | 可与 `WS3` 并行 | remote platform truth 达到目标或例外显式化 | 若组织侧受限，需改为 exception ledger |
| `Phase 5` | 执行 `WS5`，清 remaining pending rows 与 residual hygiene | `WS2` 完成或稳定 blocked reason | 可并行子项 | verified row current；pending row honest | 若提前做，会反复重拍无效收据 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| 补 current strict receipt | 改变“repo-side 是否已完成”判断 | 这是当前唯一 repo-side 硬 blocker |
| 修 GHCR external lane | 改变“能不能安全对外分发”判断 | external lane 的主红灯就在这里 |
| 硬切 deep-water English boundary | 改变“能不能被全球开发者顺滑接手”判断 | public source-first 不等于 global contributor-friendly |
| 收紧平台策略或建账 | 改变“平台供应链是否和 repo-side 一样可信”判断 | settings 也是事实源的一部分 |
| 刷 dependent compat rows | 改变“external upstream 健康度”判断 | inventory 只有 current same-run verified 才算 closure |

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 `WS1`：补 current HEAD 的 repo-side strict receipt

- **为什么先做**
  - 它是当前 top-level `partial` 的直接原因
  - 只有它结束，才能诚实判断“repo-side 是否已完成”
- **打掉什么幻觉**
  - `governance-audit PASS = repo-side done`
- **释放什么能力**
  - 允许把主要火力彻底转向 external lane

### 2. 再做 `WS2`：修 GHCR external distribution

- **为什么第二**
  - 这是 external/public distribution 的唯一主 blocker
  - 不解决它，仓库永远只能停在 source-first，而不能升级到可信 external delivery
- **打掉什么幻觉**
  - `workflow / SBOM / attestation 都在 = external 已闭环`
- **释放什么能力**
  - 让 `strict-ci-compose-image-set` 和 external lane 真正 current-head 化

### 3. 然后做 `WS3`：硬切 deep-water English boundary

- **为什么第三**
  - 前两项是“收据问题”，第三项是“全球协作问题”
  - 它会直接改变 open-source/readiness 与招聘信号
- **打掉什么幻觉**
  - `public repo + 文档齐全 = 全球开发者可顺滑接手`
- **释放什么能力**
  - 让这个仓库从“强中文 source-first 项目”更接近“全球可协作工程项目”

## [十三] 不确定性与落地前核对点

### 高置信事实

- 当前 `HEAD` clean 且对齐 `origin/main`
- 当前 newcomer/current-state 都是 `partial`
- 当前 blocker 是 `repo_side_strict_missing_current_receipt`
- 当前 GHCR lane blocked
- 当前 release-evidence lane 只是 `ready`
- 当前 deep-water English boundary 问题真实存在

### 中置信反推

- `WS1` 可能只需跑 gate 并捕获 PASS，不一定需要源码修复
- `WS4` 可能受组织级 GitHub 设置约束

### 落地前要二次核对

- `WS1` 执行后 strict gate 的 deepest honest stop
- `WS2` 里 GHCR 权限到底卡在 token scope、package ACL、repo ownership 还是 org policy
- `WS3` 中哪些中文属于产品输出契约，必须 allowlist 而不是翻译

### 但不得借此逃避的设计

- 主路线顺序不变：`WS1 -> WS2 -> WS3 -> WS4 -> WS5`
- 不因不确定性而回到“先做一些容易的 docs/cleanup”路线

## [十四] 执行准备状态

### Current Status

- `HEAD`: `e13b047e2686943481aeec5d25e5025b7083c77e`
- `branch`: `main`
- `worktree`: dirty
- `current-proof alignment`: pass
- `governance-audit`: pass
- `current workspace verdict`: partial
- `repo_side_strict_receipt`: pass
- `ghcr-standard-image`: blocked
- `release-evidence-attestation`: ready (not current-head verified)
- `validated tracked diff`: `apps/worker/tests/test_external_proof_semantics.py`
- `current fail-close blocker`: `dirty_worktree`
- `strict receipt manifest`: `.runtime-cache/run/manifests/9449f74b5c4d44e1af11737c6e53e916.json`
- `ghcr local env paths`: unset in current shell (`GHCR_WRITE_*`, `GHCR_*`, `GITHUB_TOKEN`)
- `gh local auth capability`: `gh auth` is available; `xiaojiou176` can dispatch workflow runs, `terryyifeng` makes local readiness `READY`
- `ws2 local ship status`: hosted-token workflow patch is implemented locally and backed by a targeted contract test
- `fresh governance blocker`: none inside current local-capability lanes; `governance-audit` is green again
- `runtime freshness result`: RSSHub/web and Resend refresh paths are both working again; local provider-side freshness proofs are current

### Next Actions

1. 将 `WS1` 结果正式结案为“receipt 已拿到；当前 repo-side pass 仅被 dirty worktree 阻塞”
2. 将 `WS2` 正式记账为“本地 patch ready-to-ship，但远端 current-head run 仍在跑已提交版本；要继续推进必须让 workflow patch 进入远端”
3. 将 `WS3` 的第一批落地结果正式结案，并决定是否继续补 English-only gate
4. 在不越过未授权 commit/push 边界的前提下，把 WS2 修复补到 ready-to-ship 状态
5. 如需让 `current_workspace_verdict` 变成 `pass`，需要在得到用户授权后处理 tracked worktree changes（提交或其他明确处置），而不是继续修改 repo-side 结构

### Decision Log

- 决定不再把 docs/current-summary seam 作为主 blocker，因为当前它已经 fail-close 生效
- 决定把 strict current receipt 提升为第一优先级，因为这是当前 top-level partial 的直接原因
- 决定把 deep-water English boundary 提升为前三 workstream，因为它比继续做 docs/CI 漂亮化更能改变开源与协作判断
- 决定接管当前唯一存活且时间最新、语义最匹配的 Plan：`2026-03-18_23-11-47__repo-validated-ultimate-master-plan.md`
- 决定用 Repo 真相推翻本文件中旧的 `worktree=clean` 说法，并立即校准状态区
- 决定保留 `apps/worker/tests/test_external_proof_semantics.py` 的 tracked diff；该改动已通过 targeted pytest 验证，不再视为未知风险
- 决定将 `WS2` 的执行顺序收紧为先 readiness 脱离 `registry-auth-failure`，再追 remote `verified`
- 决定将英文化 hard cut 重新挂回正确编号 `WS3`，而不是误挂到 `WS4`
- 决定将 `WS3` 第一阶段限定在 maintainer/runtime/governance surface，不把产品内容层中文一刀切
- 决定在未获 commit 授权前，不把 dirty-worktree blocker 伪装成 repo-side 结构问题
- 决定在当前 shell 中将 `WS2` 记为真实 blocked：`GHCR_WRITE_USERNAME/GHCR_WRITE_TOKEN/GHCR_USERNAME/GHCR_TOKEN/GITHUB_TOKEN` 全部 unset，当前能力范围内无法继续做 current-head publish closure
- 决定本轮先把 WS3 收口到维护/诊断/治理解释层，不在没有产品裁决的情况下硬改中文 digest/product output
- 决定接受 fresh governance-audit 结果为新的真实裁决：`WS5` 不再是纯后置项，因为 `rsshub-youtube-ingest-chain` proof 已在 72h 边界变 stale
- 决定将 `WS5` 当前问题从“纯 freshness 过期”升级为“full-stack runtime inconsistency bug”，因为本地重拍尝试已证明 `full-stack up` 的 ready 判词与实际进程存活不一致
- 决定接受更硬的新证据：这不是单纯旧缓存复用，因为强制重装 runtime web workspace 后仍然没有 `lightningcss.darwin-arm64.node`
- 决定接受 fresher runtime evidence：RSSHub/web 分支已经被补通，`WS5` 的当前 freshest blocker 已经切换成 Resend proof 过期
- 决定先落地一个最小且已证实的修复：去掉 `scripts/runtime/full_stack.sh` 对 API 进程命令行必须包含 `ROOT_DIR` 的错误要求，修复 `api: stopped` false-negative
- 决定将 `WS5` 结案为当前本地能力范围内已完成：`smoke-full-stack` 和 `run-daily-digest` 的 fresh receipts 都已经补齐，`governance-audit` 重新回绿
- 决定将 `WS2` 从“纯 blocked”升级成“本地与远端能力都已摸到，但 remote current-head 仍失败；下一步卡在 commit/push 让 workflow 变更真正生效”
- 决定为 `WS2` 增补 workflow contract test，防止 hosted workflow 再次优先吃失效的 `GHCR_WRITE_*` secret
- 决定用 fresh runtime-owned external workflow probe 覆盖旧 run 号：`WS2` 当前远端真相以 `23287211899` 为准，不再引用较早的 current-head failure

### Validation Log

- `git status --short --branch` -> dirty on `main`
- `python3 scripts/governance/check_current_proof_commit_alignment.py` -> PASS
- `python3 scripts/governance/check_newcomer_result_proof.py` -> PASS
- `python3 scripts/governance/check_current_state_summary.py` -> PASS
- `python3 scripts/governance/check_docs_governance.py` -> PASS
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` -> PASS
- refreshed `newcomer-result-proof.json` -> `repo_side_strict_receipt=pass`, `current_workspace_verdict=partial`, `blocking_conditions=[dirty_worktree]`
- refreshed `current-state-summary.md` -> `repo-side-strict receipt=pass`, `current workspace verdict=partial`, fail-close blocker `dirty_worktree`
- manifest scan -> current commit now has strict manifest `9449f74b5c4d44e1af11737c6e53e916.json`
- `WS2` validator -> blocker remains `registry-auth-failure`; readiness artifact must become non-blocked before current-head remote verification can close the lane
- local env probe -> `GHCR_WRITE_USERNAME/GHCR_WRITE_TOKEN/GHCR_USERNAME/GHCR_TOKEN/GITHUB_TOKEN` are all unset in the current shell
- `WS3` validator -> first batch is `scripts/governance/**` + `docs/reference/**`; `apps/worker` product-content layer must be treated separately
- `python3 scripts/governance/render_docs_governance.py` -> PASS
- `python3 scripts/governance/check_docs_governance.py` -> PASS
- `python3 scripts/governance/render_current_state_summary.py` -> PASS
- `python3 scripts/governance/check_current_state_summary.py` -> PASS
- `python3 scripts/governance/render_newcomer_result_proof.py` -> PASS
- `python3 scripts/governance/check_newcomer_result_proof.py` -> PASS
- targeted English-boundary scan across `scripts/governance/render_current_state_summary.py`, `scripts/governance/render_docs_governance.py`, `docs/reference/{done-model,external-lane-status,runner-baseline,root-governance,upstream-compatibility-policy,mcp-tool-routing}.md` -> no Chinese remains
- `python3 scripts/governance/check_governance_language.py` -> PASS
- `./bin/governance-audit --mode audit` -> FAIL at `[upstream-compat-freshness]`: `rsshub-youtube-ingest-chain` artifact `.runtime-cache/logs/tests/smoke-full-stack.jsonl` aged out at the 72h window
- `./bin/bootstrap-full-stack` -> PASS
- `./bin/full-stack up` -> reports ready
- `./bin/smoke-full-stack` -> FAIL (`http://127.0.0.1:9000/healthz -> 000`)
- `./bin/full-stack status` after the failure -> `api: stopped`, `worker: stopped`, `web: stopped`
- `lsof -nP -iTCP:9000 -sTCP:LISTEN` / `lsof -nP -iTCP:13001 -sTCP:LISTEN` -> no listeners
- `pgrep -af 'apps\\.api\\.app\\.main:app|scripts/dev_api\\.sh|uvicorn.*apps\\.api\\.app\\.main:app'` -> no API process
- `pgrep -af 'worker\\.main run-worker|scripts/dev_worker\\.sh'` -> no worker process
- isolated web-only launch using the same runtime workspace and env wrapper (without `setsid`) -> survives and listens beyond 20s on ports `13125` / `13126`
- `curl http://127.0.0.1:9000/healthz` -> 200 and `lsof -nP -iTCP:9000 -sTCP:LISTEN` shows a live API listener
- after fixing API signature detection, `./bin/full-stack status` now reports `api: running` and `worker: running`; only `web` remains `stopped`
- repeated `./bin/smoke-full-stack` now passes API + feed and consistently fails at `http://127.0.0.1:13001 -> 000`
- `bash ./scripts/ci/prepare_web_runtime.sh --shell-exports` after the platform-aware cache-key fix now forces a real reinstall (`added 789 packages`) and still fails with `[prepare_web_runtime] expected native runtime dependency missing for platform darwin-arm64`
- `bash ./scripts/ci/prepare_web_runtime.sh --shell-exports` now succeeds after the native dependency check fix
- `./bin/full-stack up` + `./bin/smoke-full-stack` now complete successfully on the current run
- refreshed `current-state-summary.md` shows `rsshub-youtube-ingest-chain=verified`
- fresh `./bin/governance-audit --mode audit` now fails only at `[upstream-compat-freshness]`: `resend-digest-delivery-chain` stale `.runtime-cache/logs/tests/compat-resend-daily-sent.log`
- `NOTIFICATION_ENABLED=true ./bin/run-daily-digest` -> `status=sent` with fresh `.runtime-cache/logs/tests/compat-resend-daily-sent.log`
- `config/governance/upstream-compat-matrix.json` updated to the fresh RSSHub/Resend run ids and timestamps
- final `./bin/governance-audit --mode audit` -> PASS
- `gh auth status` -> local machine has multiple GitHub auth contexts; active `xiaojiou176` lacks `write:packages`, inactive `terryyifeng` advertises `write:packages`
- controlled local readiness trial under `terryyifeng` -> `check_standard_image_publish_readiness.sh` returned `READY`
- controlled remote workflow dispatch under `xiaojiou176` -> current-head run `23287211899` created and failed at step `Standard image publish preflight`
- current-head remote job log for run `23287211899` still shows the hosted workflow using `GHCR_WRITE_USERNAME/GHCR_WRITE_TOKEN` in login/preflight, proving the local workflow patch has not taken effect remotely yet
- `apps/worker/tests/test_supply_chain_ci_contracts.py` -> 18 passed after adding the hosted-token workflow contract assertion
- `apps/worker/tests/test_external_proof_semantics.py` -> 11 passed with the current tracked diff
- `python3 scripts/governance/probe_external_lane_workflows.py` -> PASS and now records `ghcr-standard-image` as `blocked run_id=23287211899`, `latest_run_matches_current_head=true`, `failed_step_name=Standard image publish preflight`
- `python3 scripts/governance/probe_remote_platform_truth.py --repo xiaojiou176-org/video-analysis-extract` -> PASS
- `python3 scripts/governance/check_remote_required_checks.py` -> PASS (18 checks)
- `python3 scripts/governance/check_open_source_audit_freshness.py` -> PASS
- `./bin/workspace-hygiene --apply` successfully removed `.venv` and transient `__pycache__` residue created by local verification, and the follow-up root/runtime/governance gates still PASS
- timed `./bin/full-stack up` experiment now shows: immediate and delayed `lsof` both confirm API and web listeners, while `status` still misread API before the local fix
- isolated web-only launches on ports `13125`, `13126`, and `13127` stay alive beyond 20s/50s with the same runtime workspace and env wrapper, so the remaining failure is more specific than “Next dev cannot run detached at all”

### Risk / Blocker Log

- `P0`: GHCR registry auth / packages write blocker remains the only non-local-closure lane
- `P0`: WS2 patch is ready locally, but remote workflow behavior cannot change until the workflow file is committed/pushed and rerun
- `P1`: deep-water English boundary not cut
- `P1`: platform policy may still be looser than repo-side gate posture
- `P1`: dirty worktree currently prevents any honest `current_workspace_verdict=pass` claim even if a fresh strict PASS receipt is captured in this run
- `P1`: dirty worktree still blocks `current_workspace_verdict=pass`, but the tracked diff in `apps/worker/tests/test_external_proof_semantics.py` is now validated rather than unknown
- `P1`: local capability lanes are green again; the remaining local fail-close condition is `dirty_worktree`

### Files Planned To Change

- `bin/repo-side-strict-ci`
- `bin/strict-ci`
- `scripts/ci/strict_entry.sh`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `.github/workflows/build-ci-standard-image.yml`
- `infra/config/strict_ci_contract.json`
- `config/governance/upstream-compat-matrix.json`
- `scripts/governance/check_governance_language.py`
- `scripts/governance/*` (English boundary / proof renderers as needed)
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/public-repo-readiness.md`

### Files Changed Log

- authoritative execution plan re-selected to the only surviving same-timestamp candidate
- stale `worktree=clean` claim removed from the authoritative plan and replaced with live dirty-worktree truth
- workstream status table added
- WS2 calibrated into readiness-first execution order
- WS3 calibrated into maintainer-surface-first execution order
- WS1 strict current receipt captured and current-proof artifacts refreshed; remaining repo-side blocker narrowed to `dirty_worktree`
- WS3 first batch landed in renderers and governance reference docs, and the corresponding docs/current-proof render+check chain still passes
- fresh governance re-run exposed a new stale-proof blocker in `WS5`, so the execution order must now consider receipt refresh work in parallel with blocked `WS2`
- bootstrap/full-stack/smoke reproduction narrowed `WS5` from a stale receipt into a concrete runtime bug family
- `scripts/runtime/full_stack.sh` was patched so API status detection no longer falsely requires `ROOT_DIR` in the API command line; `full-stack status` now reports the live API correctly
- `scripts/ci/prepare_web_runtime.sh` was fixed so its platform-aware native dependency check matches the actual optional package layout under `node_modules/lightningcss-darwin-arm64/...`
- `WS5` refresh work successfully pushed `smoke-full-stack` past short tests, through long tests, and back to a green smoke receipt on the current run
- after that refresh, the next stale-proof blocker shifted from RSSHub to `resend-digest-delivery-chain`
- `run-daily-digest` with `NOTIFICATION_ENABLED=true` produced a fresh `status=sent` Resend compatibility receipt
- `upstream-compat-matrix.json` now points at the fresh RSSHub and Resend run ids, clearing `upstream-same-run-cohesion`
- local `governance-audit` is green again after the provider freshness receipts were refreshed
- `build-ci-standard-image.yml` was patched locally to use `github.actor + GITHUB_TOKEN` for hosted login/preflight/SBOM registry auth, but this fix is still only local until commit/push
- `apps/worker/tests/test_supply_chain_ci_contracts.py` now asserts the hosted workflow uses the hosted-token path for login/preflight/SBOM auth
- `apps/worker/tests/test_external_proof_semantics.py` tracked diff was re-validated in isolation, so it is now part of the verified patch set rather than an unknown residue
- `external-lane-workflows.json` and `current-state-summary.md` were refreshed so WS2 now points at the latest current-head blocked run instead of the older one
- `workspace-hygiene --apply` is now a proven cleanup step after local verification loops that create `.venv` / `__pycache__`, and the repo still returns to green governance afterward
- `scripts/governance/check_governance_language.py` now acts as the first anti-regression gate for the maintainer-surface English hard cut
