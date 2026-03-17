# [🧭] Repo 终局总 Plan

## Header

- Plan ID: `2026-03-17_04-49-09__repo-ultimate-final-form-master-plan`
- Created At: `2026-03-17 04:49:09 PDT`
- Last Updated: `2026-03-17 06:20:00 PDT`
- Repo: `📺视频分析提取`
- Repo Path: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Current Execution Status: `Partially Completed`
- Current Phase: `Platform Boundary Hold - Repo-side executable work exhausted; remaining blockers are external/platform`
- Current Workstream: `WS3 (external boundary verified) / WS5`
- Active Plan Authority: `本文件是当前执行期唯一可信状态源；聊天总结、旧 Plan、脑内记忆都不得覆盖它`

## [一] 3 分钟人话版

这个仓库现在最危险的地方，不是“没有治理”，而是**治理看起来已经很像 Final Form，所以特别容易让人误以为它已经完工**。

你可以把它理解成一间制度极强的工厂：

- 门禁、巡检表、仓库分区、出货说明、外部合作名录都已经建好了
- 日常纪律甚至比很多成熟项目还严
- 但今天真正的“出厂大考”还没完全通过

当前最真实的状态，不是“烂尾”，也不是“已经闭环”，而是：

1. **Repo-side 治理总闸是真绿的**
   - `./bin/validate-profile --profile local` fresh PASS
   - `./bin/governance-audit --mode audit` fresh PASS
   - 说明根目录、runtime outputs、docs governance、logging contract、dependency boundaries、upstream governance、third-party notices 这些控制面是真接线

2. **repo-side strict 收据与 current-proof 证明面都已经 fresh 对齐**
   - `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 当前已拿到 fresh PASS 收据
   - `newcomer-result-proof.json` 当前为 `status=pass` 且 `repo_side_strict_receipt=pass`
   - `current-state-summary.md` 当前也已把 strict receipt 升为 first-class repo-side signal
   - 换句话说，WS1/WS2 当前都不是主 blocker，它们已经收口到可守护状态

3. **external lane 也还没闭环**
   - `remote-required-checks = pass`
   - `ghcr-standard-image = blocked(registry-auth-failure)`
   - `release-evidence-attestation = ready`
   - 也就是说，远端平台完整性比很多项目强，但“当前 HEAD 的外部分发闭环”并没有成立

4. **这个仓库最该硬切掉的，不是旧目录美观问题，而是 3 类假成熟信号**
   - 把 `governance-audit PASS` 当成 `repo-side done`
   - 把 `ready/public/generated/workflow exists` 当成 `verified/closed/current`
   - 把“代表性结果案例已经有文档”当成“用户结果证明已经自然进主链”

改完后，它要变成的正确形态不是“更好看”，而是：

- **repo-side strict lane 继续保持可信的终局收据**
- **current-proof surface 持续保持 strict receipt 的 first-class current truth**
- **external lane 要么 verified，要么明确 blocked/ready/historical**
- **用户结果证明和 AI failure honesty 真正进入主链，而不是停留在高级叙事层**

这条路线必须硬，因为如果继续靠“表面很成熟”往前走，接下来每一轮都会被同一种问题拖住：**到底哪些算真的完成，哪些只是看起来很像完成。**

## [二] Plan Intake

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <structured_issue_ledger>available</structured_issue_ledger>
  <input_material_types>
    - 超级Review 审计报告（上方输出，含 YAML 账本）
    - 当前 Repo docs/configs/scripts/workflows/tests/runtime reports
    - 既有仓库内 Plan（仅作历史输入，不作 current truth）
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
    - 这是强工程型 source-first applied AI mini-system
    - repo-side governance gate、strict receipt 与 current-proof surface 已对齐
    - external lane 仍被 GHCR 与 release current verification 卡住
    - 当前最大的风险已从 repo-side 证明面漂移，转向 external/platform 边界与 user-result 证明强度
  </initial_claims>
  <known_conflicts>
    - 旧记忆把 repo-side strict blocker 先后写成 host Docker / web build / runtime metadata；当前 fresh 严格收据已 PASS，这些都不再是当前 blocker
    - 文档与 generated surfaces 非常成熟；当前需要防的是 future drift，而不是 strict/current-proof 仍缺失
    - 仓库已 public，但 external distribution 与平台 security capability 仍未 current-verified
  </known_conflicts>
  <confidence_boundary>
    - repo docs/configs/scripts/runtime reports 属于高置信事实
    - GitHub live probe 与 gh run 查询属高置信外部事实，但仍是 2026-03-17 本轮快照
    - 输入 YAML 账本作为初始底稿，不自动视为已证实
    - Git upstream/fork 审计不适用；external upstream governance 审计适用
  </confidence_boundary>
</plan_intake>
```

### 输入材料范围

- 超级 Review 报告散文部分
- 超级 Review `## [十三、] 机器可读问题账本` YAML
- 当前仓库 fresh 验证命令与运行时收据
- 当前仓库中的现有计划文件：
  - `.agents/Plans/2026-03-17_01-54-18__repo-final-form-master-plan.md`
  - 更早的 four-track/governance execution plans

### 验证范围

- 根目录与 runtime 输出
- docs control plane 与 generated/current state surfaces
- repo-side strict lane、governance audit、newcomer proof
- public/open-source boundary
- external lane runtime artifacts 与 GitHub live state
- AI eval、AI failure honesty、user-result proof surfaces

### Repo archetype

- **Archetype：`hybrid-repo`**
- 理由：
  - 原生核心在 `apps/ + contracts/ + infra/`
  - 外部依赖通过 `config/governance/active-upstreams.json` 与 `upstream-compat-matrix.json` 进入治理主链
  - 不是单纯 glue repo，也不是纯 internal native repo

### 当前最真实定位

- **public source-first + limited-maintenance engineering repo**
- **强工程型 applied AI mini-system**
- **owner-level candidate 仓库**
- **未到 final-form 完工态**

### 最危险误判

- 把 `governance-audit PASS` 当成 repo-side 完成
- 把 `ready/public/generated/workflow exists` 当成 `verified/current/closed`
- 把 AI 路径“跑过了”当成失败语义已经诚实

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 / 含金量 | 强项目，接近 owner-level candidate | 强项目且终局收据闭环 | A | 是 | 长板真实，终局未收口 |
| Repo-side strict receipt | fresh PASS 且可重复 | 保持 PASS，并持续作为 current-proof first-class signal 被消费 | A | 是 | 已从 blocker 升为守护项 |
| Docs 事实源 | 强 SSOT，render/control plane 已接线 | 同步保持强，且 current-proof 不会失真 | A | 是 | 不应再扩 scope 做大改 |
| Current-proof 诚实性 | newcomer/current-state/runtime truth 已对齐 | current/head-aligned、fail-close、历史态降级明确并持续守护 | A | 是 | WS2 已验证完成 |
| 架构治理 | 强 | 保持强 | A | 是 | 不是当前主修对象 |
| 缓存 / 输出治理 | 强控制面，当前 fresh 收据已与 receipt/proof surface 对齐 | output 路径、freshness、receipt 语义一致并持续守护 | A | 是 | 以守护为主，不再是当前 blocker |
| 日志治理 | 强 | 保持强 | A | 是 | 用于保护，不作重构主战场 |
| 开源 readiness | 可谨慎公开审阅 | external lane current-verified 后再升级判断 | A | 是 | 先别夸大 adoption-grade |
| 平台安全能力 | 条件式诚实，但平台能力弱 | public docs 与平台 live capability 口径完全一致 | A | 是 | third priority 后半段 |
| external lane | required checks 绿，GHCR blocked，release only ready | current HEAD external verified or explicit blocked policy | A | 是 | 第三主路线 |
| Git upstream/fork 健康 | 不适用 | 维持 N/A | A | 否 | 仅有 `origin` |
| external upstream 治理 | 强 | 保持强 | A | 是 | 不是当前破局点 |

## [四] 根因与完成幻觉总表

### 根因压缩

本轮把上游 YAML 账本、散文审计和 repo fresh 验证压缩后，当前还剩 **4 个真正要动刀的根因**：

1. **repo-side strict current receipt 已存在，但 current-proof / done-signal surfaces 还没有把它升格成唯一正式事实**
2. **external lane current verification 还没闭环，但 public/open-source narrative 已经足够强，容易被误读**
3. **AI / user-result 证明链的“真实能力”还弱于治理证明链**
4. **强控制面已经很成熟，后续修复若不受约束，最容易引入回潮型伪修复**

### 根因 / 幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `governance PASS = repo-side done` 幻觉 | `governance-audit` fresh PASS、docs 很整齐 | repo-side strict receipt 虽已 fresh PASS，但 current-proof surface 还可能落后 | WS2 | `repo-side-strict-ci` current receipt 必须进入 newcomer/current-state summary |
| strict lane 不可信幻觉 | 旧 blocker 记忆仍指向 strict lane 红 | freshest quality summary 与 strict log 已 PASS | WS1 守护 + WS2 同步 | `quality-gate/summary.json` + strict log + newcomer proof 一致 |
| external lane 成熟幻觉 | workflow 存在、SBOM/attest 存在、仓库 public | GHCR blocked、release only ready、workflow success is historical | WS3 | `current-state-summary.md` + workflow head alignment + readiness gate |
| docs current-state 幻觉 | generated docs 看起来完整 | tracked docs 只能讲规则，不能代替 runtime current truth | WS2 | `check_docs_governance.py` + `check_current_proof_commit_alignment.py` |
| 开源安全能力幻觉 | `SECURITY.md` 存在 | GitHub live capability 未成熟，private reporting 未获 current 正向证明 | WS3 | live repo API probe + public boundary docs |
| AI 产品化幻觉 | eval、computer-use、MCP、API 都存在 | failure honesty 与 user-result proof 还没成为最强 current proof | WS4 | eval regression + newcomer/result proof + semantic tests |

### 最贵 / 最伤 / 最易误判

| 维度 | 当前判断 |
| --- | --- |
| 最贵根因 | current-proof 与 done-signal surfaces 滞后于 fresh strict receipt |
| 最制造完成幻觉的根因 | current-proof 与 done-signal surfaces 混用 |
| 最伤长期维护的根因 | public/external/current/history 语义边界不够 fail-close |
| 最影响招聘信号的根因 | user-result proof 弱于治理 proof |
| 最影响开源判断的根因 | GHCR/release/security capability 仍非 current-verified |

## [五] 绝不能妥协的红线

- **红线 1：不得再用 `governance-audit PASS` 直接声明 repo-side done。**
- **红线 2：不得再把 `ready`、`historical success`、`public`、`workflow exists` 写成 `verified/current/closed`。**
- **红线 3：不得再允许 canonical strict path 因 temp-dir、worktree hygiene 这类 repo-owned 细节自爆。**
- **红线 4：不得再让用户结果证明弱于治理证明。**
- **红线 5：不得为兼容旧叙事保留长期“双口径”说明。**
- **红线 6：不得新增任何新的顶级输出路径、repo-root 私有环境路径、源码树运行态路径。**
- **红线 7：不得把 AI fallback/noop/stub 的非真实执行继续包装成 `ok`。**

## [六] Workstreams 总表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| WS1 | `Verified` | P0 | L1 + repo-owned gate path | 校准 fresh strict 事实：`quality-gate/summary.json=result=passed`，strict log `event=complete,message=PASS`，并重渲 `newcomer-result-proof` 为 `repo_side_strict_receipt=pass` | 作为守护项保留；若 strict 再红，立即回切 WS1 | `repo-side-strict-ci` current receipt 已拿到 |
| WS2 | `Verified` | P0 | L1 | 已修复 `render_newcomer_result_proof.py` 的 latest-completed strict receipt 语义；`current-state-summary` 已把 strict receipt 升为 first-class signal；docs wording 已对齐 | 转入守护项；若 current-proof surface 再落后，立即回切 WS2 | `newcomer-result-proof PASS`、`current-proof-commit-alignment PASS`、`docs governance PASS`、`governance-audit PASS` |
| WS3 | `Verified` | P1 | L1 | 已把 current HEAD external workflows 推进并写回 runtime truth：`release-evidence-attestation` 现已 current HEAD verified，`ghcr-standard-image` 已在 current HEAD 失败，失败签名收敛到 GHCR blob HEAD request `403 Forbidden`；本地 GHCR readiness 同样 blocked，平台 security capability 仍未启用 | 保留为平台边界结论；除非拿到新权限/平台能力，不再在 Repo 内空转 | `release workflow verified`、`ghcr workflow blocked(current HEAD failure)`、`local GHCR readiness blocked`、`GitHub security capability disabled/null` |
| WS4 | `Verified` | P1 | L1 | 已把 representative result proof pack 接回 newcomer/value-proof surfaces，并补了 3 个稳定 case id；AI failure honesty targeted tests fresh PASS | 转入守护项；若 proof pack 与 newcomer surface 再脱节，立即回切 WS4 | `newcomer-result-proof PASS`、`docs governance PASS`、AI targeted tests `38 passed` |
| WS5 | `Active Guard` | P2 | L1 | 持续保持 root/runtime/docs/logging/upstream control planes 不被顺手破坏 | 在全部执行过程中防止回潮 | 强控制面当前保持 PASS |

## [七] 详细 Workstreams

### WS1. Repo-side Strict Lane Reliability Hard Cut

#### 目标

把 `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 从“结构上很正确，但 fresh 仍会因为自身执行链失真而红”推进到“可以作为唯一 canonical repo-side strict current receipt”。

#### 为什么它是结构性动作

因为当前最大的误判源，不是业务代码，而是**测量仪器本身**。  
只要 strict lane 还会被 repo-owned temp-dir/worktree hygiene 绊倒，所有“repo-side done”结论都不可靠。

#### 输入

- [scripts/governance/quality_gate.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/quality_gate.sh)
- [scripts/ci/web_test_build.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/web_test_build.sh)
- [apps/web/vitest.config.mts](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/web/vitest.config.mts)
- [.runtime-cache/reports/governance/quality-gate/summary.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/governance/quality-gate/summary.json)

#### 输出

- strict lane 的 Web unit coverage temp tree 稳定存在
- strict lane 的 contract diff local gate 可重复执行，不受 stale registered worktree 污染
- fresh strict receipt 产出

#### 改哪些目录 / 文件 / 配置 / gate

| 对象 | 动作 |
| --- | --- |
| `apps/web/vitest.config.mts` | 明确 coverage runtime temp root 的目录存在契约；不要依赖工具隐式创建 `.tmp/` |
| `scripts/ci/web_test_build.sh` | 在跑 `npm run test:coverage` 前显式创建 `.runtime-cache/tmp/vitest-coverage` 及其子目录，必要时先清理旧残留 |
| `scripts/governance/quality_gate.sh` | 在 `run_contract_diff_local_gate()` 中对 `.runtime-cache/tmp/contract-diff-local/base-tree` 做 `git worktree prune`/安全 remove/路径重建，确保 stale registration 不会制造假红 |
| `scripts/runtime/workspace_hygiene.sh` | 仅在需要时补充 strict-temp hygiene，不把 repo-side long-lived receipt 误删 |
| `.runtime-cache/reports/governance/quality-gate/summary.json` | 保持为 canonical strict failure/success summary，不再让临时 stderr 成为唯一事实源 |

#### 删除哪些旧结构

- 删除“默认假设工具自己会建好 temp-dir”的隐式约定
- 删除“contract-diff-local/base-tree 可以长期复用”的隐式约定

#### 迁移桥

- 允许在 `quality_gate.sh` 内增加一次性 stale worktree 自清理桥
- 允许在 Web unit gate 内增加 repo-owned temp tree bootstrap 桥

#### 兼容桥删除条件与时点

- 当 strict lane 连续 3 次在 clean workspace 上 fresh PASS，且不再出现 temp-dir/worktree 假红时
- 删除任何仅用于兼容历史残留路径的分支判断

#### Done Definition

- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` fresh PASS
- `.runtime-cache/reports/governance/quality-gate/summary.json` 的 `result = passed`
- newcomer/result surfaces 能读取到 fresh strict receipt

#### Fail Fast 检查点

- Web unit tests 通过后仍出现 coverage temp `ENOENT` -> 立即停，先修 temp root
- contract diff gate 再次出现 registered stale worktree -> 立即停，先修 worktree lifecycle

#### 它会打掉什么幻觉

- “绝大多数 gate 都绿了，所以 strict 也差不多绿了”

#### 它会改变哪个上层判断

- 把“半靠谱偏强”推进到“repo-side 可信完成”

---

### WS2. Current-Proof / Done-Signal Hard Cut

#### 目标

让仓库里所有对“当前状态 / 完成状态 / repo-side done / external done”的表达，统一只消费 fresh current truth，不再允许轻量 gate、历史收据、ready 状态冒充终局收据。

#### 为什么它是结构性动作

因为当前最大的治理问题不是缺文件，而是**语义污染**。  
如果 current-proof 和 done-signal 语义不硬切，哪怕 WS1 修完，后面还会重复出现“到底这算不算 done”的争论。

#### 输入

- [scripts/governance/render_current_state_summary.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_current_state_summary.py)
- [scripts/governance/render_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_newcomer_result_proof.py)
- [scripts/governance/check_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_newcomer_result_proof.py)
- [scripts/governance/check_current_proof_commit_alignment.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_current_proof_commit_alignment.py)
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)

#### 输出

- `current-state-summary`、`newcomer-result-proof`、`README/start-here` 对 done state 的语义完全一致
- repo-side done 只接受 fresh strict receipt + governance receipt 的组合
- external lane 的 `ready/historical/verified/blocked` 语义只按 runtime artifact 读取

#### 改哪些目录 / 文件 / 配置 / gate

| 对象 | 动作 |
| --- | --- |
| `scripts/governance/render_current_state_summary.py` | 明确把 repo-side strict current receipt 暴露成 first-class field，不让读者只看到 governance 绿 |
| `scripts/governance/render_newcomer_result_proof.py` | 把 strict current receipt、governance receipt、eval regression、current proof alignment 统一压成 newcomer 入口语义 |
| `scripts/governance/check_newcomer_result_proof.py` | 提高要求：当 repo-side strict receipt 缺失时，报告必须显式降级，不允许模糊 partial 成功文案 |
| `docs/reference/done-model.md` | 明确终局口径：repo-side done = governance + strict current receipt；external done = current HEAD external verified |
| `README.md`, `docs/start-here.md`, `docs/reference/external-lane-status.md` | 移除任何会让轻量 PASS 冒充终局 PASS 的措辞 |

#### 删除哪些旧结构

- 删除“governance green 即 repo-side green”的隐式叙事
- 删除“current-state 只看 tracked docs 就够了”的旧阅读习惯

#### 迁移桥

- 保留 `docs/generated/external-lane-snapshot.md` 作为 pointer page
- 但不再允许它承载 current verdict payload

#### 兼容桥删除条件与时点

- 当所有入口文档都只指向 runtime-owned current truth 且 current-proof alignment 持续 PASS

#### Done Definition

- newcomer/current-state/readme 对 done 语义零冲突
- `check_current_proof_commit_alignment.py` 持续 PASS
- 任意一条 current-state claim 都能回落到同 HEAD runtime artifact

#### Fail Fast 检查点

- 任何入口文档再次直接声称 external/current verified 而未指向 runtime artifact -> 立即停
- newcomer proof 再次能在 strict receipt 缺失时产出暧昧正向结论 -> 立即停

#### 它会打掉什么幻觉

- “绿过一次 / 有个 generated 页面 / 有个 readiness json，就等于今天已经完成”

#### 它会改变哪个上层判断

- 把“文档看起来很诚实”推进到“done signal 语义真的诚实”

---

### WS3. External Lane / Public Truth Closure

#### 目标

把 external lane 从“public repo + workflows + readiness + 历史成功”推进到“current HEAD external verified or explicit blocked/historical truth”。

#### 为什么它是结构性动作

因为 open-source / public 判断最大的误判源，不在 LICENSE，而在**外部分发与平台能力会被自然高估**。

#### 输入

- [scripts/ci/check_standard_image_publish_readiness.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/check_standard_image_publish_readiness.sh)
- [.github/workflows/build-ci-standard-image.yml](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.github/workflows/build-ci-standard-image.yml)
- [.github/workflows/release-evidence-attest.yml](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.github/workflows/release-evidence-attest.yml)
- [.runtime-cache/reports/governance/standard-image-publish-readiness.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/governance/standard-image-publish-readiness.json)
- [.runtime-cache/reports/release/release-evidence-attest-readiness.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.runtime-cache/reports/release/release-evidence-attest-readiness.json)
- [SECURITY.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/SECURITY.md)
- [docs/reference/public-repo-readiness.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/public-repo-readiness.md)

#### 输出

- GHCR lane 若未闭环，保持 blocked 且解释清晰
- release evidence 若未 current-verified，保持 ready/historical，不再被误讲成 done
- public/open-source docs 与 GitHub live capability 完全同口径

#### 改哪些目录 / 文件 / 配置 / gate

| 对象 | 动作 |
| --- | --- |
| `scripts/ci/check_standard_image_publish_readiness.sh` | 把 write-capable token path、package probe、actor-sensitive truth 继续收紧为唯一外部镜像 readiness 入口 |
| `.github/workflows/build-ci-standard-image.yml` | 保持 current HEAD publish/attest 主路径明确，必要时增加失败摘要落盘，避免只看 workflow conclusion |
| `.github/workflows/release-evidence-attest.yml` | 确保 current HEAD / current tag / current artifact 的对齐关系明确可验 |
| `SECURITY.md` | 维持 capability-conditioned wording，不允许暗示 live PVR 一定存在 |
| `docs/reference/public-repo-readiness.md` | 明确 public source-first != adoption-grade |

#### 删除哪些旧结构

- 删除“workflow exists = capability exists”的暗示性叙事
- 删除“ready = verified”的任何口径

#### 迁移桥

- 允许保留 blocked/ready/historical 这三种中间态
- 不允许跳过它们直接宣称 closed

#### 兼容桥删除条件与时点

- 当前 HEAD 拿到 GHCR current verified + release evidence current verified 后
- 再考虑把 public posture 从“谨慎公开审阅”上调

#### Done Definition

- GHCR lane current verified 或显式长期 optional policy 被正式写入
- release evidence current verified
- public security/open-source wording 与 GitHub live capability 无冲突

#### Fail Fast 检查点

- GHCR readiness 再次靠历史 workflow 成功冒充 current -> 立即停
- security docs 再次暗示 private reporting 一定 live 可用 -> 立即停

#### 它会打掉什么幻觉

- “public + LICENSE + workflow = 已经成熟开源”

#### 它会改变哪个上层判断

- 把“可公开审阅”推进到“更可公开消费”

---

### WS4. User-Result Proof / AI Failure Honesty Mainline

#### 目标

让仓库的 strongest proof 不再只是治理证明，还要有**代表性用户结果证明**和**AI 失败诚实度证明**。

#### 为什么它是结构性动作

因为这个仓库的高含金量来自“结果可复核、失败可解释”。  
如果最终 strongest proof 永远只是 governance pass，那招聘信号和产品化信号都会被打折。

#### 输入

- [docs/reference/value-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/value-proof.md)
- [docs/proofs/task-result-proof-pack.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/proofs/task-result-proof-pack.md)
- [scripts/governance/render_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/render_newcomer_result_proof.py)
- AI failure semantics 相关实现与测试：
  - `apps/api/app/services/computer_use.py`
  - `apps/worker/worker/pipeline/steps/llm_*`
  - 相关 worker/api tests

#### 输出

- newcomer/result proof 不再只是“预检 + gate receipt”，还包含 representative result proof 引用
- AI failure honesty 在主链解释中清楚表达 `unsupported/degraded/failed`
- `value-proof` 与 current representative proof 不再脱节

#### 改哪些目录 / 文件 / 配置 / gate

| 对象 | 动作 |
| --- | --- |
| `scripts/governance/render_newcomer_result_proof.py` | 在不污染 newcomer 入口的前提下，增加 representative proof pointers |
| `docs/proofs/task-result-proof-pack.md` | 收口为 canonical human-readable proof pack |
| `docs/reference/value-proof.md` | 只保留高价值解释，不承担 current verdict |
| AI semantic tests | 锁死 fallback/noop/unsupported/degraded 的真实语义，不回退到 `ok` |

#### 删除哪些旧结构

- 删除“AI 路径存在”即可当产品化成立的浅层证明
- 删除“只靠治理和 eval 文档讲强”的单薄叙事

#### 迁移桥

- 允许 first version 的 proof pack 只覆盖 2-3 条代表链路
- 不要求一口气做成大而全 case library

#### 兼容桥删除条件与时点

- 当 representative proof pack 与 newcomer/current-state surfaces 已稳定接线

#### Done Definition

- 至少 2-3 条 representative user-result proofs 有 current-aligned pointers
- AI semantic tests 明确保护 failure honesty
- value-proof 不再承担 current verdict 职责

#### Fail Fast 检查点

- 如果 proof pack 开始承载 current verdict payload -> 立即停，转回 pointer 模式

#### 它会打掉什么幻觉

- “治理强 = 用户结果强”

#### 它会改变哪个上层判断

- 把“强工程仓”推进到“更强产品化仓”

---

### WS5. Strong Control Plane Preservation

#### 目标

在前四个主 Workstreams 改造期间，保持已经很强的控制面不被顺手破坏。

#### 为什么它是结构性动作

因为这个仓库的长板很稀缺：  
docs control plane、root/runtime governance、logging contract、upstream governance、public boundary 都已经很像成熟基础设施。  
主路线不是重做它们，而是**保护它们不被返工伤到**。

#### 输入

- `config/docs/*`
- `config/governance/*`
- docs governance / root allowlist / runtime outputs / logging / upstream 相关 checks

#### 输出

- 所有强控制面保持 PASS
- 不为修 strict lane 引入新的顶级项、新输出路径、新 current-state tracked payload

#### 改哪些目录 / 文件 / 配置 / gate

| 对象 | 动作 |
| --- | --- |
| `config/docs/*` | 只允许最小必要变更 |
| `config/governance/*` | 不新增宽松例外；新增必须有可解释治理含义 |
| `.gitignore` / runtime hygiene | 继续禁止源码树运行态 |
| docs/current-state renderers | 继续保持 tracked rules vs runtime truth 分离 |

#### 删除哪些旧结构

- 禁止新增“为方便排障临时放宽”的长期 allowlist
- 禁止新增 repo-root 输出路径

#### 迁移桥

- 仅允许短期、显式、可删除的执行桥

#### 兼容桥删除条件与时点

- 对应 blocker 修完立即删

#### Done Definition

- 前四个主 Workstreams 收口后，强控制面仍 fresh PASS

#### Fail Fast 检查点

- 任何修复若要求放宽 root/runtime/docs truth boundary -> 立即停，重新设计

#### 它会打掉什么幻觉

- “为了快速修 blocker，可以先放宽治理，回头再补”

#### 它会改变哪个上层判断

- 保住本仓最值钱的长期维护优势

## [八] 硬切与迁移方案

### 立即废弃项

| 对象 | 废弃原因 | 执行动作 |
| --- | --- | --- |
| “`governance-audit PASS` = repo-side done”说法 | 造成最大完成幻觉 | 在 docs/current-state/newcomer surfaces 中硬切 |
| implicit Vitest temp-dir existence | 导致 strict lane 假红 | 显式创建并验证 temp tree |
| stale registered contract-diff worktree | 导致 contract gate 假红 | 在 gate 前 prune/remove/recreate |
| 任何把 `ready/public/generated/historical success` 写成 `verified/current/closed` 的文案 | 造成 public/external 幻觉 | 统一 hard cut |

### 迁移期兼容桥

| 兼容桥 | 允许原因 | 删除条件 |
| --- | --- | --- |
| contract-diff stale worktree 自清理桥 | 修复历史残留，不改 contract gate 语义 | strict lane 连续 3 次 clean workspace PASS |
| newcomer proof 中保留 `missing_current_receipt` 状态 | 允许真实表达未闭环中间态 | fresh strict receipt 持续可得 |
| external lane 保留 `ready/historical/blocked` | 防止假宣布完成 | current HEAD external verified |

### 禁写时点

- 从本 Plan 生效起：
  - **禁止新增新的 tracked current-state payload docs**
  - **禁止新增新的 repo-root 私有环境路径**
  - **禁止新增新的源码树运行态默认路径**

### 只读时点

- 在 WS1 开始后：
  - `docs/generated/external-lane-snapshot.md` 永久只读为 pointer page

### 删除时点

- WS1 完成后：删掉任何用于兼容旧 strict temp/worktree 生命周期的临时 hack 分支
- WS2 完成后：删掉 docs 中所有能把轻量 gate 冒充终局 gate 的句子
- WS3 完成后：删掉 external lane 里任何 historical success 被 current narrative 引用的残留

### 防永久兼容机制

- 每个兼容桥必须：
  - 有单独 ID
  - 有删除条件
  - 有删除时点
  - 有对应 gate
- 未满足上述四项的兼容桥，一律视为禁止

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| 项目定位是否与真实能力对齐 | README / positioning / done-model 与 current-state 一致 | `python3 scripts/governance/check_docs_governance.py` + 人工 spot check | 入口文档不再混淆 repo-side 与 external | 叙事仍在制造完成幻觉 |
| repo-side strict 是否真实闭环 | canonical strict command | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | fresh PASS | 不能宣称 repo-side done |
| governance control plane 是否保持强 | governance audit | `./bin/governance-audit --mode audit` | fresh PASS | 强控制面被破坏 |
| root allowlist 是否强制 | root gate | `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | PASS | repo-root 私有态复发 |
| runtime outputs 是否合法 | runtime-output gate | `python3 scripts/governance/check_runtime_outputs.py` | PASS | 源码树 / 非法路径又承载运行态 |
| cache 全删可重建是否成立 | runtime cache maintenance | `python3 scripts/governance/check_runtime_cache_retention.py` + `check_runtime_cache_freshness.py` | PASS | 历史 artifacts 仍能冒充 current |
| 日志 schema / correlation 是否成立 | logging contract | `python3 scripts/governance/check_logging_contract.py` | PASS | 日志对诊断失去价值 |
| docs 是否是真事实源 | docs governance | `python3 scripts/governance/check_docs_governance.py` | PASS | render-only/manual boundary 漂移 |
| current-proof 是否 head-aligned | current proof gate | `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS | tracked/runtime state 仍可能说旧 truth |
| newcomer/result proof 是否诚实 | newcomer gate | `python3 scripts/governance/check_newcomer_result_proof.py` | PASS | 新手入口仍会误导当前完成状态 |
| external lane 是否 current-verified | GHCR/release/workflow head alignment | `.runtime-cache/reports/governance/current-state-summary.md` + live `gh run`/repo API | 仅 verified 才可宣称闭环 | external lane 仍只是准备态或历史态 |
| public surface / secrets / license / provenance 是否达标 | notices/public boundary/security wording | `THIRD_PARTY_NOTICES.md` render check + public docs review + live repo API | 文档与 live capability 无冲突 | 开源 readiness 仍被高估 |
| dependency boundary / upstream governance 是否成立 | upstream gates | `python3 scripts/governance/check_upstream_governance.py` + `check_dependency_boundaries.py` | PASS | 外部依赖治理被破坏 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| Phase A | 锁死主路线范围，不再扩大战场 | 本 Plan 生效 | 串行 | 新增动作只允许服务于 WS1-WS5 | 范围漂移 |
| Phase B | 执行 WS1 strict lane reliability hard cut | 无 | 串行优先 | fresh strict PASS | 若先改 docs/external，仍会被 strict 红灯打回 |
| Phase C | 执行 WS2 done-signal/current-proof hard cut | WS1 至少能稳定产出 strict receipt | 可与 WS4 部分并行 | newcomer/current-state/readme 语义统一 | 若先改叙事但没有 receipt，会形成新一轮空口号 |
| Phase D | 执行 WS3 external/public truth closure | WS2 done 语义已统一 | 串行优先 | external lane 不再被 ready/historical 偷换 | 若先做 public 提升，会过度承诺 |
| Phase E | 执行 WS4 user-result proof / AI honesty mainline | WS1、WS2 已基本稳定 | 可并行 | result proof 进入主链 | 若先做，可能又被 current-proof 语义污染 |
| Phase F | 执行 WS5 preservation sweep | 所有阶段全程 | 并行守护 | 强控制面持续 PASS | 顺手修复引入治理退化 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| 修复 strict lane 的 Vitest temp-dir 与 contract-diff worktree | 把“半靠谱偏强”改成“repo-side 真靠谱” | 终局收据终于可信 |
| 把 strict receipt 升级为 newcomer/current-state 的 first-class verdict | 把“文档很诚实”改成“完成信号真诚实” | 轻量 PASS 不再冒充 done |
| 关闭 GHCR blocked / release only ready 的外部分发缺口 | 把“可公开看”改成“更可公开消费” | external lane 当前 HEAD 真闭环 |
| 把 user-result proof mainline 化 | 把“强工程仓”改成“更强产品化仓” | strongest proof 不再只是治理 proof |
| 维持强控制面不退化 | 把“本轮修好了”改成“长期维护税没上升” | 不为修 blocker 伤到底盘 |

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 WS1：strict lane reliability hard cut

**为什么先做**

- 这是 freshest repo-side blocker
- 它决定所有后续 done claim 是否可信
- 不修它，所有文档/外部叙事都只是更漂亮的“未完工说明书”

**它打掉的幻觉**

- “governance 绿了，所以 repo-side 差不多也绿了”

**它释放的能力**

- fresh canonical strict receipt
- true repo-side done judgment

### 2. 再做 WS2：current-proof / done-signal hard cut

**为什么第二**

- WS1 修的是事实
- WS2 修的是事实的表达
- 先有正确事实，再有正确叙事，顺序不能倒

**它打掉的幻觉**

- “ready / generated / historical success 也能讲成 current closure”

**它释放的能力**

- newcomer/current-state/readme 同口径
- repo-side vs external lane 无争议表达

### 3. 然后做 WS3：external/public truth closure

**为什么第三**

- external lane 当前仍 blocked/ready/historical
- 但在 repo-side strict 未站稳前，先冲 external 只会放大噪音

**它打掉的幻觉**

- “public repo + workflow + attestation = 已成熟开源分发”

**它释放的能力**

- 更真实的 open-source/public posture
- 更可信的 release/distribution judgment

## [十三] 不确定性与落地前核对点

### 高置信事实

- `validate-profile` fresh PASS
- `governance-audit` fresh PASS
- `repo-side-strict-ci` fresh FAIL
- strict 失败点是 `web_unit_tests` temp-dir `ENOENT` 与 `contract_diff_local_gate` stale registered worktree
- external lane 现状为 `remote-required-checks=pass`, `ghcr-standard-image=blocked`, `release-evidence-attestation=ready`
- Git upstream/fork 不适用

### 中置信反推

- 修复 WS1 后，repo-side done judgment 会显著上升  
  这是高概率，但仍需 fresh rerun 验证
- 修复 WS3 后，open-source posture 可从“谨慎公开审阅”提升  
  仍取决于平台权限与 current HEAD external verification

### 落地前二次核对点

- WS1 落地前核对 `Vitest` 对 reportsDirectory/.tmp 的真实创建语义，避免打无效补丁
- WS1 落地前核对 `git worktree prune/remove` 在当前本地环境的安全用法，避免误删正常 worktree
- WS3 落地前核对当前 GitHub token / GHCR token 的真实作用域和 package ownership

### 但不得因此逃避完整 Plan

本 Plan 已默认采用唯一主路线：

- **先修 strict lane**
- **再修 done-signal/current-proof**
- **再修 external/public truth**
- **最后把 user-result/AI honesty 拉上主链**

不存在保守路线/激进路线二选一。

## [十四] 执行准备状态

### Current Status

- `validate-profile`：PASS
- `governance-audit`：PASS
- `repo-side-strict-ci`：PASS（fresh strict current receipt 已拿到）
- `current-state-summary`：可读且 head-aligned
- `newcomer-result-proof`：PASS，且 `repo_side_strict_receipt=pass`
- external lane：GHCR image workflow 对当前 HEAD 已失败并留下 403 证据，release attestation 对当前 HEAD 已 verified，本地 GHCR readiness 仍 blocked
- Git closure：当前所有有效脏改动已保全提交并推送到 `origin/main`，本地 `main...origin/main = 0 0`
- 当前主战场：**无新的 Repo-side blocker；当前已抵达外部平台边界，WS5 继续守护**

### Task Checklist

- `[x]` 接管最新 Plan，并将其确立为唯一可信状态源
- `[x]` 校准 Plan 与 Repo 当前状态，确认 WS1 的 strict receipt 已真实存在
- `[x]` 重新渲染并验证 newcomer/result proof，使其追平 strict current receipt
- `[x]` 将 strict current receipt 升格进 current-state-summary 与 done-signal surfaces
- `[x]` 统一 README / start-here / done-model / external-lane-status 的 current truth 语义
- `[x]` 校准 external/public truth surfaces，确认 Repo 侧已基本诚实，剩余主要是平台阻塞
- `[x]` 把 representative user-result proof 拉上主链
- `[x]` 将当前 main 上全部有效脏改动保全为提交并推送到 `origin/main`
- `[-]` 持续守护 WS5：防止修复过程破坏现有强控制面

### Next Actions

1. 若平台条件变化，优先重开 WS3：GHCR write-capable token / package permission / GitHub security capability
2. 若继续纯 Repo-side推进，优先执行 WS5 守护与同类 drift 复核，不新增无意义表层改动
3. 下一轮任何执行前，先读本 Plan 当前状态，不得回退到“WS1/WS2 仍红”或“release 仍仅 ready”的旧叙事

### Decision Log

- 采用唯一主路线：strict receipt first
- 不把 Git upstream/fork 作为本仓工作流的一部分
- 不为“更好看”而重构强控制面
- 不把 ready/public/generated 当作可汇报的完成信号
- 2026-03-17 05:02 PDT：校准 Repo 当前状态后，确认 WS1 在 Repo 事实层已经完成；Plan 必须追认 strict receipt，而不能继续按旧 blocker 叙事执行
- 2026-03-17 05:02 PDT：将主战场从“修 strict lane”切换为“修 current-proof / done-signal surfaces”，因为当前最大的偏差已变成证明面落后于真实能力
- 2026-03-17 05:11 PDT：再次校准后，确认 WS2 的具体 blocker 已收敛为 renderer 语义错误：`render_newcomer_result_proof.py` 使用 latest strict manifest，而不是 latest completed strict receipt；只要新的 strict run 尚未写入 PASS completion，就会把已存在的 strict PASS 收据重新压回 `missing_current_receipt`
- 2026-03-17 05:24 PDT：WS2 已完成并验证：`render_newcomer_result_proof.py` 现在优先消费 latest completed strict receipt，`current-state-summary` 已把 strict receipt 升为 first-class repo-side signal，入口文档 wording 也已与 fresh runtime truth 对齐
- 2026-03-17 05:32 PDT：WS3 已完成 repo-side 可完成部分验证：GHCR 仍被 `no token path with packages write capability detected` 阻塞，release evidence 仍是 READY，GitHub live probe 显示 private vulnerability reporting 仍无正向启用证明；当前剩余项主要是平台/权限阻塞，不再空转 WS3
- 2026-03-17 05:45 PDT：WS4 已完成并验证：`newcomer-result-proof.json` 现在带 `representative_result_proof_pack` 与 3 个稳定 `representative_result_cases`；`task-result-proof-pack.md` 已显式标出 case id；`value-proof.md` 与 newcomer 文档已讲清“当前收据”和“代表性案例”的搭配阅读规则；AI failure honesty targeted tests fresh 通过
- 2026-03-17 05:50 PDT：reviewer 指出 Plan 的 [一]/[三] 高层摘要仍残留旧的 WS1/WS2 红灯表述；已按 runtime truth 回写修正，确保高层摘要、总览表与当前状态机一致
- 2026-03-17 05:58 PDT：WS3 再前推一层：已触发 current HEAD 的 `build-ci-standard-image` 与 `release-evidence-attest` workflows，并将其状态写回 runtime truth；当前 `release-evidence-attestation` 对 current HEAD 已 `verified`，`ghcr-standard-image` 对 current HEAD 已 `in_progress`
- 2026-03-17 06:08 PDT：WS3 已查到底：current HEAD 的 `build-ci-standard-image` workflow 最终失败在 step 8 `Build and push strict CI standard image`，失败签名为 GHCR blob `HEAD request ... 403 Forbidden`；`release-evidence-attestation` 对 current HEAD 保持 verified。当前剩余项已收敛为平台/权限边界，而不是 Repo 内待改逻辑
- 2026-03-17 06:20 PDT：已执行 Git 收口保全：当前 main 上全部有效脏改动已提交为 `a507a0f` (`chore(governance): land repo-side closure state`) 并推送到 `origin/main`；本地 `main...origin/main` 为 `0 0`，工作区已清空到只剩本次收口记账提交待落盘

### Validation Log

- `./bin/validate-profile --profile local` fresh PASS
- `./bin/governance-audit --mode audit` fresh PASS
- `.runtime-cache/reports/governance/quality-gate/summary.json` 当前 `result=passed`
- `.runtime-cache/logs/governance/55d7de9cc25f4b22b4fdbe7f3a1dbad8.jsonl` 含 `event=complete,message=PASS`
- `.runtime-cache/logs/governance/7a9a13f2db3c4f6e9ebbbd6918e8778c.jsonl` 含 `event=complete,message=PASS`
- `python3 scripts/governance/render_newcomer_result_proof.py` fresh 产出 `status=pass` 且 `repo_side_strict_receipt=pass`
- `python3 scripts/governance/render_current_state_summary.py` fresh 产出 Repo-side Signals：`newcomer-result-proof artifact=pass`、`repo-side-strict receipt=pass`
- `python3 scripts/governance/check_newcomer_result_proof.py` fresh PASS
- `python3 scripts/governance/check_current_proof_commit_alignment.py` fresh PASS
- `python3 scripts/governance/check_docs_governance.py` fresh PASS
- `./bin/governance-audit --mode audit` 在 WS2 修改后 fresh PASS
- GitHub live probe on March 17, 2026 confirms current repo visibility and branch-protection truth
- `./scripts/ci/check_standard_image_publish_readiness.sh` fresh FAIL：`no token path with packages write capability detected`
- `python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag v0.1.0` fresh READY
- `gh api repos/xiaojiou176-org/video-analysis-extract | jq '{private_vulnerability_reporting,security_and_analysis}'` fresh 显示 `private_vulnerability_reporting=null` 且 security_and_analysis 多项 `disabled`
- `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT="$HOME/.cache/video-digestor/project-venv" uv run pytest apps/worker/tests/test_llm_computer_use_step.py apps/worker/tests/test_external_proof_semantics.py -q` fresh PASS（`38 passed`）
- `python3 scripts/governance/render_newcomer_result_proof.py && python3 scripts/governance/check_newcomer_result_proof.py && python3 scripts/governance/check_docs_governance.py` 在 WS4 proof-pack 接线后 fresh PASS
- `./bin/governance-audit --mode audit` 在 WS4 修改后 fresh PASS
- `gh workflow run build-ci-standard-image.yml --ref main` 成功触发 current HEAD run `23194567312`
- `gh workflow run release-evidence-attest.yml --ref main -f release_tag=v0.1.0` 成功触发 current HEAD run `23194567307`
- `gh run view 23194567312 --json jobs,conclusion,status,updatedAt,url` fresh 显示 current HEAD workflow `build-ci-standard-image` 失败于 step 8 `Build and push strict CI standard image`
- `gh run view 23194567312 --job 67399320549 --log-failed` fresh 显示最终失败签名：`failed to push ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard... unexpected status from HEAD request ... 403 Forbidden`
- `python3 scripts/governance/probe_external_lane_workflows.py` fresh 写回：`ghcr-standard-image=blocked`、`release-evidence-attestation=verified`
- `python3 scripts/governance/render_current_state_summary.py` fresh 写回：lane 总表已显示 `ghcr-standard-image=blocked`、`release-evidence-attestation=verified`
- `./bin/governance-audit --mode audit` 在外部 workflow 最终 truth 回写后 fresh PASS
- `git commit -m "chore(governance): land repo-side closure state"` 生成本地保全提交 `a507a0f`
- `git push origin main` 成功，将 `origin/main` 从 `362a7e4` 前推到 `a507a0f`
- `git rev-list --left-right --count main...origin/main` 当前为 `0 0`
- `git status --short --branch` 在本次记账前为干净 `## main...origin/main`

### Risk / Blocker Log

- Blocker 1: 无当前 repo-side blocker；WS1 旧 blocker 已被 fresh strict receipt 取代
- Structural 1: GHCR image lane 对 current HEAD 已明确失败，失败签名为 registry/blob `HEAD request ... 403 Forbidden`
- Structural 2: GitHub platform security capability 仍未 current-verified，不得被 `SECURITY.md` 文件存在本身补票
- Risk 1: current HEAD 的 release attestation 已 verified，但 GHCR image lane 仍 blocked；不得把 release verified 偷换成 external lane fully closed
- Risk 2: user-result proof 已上主链，但相较治理 proof 仍是代表性证明，不等于 adoption-grade 外部证明

### Files Changed Log

- `.agents/Plans/2026-03-17_04-49-09__repo-ultimate-final-form-master-plan.md`
- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- `.runtime-cache/reports/governance/current-state-summary.md`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `a507a0f`（`chore(governance): land repo-side closure state`）已将全部有效脏改动保全进 `main`
- `scripts/governance/render_newcomer_result_proof.py`
- `scripts/governance/render_current_state_summary.py`
- `scripts/governance/check_newcomer_result_proof.py`
- `README.md`
- `docs/reference/done-model.md`
- `docs/reference/newcomer-result-proof.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/value-proof.md`
- `docs/proofs/task-result-proof-pack.md`
- `docs/start-here.md`

### Files Planned To Change

- `.agents/Plans/2026-03-17_04-49-09__repo-ultimate-final-form-master-plan.md`（当前收口记账提交）
- `scripts/ci/check_standard_image_publish_readiness.sh`（仅当平台/权限条件变化后继续）
- `.github/workflows/build-ci-standard-image.yml`（仅当需要把平台 blocker 转成更强 repo-side readiness 诊断时）
- `.github/workflows/release-evidence-attest.yml`（仅当 external release verification 有继续推进条件时）
- `SECURITY.md`（仅当 GitHub 平台安全 capability 变化时继续）
- `docs/reference/public-repo-readiness.md`（仅当 public posture 需要跟平台事实继续收口时）
