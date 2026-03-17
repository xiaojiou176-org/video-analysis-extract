# [🧭] Repo 终局总 Plan

## Header

- Plan ID: `2026-03-17_01-54-18__repo-final-form-master-plan`
- Created At: `2026-03-17 01:54:18 PDT`
- Last Updated: `2026-03-17 11:10:00 PDT`
- Repo: `📺视频分析提取`
- Repo Path: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid`
- Current Execution Status: `Partially Completed`
- Current Phase: `WS1/WS2/WS4 landed; WS5 handler semantics landed; WS3 heavy receipt deeper rerun in progress`
- Active Plan Authority: `本文件是当前唯一可信执行状态源；旧 plans 只能作为历史输入，不得当 current truth`

## Header

- Plan ID: `2026-03-17_01-54-18__repo-final-form-master-plan`
- Created At: `2026-03-17 01:54:18 PDT`
- Last Updated: `2026-03-17 02:22:00 PDT`
- Repo: `📺视频分析提取`
- Repo Path: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid`
- Status: `IN_PROGRESS`
- Current Phase: `Phase 5 - Verification & Plan Reconciliation`
- Current Workstream: `WS3 gate-chain rebase / WS6 result-proof mainline`
- Source of Truth: `本文件是当前执行期唯一可信状态源；同会话旧 Plan 已降级为历史输入`

## [一] 3 分钟人话版

这个仓库现在最危险的问题，不是“没有治理”，而是**治理很强，但当前状态已经开始和自己的叙事脱节**。

你可以把它理解成一栋制度很完整的大楼：

- 楼层规划、门禁、巡检表、应急手册都很全
- 但今天现场仍然有几类不该出现的东西
- 而且外墙公告栏还在挂旧公告

当前最硬的现实已经收敛成下面这组更准确的状态：

1. **repo-side 根目录 / 源码树污染已经被推到 current fresh 绿**
   - `root-allowlist` 不再红在 `.venv`
   - `runtime-outputs` 不再红在 `apps/web/node_modules`
   - 说明“运行时产物必须离开源码树”已经从原则推进到了当前 workspace 的真实状态
2. **current-proof honesty 已经从 stale 状态页修成 tracked pointer + runtime truth**
   - `docs/generated/external-lane-snapshot.md` 不再承载 current verdict payload
   - current verdict 只从 `.runtime-cache/reports/**` 读取
   - 这相当于把“前台公告栏”改成“去看后台实时报表”，而不是继续贴旧公告
3. **AI feature 的 stub/noop 假成功语义已经在 handler 层被打掉**
   - `browser_stub` 现在返回 `degraded`
   - `no_op` 现在返回 `unsupported`
   - `playwright` 失败后的 fallback 不再伪装成真正执行成功
4. **repo-side canonical governance gate 已经 fresh 转绿，但 heavier receipt 还没补完**
   - `./bin/governance-audit --mode audit` 当前 fresh PASS
   - `newcomer-result-proof` 当前 fresh PASS
   - 但 `repo_side_strict_receipt` 仍是 `missing_current_receipt`
   - 这说明“厨房已经打扫干净”，但“更重那张毕业证”还没拿到

这份 Plan 的唯一主路线，就是把仓库从“治理强但当前状态不诚实”推进到“**repo-side 运行态干净、current-proof 不撒谎、AI 失败语义真实、结果证明能上主链**”。

这条路是**硬切路线**，不是修修补补路线。要被硬切掉的包括：

- 根目录 `.venv`
- 源码树 `apps/web/node_modules`
- checked-in 但失真的 current-state 文档
- `browser_stub/no_op` 返回 `ok` 的 AI 假成功语义
- 把 `ready`、`public`、`generated`、`有脚本` 误讲成“已经闭环”的叙事

---

## [二] Plan Intake

```xml
<plan_intake>
  <same_repo>true</same_repo>
  <input_material_types>
    - user-provided audit report 1: docs governance + ci governance
    - user-provided audit report 2: open-source readiness governance
    - user-provided audit report 3: architecture/cache/logging/root/upstream governance
    - user-provided audit report 4: high-signal personal project / AI feature audit
    - existing in-repo plan under .agents/Plans/
    - current repo docs/configs/scripts/workflows/runtime reports/tests
  </input_material_types>
  <validation_scope>
    - repo structure
    - root governance
    - runtime-output policy
    - docs control plane
    - governance gates
    - AI eval assets and regression
    - worker AI step implementation and tests
    - public/open-source boundary docs
    - remote/runtime evidence surfaces
  </validation_scope>
  <initial_claims>
    - repo is a strong hybrid-repo with high-maturity governance
    - repo-side gates are not fully green
    - current-state docs may be stale versus runtime truth
    - external GHCR lane remains blocked
    - AI feature is stronger than a demo but still retains demo-like fallback semantics
  </initial_claims>
  <known_conflicts>
    - earlier reports emphasized runtime-cache-maintenance as the front repo-side blocker; current fresh audit now stops earlier at root/runtime leakage (.venv and apps/web/node_modules)
    - older notes implied .venv was no longer a live blocker; current root/runtime checks show it is a live blocker on this workspace
    - open-source report treated private vulnerability reporting mismatch as a major blocker; current repo-side public-contact gate passes even though GitHub platform still reports enabled=false
    - previous execution plan claimed runtime/cache hard-cut completed; current runtime-output/root checks show hard-cut is incomplete on this workspace
  </known_conflicts>
  <confidence_boundary>
    - repo-local docs/configs/scripts/tests/runtime reports are high-confidence
    - remote platform truth via gh/remote reports is medium-high confidence for platform state, but still snapshot-sensitive
    - user-provided reports are treated as leads, not facts
    - no fresh full repo-side-strict-ci PASS receipt was captured in this turn
    - no fresh end-to-end live provider run was captured in this turn
  </confidence_boundary>
</plan_intake>
```

### Repo Archetype

- **Repo archetype**：`hybrid`
- **当前最真实定位**：`public source-first + limited-maintenance + strong engineering applied AI mini-system`
- **最不该被误判成**：
  - adoption-grade open-source product
  - repo-side fully green final form
  - already-closed external distribution system
  - fully productized AI system with truthful runtime semantics everywhere

### 输入材料归一化命名

| 输入代号 | 含义 |
| --- | --- |
| `R1` | 用户提供报告 1：文档治理 + CI 治理 |
| `R2` | 用户提供报告 2：开源就绪治理 |
| `R3` | 用户提供报告 3：架构 / 缓存 / 日志 / 根目录 / 外部依赖治理 |
| `R4` | 用户提供报告 4：高含金量个人项目 / AI feature |
| `P0` | 仓库内已有执行计划 [2026-03-16_16-15-07__repo-four-track-governance-final-form-execution-plan.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/.agents/Plans/2026-03-16_16-15-07__repo-four-track-governance-final-form-execution-plan.md) |
| `C*` | 本次 fresh repo validation 命令与读档证据 |

### Canonical Claim / Issue Ledger

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `CL-01` | 仓库是高成熟 hybrid-repo | R1,R3,R4 | 已验证 | A | fact | structural | 决定主路线不应重做架构底盘 | 责任层与上游治理同时存在 | 采纳 |
| `CL-02` | docs current-state page 存在 stale drift | R1,R2,R3,R4 | 已验证 | A | fact | blocker | 直接破坏 current-proof honesty | generated current-state 未被 same-HEAD fail-close 约束 | 采纳 |
| `CL-03` | repo-side canonical gate 当前不绿 | R1,R3,R4 | 已验证 | A | fact | blocker | 不能宣称 repo-side done | root/runtime leakage + docs drift + retention 并存 | 采纳 |
| `CL-04` | 当前 repo-side 首要 blocker 是 runtime-cache-maintenance | R1,R3,R4,P0 | 被部分推翻 | A | inference | blocker | 影响主路线排序 | 当前 workspace 已出现更前置 blocker：`.venv` / `apps/web/node_modules` | 部分采纳 |
| `CL-05` | `.venv` 不再是当前 blocker | memory/older note | 被推翻 | A | fact | blocker | 影响根治理裁决 | 当前 workspace 根目录真实存在 `.venv` | 不采纳 |
| `CL-06` | `apps/web/node_modules` 不应停留在源码树 | R3,R4 | 已验证 | A | fact | blocker | 影响 runtime-output 主路线 | runtime-outputs contract 明确 forbids `node_modules` | 采纳 |
| `CL-07` | remote required checks 与 branch protection 对齐 | R1,R2,R3 | 已验证 | A | fact | structural | 说明远端完整性面较强 | remote policy/readiness 已接线 | 采纳 |
| `CL-08` | GHCR external image lane 仍 blocked | R1,R2,R3,R4 | 已验证 | A | fact | structural | external lane 不能宣称闭环 | registry auth / token scope 未闭环 | 采纳 |
| `CL-09` | release evidence 只是 ready，不是 verified | R1,R2,R3,R4 | 已验证 | A | fact | important | 不能把 release preflight 写成完成 | `ready` 与 `verified` 语义未统一消费 | 采纳 |
| `CL-10` | PVR mismatch 是当前 repo-side blocker | R2 | 部分验证 | B | risk | important | 影响 open-source narrative | 平台为 false，但当前 public-contact gate 已通过 | 部分采纳 |
| `CL-11` | 架构/合同/日志/上游控制面整体很强 | R1,R3,R4 | 已验证 | A | fact | structural | 说明主路线应聚焦 truthfulness，而非重画架构图 | control planes 已 machine-enforced | 采纳 |
| `CL-12` | AI eval 只是叙事，没有 fresh receipt | R4 | 被推翻 | A | fact | important | 影响含金量判断 | eval assets + regression 本轮 fresh PASS | 不采纳 |
| `CL-13` | AI feature 仍带 demo 语义 | R4 | 已验证 | A | fact | structural | 影响招聘信号与 failure honesty | `computer_use` fallback 返回 `ok` | 采纳 |
| `CL-14` | newcomer/result proof 已 fully mainlined | P0 | 被推翻 | A | fact | important | 影响结果证明判断 | `check_newcomer_result_proof.py` 当前 FAIL | 不采纳 |
| `CL-15` | `.agents` tracked/ignored 裂缝是当前主要 blocker | R3,older memory | 部分验证但非当前主 blocker | C | risk | enhancement | 影响长期治理，但不在当前红灯栈最前 | `.gitignore` 已对白名单 `Plans` 解禁 | 部分采纳 |

### 冲突仲裁结论

| 冲突点 | 双方说法 | 当前裁决 |
| --- | --- | --- |
| repo-side 最前 blocker | 旧报告强调 `runtime-cache-maintenance`；当前 fresh gate 先红在 `.venv` | **以当前 gate 顺序为准**：先根目录 / runtime-output 泄漏，再 docs drift，再 retention |
| `.venv` 是否还是 blocker | 旧记忆称不是当前 blocker；fresh root allowlist 称是 blocker | **以 fresh root allowlist 为准**：当前 workspace 的 `.venv` 就是 blocker |
| PVR 是否构成当前 repo-side 红灯 | 平台 `enabled=false`；repo-side public-contact gate PASS | **裁决为“平台事实为红，repo-side wording 已部分补救”**，属于 public-truth structural item，不是当前第一 repo-side blocker |
| newcomer/result proof 是否已闭环 | 旧计划写主链化完成；fresh newcomer gate FAIL | **以 fresh gate 为准**：还没有闭环 |

---

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 / 含金量 | 强工程型 applied AI mini-system 候选 | owner-level 叙事与 current-proof、user-result proof 同步成立 | A | 是 | 长板真实，但终局未闭环 |
| 开源边界 / public surface | 公开边界大体清楚，但平台事实与部分叙事仍有张力 | public narrative 完全以平台 truth + repo truth 双重 fail-close 驱动 | A | 是 | PVR、GHCR、ready/verified 仍需收口 |
| 文档事实源治理 | docs control plane 强，但 generated current-state 已失真 | current-state docs 同 commit、不同 commit 自动降级为 stale/historical | A | 是 | 当前 docs gate 已红 |
| CI 主链与 Gate 可信度 | workflow / remote required checks 很强，但 repo-side current proof 不闭环 | gate 结果与最终叙事同口径；repo-side done 不再被轻量 gate 误讲 | A | 是 | governance-audit 当前非绿 |
| 架构治理 | 强 | 保持强，不做无关重构 | A | 是 | 不是当前主战场 |
| 缓存治理 | `.runtime-cache` 契约强，但 retention 与 runtime leakage 并存 | runtime outputs 真单出口，重建与清理路径一致 | A | 是 | `.venv` / `node_modules` / expired artifacts 并存 |
| 日志治理 | 强 | 保持强，补入 current-proof 事件 | A | 是 | 不是当前 blocker |
| 根目录洁净治理 | 当前红在 `.venv` | 根目录无未知项；本地环境不再落入 repo root | A | 是 | 当前最前 blocker |
| 外部依赖集成治理 | 上游 inventory 强，GHCR lane blocked | external lane 要么 verified，要么明确 optional | A | 是 | 不应继续含糊 |
| AI feature 真实性 | eval 真跑，主流程真存在，但 failure honesty 不够 | AI 路径失败 / unsupported / degraded 语义真实 | A | 是 | `browser_stub/no_op -> ok` 必须硬切 |
| 用户结果证明 | 有结果证明文档，但 fresh newcomer/result receipt 不足 | 至少 2-3 个 representative task proof pack fresh mainlined | B | 是 | 当前弱于治理证明 |

---

## [四] 根因与完成幻觉总表

### 根因压缩

当前表层问题很多，但底层可以压成 **5 个根因**：

1. **运行态没有被彻底赶出源码树与根目录**
2. **current-proof surface 不是 same-HEAD fail-close**
3. **repo-side 完成信号被轻量 gate、历史工件和 missing receipt 混用**
4. **AI / 结果证明里仍有“看起来成功”的 demo 语义**
5. **public/external 叙事仍允许“存在/ready/public”偷换成“verified/closed”**

### 根因 / 幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| docs 幻觉 | 有 generated snapshot 页面 | 页面写的是旧 HEAD，不等于 current truth | WS2 current-proof/docs hard cut | `check_docs_governance.py` + `check_current_proof_commit_alignment.py` |
| CI 可信幻觉 | remote required checks PASS | 远端完整性绿，不等于 repo-side 当前绿 | WS3 gate chain rebase | `governance-audit` + `repo-side-strict-ci` receipt |
| 架构治理幻觉 | contract/logging/upstream 多数 PASS | 底盘强，不等于今天这棵树干净 | WS1 runtime surface hard cut | `check_root_allowlist.py` + `check_runtime_outputs.py` |
| 缓存治理幻觉 | `.runtime-cache` 已是事实源 | repo 外与源码树里仍有运行态泄漏，run/report 还会过期 | WS1 + WS3 | `check_runtime_outputs.py` + `check_runtime_cache_retention.py` |
| 开源 readiness 幻觉 | public repo + LICENSE + SECURITY + generated docs | 平台 PVR 为 false；GHCR blocked；release only ready | WS4 public/external truth alignment | `check_public_contact_points.py` + readiness reports |
| 项目含金量幻觉 | README / value-proof / eval 文档很完整 | 用户结果证明仍弱于治理证明 | WS6 user-result proof mainline | `check_newcomer_result_proof.py` + fresh proof pack receipts |
| AI productization 幻觉 | computer-use 路径存在且有测试 | fallback/noop 仍返回 `ok`，失败诚实度不足 | WS5 AI failure honesty hard cut | worker tests + eval rubric / smoke semantics |
| “clean git status = clean repo” 幻觉 | `git status --short` clean | ignored `.venv` 与 `apps/web/node_modules` 仍让 gate 红 | WS1 runtime surface hard cut | `check_root_allowlist.py` + `check_runtime_outputs.py` |

### 哪个根因最贵 / 最危险

| 问题 | 判断 |
| --- | --- |
| 最贵的根因 | **运行态未硬切出源码树与根目录**。它会同时污染 root governance、runtime outputs、repo-side done、newcomer 体验和本地执行习惯。 |
| 最能制造完成幻觉 | **current-proof surface stale 仍可被正式文档消费**。它会让人直接相信旧状态。 |
| 最伤长期维护 | **轻量 gate、历史工件、missing receipt 混用**。这会让每次汇报都先做语义辩论。 |
| 最影响招聘 / 展示信号 | **AI fallback 假成功语义 + 用户结果证明不足**。会被问穿。 |
| 最影响开源 / public 判断 | **ready/public/generated 被误讲成 verified/closed**。 |

---

## [五] 绝不能妥协的红线

- **不能再允许根目录 `.venv` 存在于 canonical local path**。本地私有环境必须移出 repo root 或进入 `.runtime-cache/tmp/**` 这类受控临时面。
- **不能再允许 `apps/web/node_modules` 被当作可接受的本地默认状态**。这与 runtime-output contract 直接冲突。
- **不能再让 `docs/generated/external-lane-snapshot.md` 这种 current-state 页面在旧 HEAD 上继续被 README / docs 当权威入口引用。**
- **不能再让 `browser_stub` / `no_op` 返回 `status=ok` 进入 canonical AI 语义。**
- **不能再把 `ready`、`public`、`generated`、`historical success`、`启动过` 写成 “verified / closed / current PASS”。**
- **不能再把 `./bin/governance-audit --mode audit` 单独当成 repo-side done 信号。**
- **不能继续保留会把 repo-side 安装路径写回源码树的 public docs / runbook / golden command。**
- **不能为了兼容历史习惯而长期保留“双路径都行”的说法。** 临时桥只能有明确禁写时点和删除时点。

---

## [六] Workstreams 总表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| WS1 Runtime Surface Hard Cut | `PARTIALLY_COMPLETED` | P0 | L1 + implementer lane | `workspace-hygiene` 已接入 wrapper / entrypoint / bootstrap / validate-profile；root/runtime residue 当前 fresh 清零 | 收口 raw `uv run` 绕过 wrapper 时的 `.venv` 复发风险 | `root-allowlist PASS`、`runtime-outputs PASS` |
| WS2 Current-Proof / Docs Hard Cut | `VERIFIED` | P0 | L1 | `external-lane-snapshot` 改成 tracked pointer page；README/start-here/runbook 已重渲 | 若继续推进，再把 runtime-owned current-state summary 接入导航 | `check_docs_governance PASS` |
| WS3 Repo-side Gate Chain Rebase | `PARTIALLY_COMPLETED` | P0 | L1 | canonical blocker ladder 已从 root/source residue 收敛到 maintenance / heavier receipts | 补 fresh `repo-side-strict-ci` receipt，并决定 maintenance `--apply` 的长期入口 | `governance-audit PASS` |
| WS4 Public / External Truth Alignment | `PARTIALLY_COMPLETED` | P1 | L1 | SECURITY/public wording 已改成 capability-conditioned truth；public-contact 仍 PASS | 决定是否把 PVR / repo metadata probe 产物做成 canonical runtime report | `public-contact-points PASS` |
| WS5 AI Failure Honesty Hard Cut | `PARTIALLY_COMPLETED` | P0 | L1 | `browser_stub/no_op` 不再返回 `ok`；navigate 真 bug 也已顺手修正 | 评估是否继续把 outer call-meta 的 `status=ok` 语义一并收紧 | `43 worker tests PASS` |
| WS6 User-Result Proof Mainline | `PARTIALLY_COMPLETED` | P1 | L1 | `render_newcomer_result_proof.py` fresh 生成；`check_newcomer_result_proof.py` PASS | 补 `repo_side_strict_receipt=pass` 与 2-3 个 task-result proof pack | `newcomer-result-proof PASS` |
| WS7 Preserve Strong Control Planes | `ACTIVE_GUARD` | P2 | L1 | 强面 gates 持续保持 PASS | 不主动扩 scope；只在新 blocker 波及时触碰 | `dependency/logging/upstream/contract PASS` |

---

## [七] 详细 Workstreams

### WS1. Runtime Surface Hard Cut

**目标**

把 repo-side 运行态从“原则上该离开源码树”推进到“当前路径上真的离开源码树”。

**为什么它是结构性动作**

- 这是当前 repo-side 最前 blocker
- 它不解决，后面 docs、strict receipts、新手体验都会持续被假脏树污染
- 它决定仓库到底是“制度型 clean repo”，还是“clean git status 但 ignored 垃圾到处在”

**输入**

- [config/governance/runtime-outputs.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/config/governance/runtime-outputs.json)
- [docs/reference/cache.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/cache.md)
- [scripts/governance/check_runtime_outputs.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_runtime_outputs.py)
- [scripts/runtime/clean_source_runtime_residue.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/runtime/clean_source_runtime_residue.py)
- [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)

**输出**

- Python 本地环境统一迁出 repo root
- Web machine-state 统一迁入 `.runtime-cache/tmp/web-runtime/**`
- README / runbook / public quickstart 不再推荐生成 `apps/web/node_modules`
- runtime-output gate 从“原则正确”变成“现场也正确”

**改造对象**

- 文档：
  - [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)
  - [docs/start-here.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/start-here.md)
  - [docs/runbook-local.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/runbook-local.md)
  - [ENVIRONMENT.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/ENVIRONMENT.md)
  - [docs/reference/cache.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/cache.md)
- 配置与 gate：
  - [config/governance/runtime-outputs.json](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/config/governance/runtime-outputs.json)
  - [scripts/governance/check_runtime_outputs.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_runtime_outputs.py)
  - [scripts/governance/check_root_allowlist.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_root_allowlist.py)
- 执行入口：
  - [bin/prepare-web-runtime](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/prepare-web-runtime)
  - [bin/run-in-standard-env](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/run-in-standard-env)
  - [scripts/ci/python_tests.sh](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/ci/python_tests.sh)

**删除 / 禁用**

- README / runbook 中把 `npm --prefix apps/web ci` 作为 repo-tree 默认路径的口径
- repo-root `.venv` 作为默认 local env 的习惯
- 任何允许 `apps/web/node_modules` 成为长期稳定状态的口径

**迁移桥**

- 临时允许 `bin/prepare-web-runtime` 作为唯一兼容桥
- 兼容桥职责：
  - 在 `.runtime-cache/tmp/web-runtime/workspace/apps/web` 准备 Web 工作区
  - 明确桥接后的 install / build / test 命令入口
- 禁止：
  - 新文档再推荐直接 repo-tree install
  - 新脚本继续写入 `apps/web/node_modules`

**禁写时点**

- 本 Plan 落地后，立刻禁止新增任何文档或脚本把 `.venv` / `apps/web/node_modules` 写成 canonical path

**删除时点**

- 当 `README.md`、`docs/start-here.md`、`docs/runbook-local.md`、`bin/prepare-web-runtime`、`check_runtime_outputs.py` 全部对齐后，删除所有剩余旧命令示例

**Done Definition**

- `python3 scripts/governance/check_root_allowlist.py --strict-local-private` PASS
- `python3 scripts/governance/check_runtime_outputs.py` PASS
- `./bin/governance-audit --mode audit` 至少不再红在 `.venv` / `apps/web/node_modules`
- 所有 public docs 不再引导用户生成 repo-tree venv / node_modules

**Fail Fast 检查点**

- root 仍出现 `.venv`
- `apps/web/node_modules` 仍被 `prepare-web-runtime` 之外的路径生成
- 文档仍保留 direct repo-tree install 指令

**它会打掉什么幻觉**

- clean git status = clean repo
- 有 runtime-output contract = 现场已经按 contract 执行

**它会改变哪个上层判断**

- repo-side root/runtime governance 从“结构强但现场红”变成“现场也强”
- open-source / newcomer 体验不再被本地环境落点污染

---

### WS2. Current-Proof / Docs Hard Cut

**目标**

让 current-state surface 只能说当前真话，说不了就直接降级成 stale / historical。

**为什么它是结构性动作**

- 当前文档治理最危险的不是 manual sync 税，而是 current-state 页面会误导判断
- 这会同时污染 docs/CI/open-source/project-signal 四条叙事

**输入**

- [docs/generated/external-lane-snapshot.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/generated/external-lane-snapshot.md)
- [docs/reference/external-lane-status.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/external-lane-status.md)
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [docs/reference/newcomer-result-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/newcomer-result-proof.md)
- [scripts/governance/check_docs_governance.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_docs_governance.py)
- [scripts/governance/check_current_proof_commit_alignment.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_current_proof_commit_alignment.py)
- [scripts/governance/check_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_newcomer_result_proof.py)

**输出**

- generated current-state docs 只有两种合法状态：
  - `current and aligned`
  - `degraded / stale / historical`
- newcomer/result proof 会带上 eval regression summary 与 fresh receipt 语义
- README 不再把 stale current-state 页面当自然可信入口

**改造对象**

- 文档：
  - [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)
  - [docs/reference/external-lane-status.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/external-lane-status.md)
  - [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
  - [docs/reference/newcomer-result-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/newcomer-result-proof.md)
- 渲染与检查：
  - `scripts/governance/render_docs_governance.py`
  - `scripts/governance/check_docs_governance.py`
  - `scripts/governance/check_current_proof_commit_alignment.py`
  - `scripts/governance/check_newcomer_result_proof.py`
  - `config/docs/render-manifest.json`
  - `config/docs/change-contract.json`

**删除 / 禁用**

- generated current-state 页面里写死历史 HEAD 并被继续当 current proof 入口消费
- newcomer proof 中 `missing_current_receipt` 被口头讲成“差不多通过”

**迁移桥**

- 临时允许 generated 页面输出 `degraded: stale_current_commit_mismatch`
- 桥接存在条件：
  - 仅在 current commit proof 缺失时展示
  - 不允许 README 把 degraded 页面写成“当前状态已确认”

**禁写时点**

- 本 Plan 落地后，立刻禁止在任何解释层文档中把 historical workflow success 当 current verified

**删除时点**

- 当 render chain 自动使用 current HEAD/runtime reports 并通过 `check_docs_governance.py` 后，删除所有旧 HEAD 示例残留

**Done Definition**

- `python3 scripts/governance/check_docs_governance.py` PASS
- [docs/generated/external-lane-snapshot.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/generated/external-lane-snapshot.md) 中 current HEAD 与 runtime report `source_commit` 一致
- `python3 scripts/governance/check_newcomer_result_proof.py` PASS

**Fail Fast 检查点**

- generated current-state 页面仍出现旧 HEAD
- newcomer proof 缺少 eval regression summary
- README 仍默认引用 stale current-state surface

**它会打掉什么幻觉**

- generated = truthful
- ready = verified
- public docs 很强 = 当前状态没漂移

**它会改变哪个上层判断**

- 文档治理从“结构强但可信度被 stale page 击穿”变为“解释层和证据层一致”
- public/open-source/recruiting 叙事恢复可信

---

### WS3. Repo-side Gate Chain Rebase

**目标**

把 repo-side 完成信号从“多个轻重不一的绿色表面”收束成一条严肃、可复核、不可偷换的 gate 链。

**为什么它是结构性动作**

- 当前最容易误判的是：有很多 PASS，就以为整体 PASS
- 但 repo-side done 应该是“重 gate 的 fresh receipt”，不是“轻 gate 曾经过”

**输入**

- [bin/governance-audit](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/governance-audit)
- [bin/repo-side-strict-ci](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/repo-side-strict-ci)
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [docs/testing.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/testing.md)

**输出**

- `governance-audit`：只负责 repo-side control-plane honesty
- `repo-side-strict-ci`：作为 repo-side 完成重 gate
- `strict-ci`：明确为 external / heavier lane，不与 repo-side 偷换

**改造对象**

- `bin/governance-audit`
- `bin/repo-side-strict-ci`
- `bin/strict-ci`
- `scripts/governance/gate.sh`
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [docs/testing.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/testing.md)
- `.runtime-cache/reports/governance/newcomer-result-proof.json`

**删除 / 禁用**

- “`governance-audit` PASS = repo-side done” 的旧口径
- “strict 命令启动过” 被讲成 “strict PASS”

**迁移桥**

- 允许 `governance-audit` 继续作为快速 honesty gate
- 但从本 Plan 起，任何“repo-side 完成”叙事必须绑定 `repo-side-strict-ci` fresh PASS receipt

**禁写时点**

- 立即禁止在 README / docs / proof pack 中把 `governance-audit` 单独写成完成证明

**删除时点**

- 当 `newcomer-result-proof` 和 `done-model` 完全只消费 fresh heavy receipts 后，删除旧轻量完成表述

**Done Definition**

- `governance-audit` 通过时，只证明 honesty gate 通过
- `repo-side-strict-ci` fresh PASS 收据存在且被 newcomer/result proof 消费
- `done-model`、`README`、`testing.md` 对完成信号语义完全一致

**Fail Fast 检查点**

- 任一文档仍把 `governance-audit` 讲成 repo-side 完成
- newcomer/result proof 仍缺 strict receipt

**它会打掉什么幻觉**

- 有很多 green sub-gates = 整体 repo-side done

**它会改变哪个上层判断**

- CI / governance 可信度从“解释靠嘴”变成“解释靠 gate 分层”

---

### WS4. Public / External Truth Alignment

**目标**

让 public/open-source/external 叙事严格服从平台 truth 和 runtime truth，而不是服从愿望。

**为什么它是结构性动作**

- 当前 public 叙事已经比以前诚实，但还没有完全 fail-close
- GHCR blocked、release only ready、PVR platform false 这三类状态很容易被外部误读

**输入**

- [SECURITY.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/SECURITY.md)
- [docs/reference/public-repo-readiness.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/public-repo-readiness.md)
- [docs/reference/external-lane-status.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/external-lane-status.md)
- [docs/generated/external-lane-snapshot.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/generated/external-lane-snapshot.md)
- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/release/release-evidence-attest-readiness.json`
- `gh api repos/.../private-vulnerability-reporting`

**输出**

- public docs 明确：
  - 什么是 repo-side truth
  - 什么是 external truth
  - 什么是 `ready`
  - 什么是 `verified`
  - 当前 external lane 哪些只是 optional / blocked / historical

**改造对象**

- 文档：
  - [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)
  - [SECURITY.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/SECURITY.md)
  - [docs/reference/public-repo-readiness.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/public-repo-readiness.md)
  - [docs/reference/external-lane-status.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/external-lane-status.md)
- Gate / probe：
  - [scripts/governance/check_public_contact_points.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_public_contact_points.py)
  - [scripts/governance/check_remote_required_checks.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_remote_required_checks.py)
  - `scripts/ci/check_standard_image_publish_readiness.sh`

**删除 / 禁用**

- “public repo” 被理解成“可以高信心采用”
- “release evidence ready” 被理解成“release verified”
- “private vulnerability reporting path exists in docs” 被理解成“平台肯定打开”

**迁移桥**

- GHCR lane 在未 verified 前，允许明确标记为 `optional external lane`，但不允许继续模糊成“正在差不多收尾”

**禁写时点**

- 本 Plan 落地后，立刻禁止任何文档把 GHCR / release / PVR 的平台事实写得比 probe 更乐观

**删除时点**

- 当 GHCR lane fresh verified 或被正式降级为非公共承诺时，删除模糊表述

**Done Definition**

- repo docs 对 `ready` / `verified` / `blocked` / `optional` 定义完全一致
- PVR 文案与平台 truth 不冲突
- GHCR lane 要么 verified，要么被显式降级为 optional external lane

**Fail Fast 检查点**

- `gh api ... private-vulnerability-reporting` 仍 false，但 docs 仍把私密入口写成默认可用
- GHCR lane 仍 blocked，但 public docs 继续暗示镜像可拉取

**它会打掉什么幻觉**

- public = adoption-grade
- ready = done
- 有 workflow = external lane 闭环

**它会改变哪个上层判断**

- open-source/public 展示判断从“强仓但口径有风险”变成“边界诚实的强仓”

---

### WS5. AI Failure Honesty Hard Cut

**目标**

把 AI 路径里所有“看起来执行了，其实只是 fallback/noop”的语义改成真实状态语义。

**为什么它是结构性动作**

- 这是当前最伤招聘/作品含金量的单点
- 不是小修补，而是“系统是否诚实对待失败”的价值观问题

**输入**

- [apps/worker/worker/pipeline/steps/llm_computer_use.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/steps/llm_computer_use.py)
- [apps/worker/tests/test_llm_computer_use_step.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/tests/test_llm_computer_use_step.py)
- [docs/reference/ai-evaluation.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/ai-evaluation.md)
- [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)

**输出**

- `playwright` 失败后，不再通过 `browser_stub` 产出 `status=ok`
- unknown executor 不再返回 `status=ok`
- `browser_stub` / `no_op` 若保留，只能表达：
  - `unsupported`
  - `degraded`
  - `failed`
  - 或显式 `skipped_by_policy`

**改造对象**

- [apps/worker/worker/pipeline/steps/llm_computer_use.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/steps/llm_computer_use.py)
- [apps/worker/tests/test_llm_computer_use_step.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/tests/test_llm_computer_use_step.py)
- 相关 read model / docs 消费面（如果有 status enum）
- smoke 说明文档：
  - [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)
  - [docs/reference/ai-evaluation.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/ai-evaluation.md)

**删除 / 禁用**

- `browser_stub` 返回 `computer_use_browser_stub_executed` 且 `status=ok`
- `no_op` 返回 `computer_use_noop_executed` 且 `status=ok`
- `playwright` error 后 fallback 仍 `status=ok`

**迁移桥**

- 如确有下游消费者依赖旧 `ok` 语义，桥只能存在于序列化适配层
- 桥接规则：
  - 内部状态先真实
  - 兼容转换仅短期存在
  - 下游迁完立即删除

**禁写时点**

- 本 Plan 落地后，立即禁止新增任何“失败后仍 ok”的 AI path 语义

**删除时点**

- 当所有消费方只依赖新状态枚举后，删除旧兼容转换

**Done Definition**

- worker tests 证明 fallback/noop 不再返回 `ok`
- 相关 API / docs / eval 文案使用统一失败语义
- `smoke-computer-use-local` 的 skip/unsupported/failed 规则与运行时一致

**Fail Fast 检查点**

- 代码里仍能找到 `browser_stub` / `no_op` 走 `status=ok`
- 测试继续把 fallback 成功写成 expected behavior

**它会打掉什么幻觉**

- 有 computer-use 路径 = 已 productized
- fallback 成功 = 真执行成功

**它会改变哪个上层判断**

- AI feature 从“有产品化意图”提升到“failure honesty 合格”
- 作品集/面试信号明显变硬

---

### WS6. User-Result Proof Mainline

**目标**

把“价值证明”从治理文档，推进成带 fresh receipt 的任务级结果证明。

**为什么它是结构性动作**

- 当前仓库最大短板不是没有 proof，而是 proof 偏向控制面
- 要想从“强工程仓”升级到“高含金量项目”，必须让用户任务结果也上主链

**输入**

- [docs/reference/value-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/value-proof.md)
- [docs/proofs/task-result-proof-pack.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/proofs/task-result-proof-pack.md)
- [docs/reference/newcomer-result-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/newcomer-result-proof.md)
- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- eval regression receipt
- representative smoke / API / process receipts

**输出**

- 至少 2-3 个 representative user-result case 有 fresh、public-safe、可追溯的 receipt
- newcomer proof 不再停留在“有读数规则”，而是有 current pass/fail result
- value-proof 不再只讲为什么复杂度值得，而能指向当前结果收据

**改造对象**

- 文档：
  - [docs/reference/value-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/value-proof.md)
  - [docs/proofs/task-result-proof-pack.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/proofs/task-result-proof-pack.md)
  - [docs/reference/newcomer-result-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/newcomer-result-proof.md)
- 生成与检查：
  - `scripts/governance/render_newcomer_result_proof.py`
  - [scripts/governance/check_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_newcomer_result_proof.py)
- receipt 来源：
  - [bin/api-real-smoke-local](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/api-real-smoke-local)
  - [bin/smoke-computer-use-local](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/smoke-computer-use-local)
  - [bin/repo-side-strict-ci](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/repo-side-strict-ci)

**删除 / 禁用**

- 只用 `value-proof.md` 的口头型叙事作为“结果证明”

**迁移桥**

- 在 fresh proof receipts 未补齐前，允许文档显示 `missing_current_receipt`
- 但不允许继续把 missing 写成 implicit pass

**禁写时点**

- 本 Plan 落地后，立即禁止新增没有 receipt 的“代表性成功案例”叙事

**删除时点**

- 当 2-3 个 representative case 都有 current receipts 且被主链消费后，删除旧的“以后再补结果证明”口径

**Done Definition**

- `check_newcomer_result_proof.py` PASS
- value-proof 中每个重点 case 都能指向当前或显式 historical 的 receipt
- 至少一个 API/ingest chain、一个 AI/eval chain、一个 repo-side heavy receipt 被 proof pack 消费

**Fail Fast 检查点**

- newcomer proof 仍 `missing`
- eval regression summary 仍未接入 newcomer proof
- 任务结果 case 仍只有文档解释，没有当前收据

**它会打掉什么幻觉**

- 治理很强 = 用户结果已证明

**它会改变哪个上层判断**

- 项目含金量从“强工程型候选”升级到“更接近 owner-level 完整项目”

---

### WS7. Preserve Strong Control Planes

**目标**

保持架构 / 合同 / 日志 / 上游治理这些真实长板，不做无关重构。

**为什么它是结构性动作**

- 当前主路线不是重写底盘
- 底盘已经强，真正要做的是让它不再被前门叙事和运行态脏项拉低可信度

**输入**

- [scripts/governance/check_dependency_boundaries.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_dependency_boundaries.py)
- [scripts/governance/check_logging_contract.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_logging_contract.py)
- [scripts/governance/check_upstream_governance.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_upstream_governance.py)
- [scripts/governance/check_upstream_same_run_cohesion.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_upstream_same_run_cohesion.py)
- [scripts/governance/check_contract_locality.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_contract_locality.py)

**输出**

- 保持这些 gate 继续通过
- 任何与主路线无关的重构一律禁止

**改造对象**

- 仅在必要的文档/状态语义层补充，不改底盘组织方式

**删除 / 禁用**

- 无关的架构“美化”

**Done Definition**

- dependency/logging/upstream/contract gates 继续绿

**它会打掉什么幻觉**

- 必须大重构架构才能走向终局

**它会改变哪个上层判断**

- 让执行聚焦真正 blocker，而不是重画已成立的结构

---

## [八] 硬切与迁移方案

### 立即废弃项

| 对象 | 立即动作 | 原因 |
| --- | --- | --- |
| repo-root `.venv` 作为 canonical local env | 立即废弃 | 当前 root allowlist 真实红灯 |
| `apps/web/node_modules` 作为默认本地依赖落点 | 立即废弃 | 当前 runtime-output contract 真实红灯 |
| stale generated current-state page 被 README 继续自然消费 | 立即废弃 | 直接制造完成幻觉 |
| `browser_stub/no_op -> status=ok` | 立即废弃 | 直接制造 AI 假成功 |
| `governance-audit PASS = repo-side done` | 立即废弃 | 轻重 gate 语义混乱 |
| `ready/public/generated` 被写成 `verified/closed` | 立即废弃 | 直接污染 public / external 判断 |

### 迁移期兼容桥

| 桥接对象 | 允许存在的桥 | 允许原因 | 禁止原因 |
| --- | --- | --- | --- |
| Web 本地工作区 | `bin/prepare-web-runtime` | 当前已有 runtime tmp 方向，适合作为短期桥 | 不能永久把 direct repo-tree install 和 tmp-workspace 双轨并存 |
| AI status enum | 序列化适配层短期兼容旧消费者 | 防止一次性打爆调用方 | 不能让内部状态继续假成功 |
| current-state 页面 | `degraded/stale` 占位态 | 保证读者看到“当前不可用”，而不是旧真相 | 不能继续静默展示旧 HEAD |

### 禁写时点

- 本 Plan 合入后立即生效：
  - 禁写 repo-root `.venv` 文档口径
  - 禁写 `apps/web/node_modules` canonical 口径
  - 禁写 stale current-state 当 current truth
  - 禁写 AI fallback `ok`
  - 禁写 `governance-audit` 单独完成语义

### 只读时点

- 历史 current-state / historical release / old success run 可以保留为历史证据，但只能只读、只能带 `historical` 语义

### 删除时点

| 对象 | 删除条件 |
| --- | --- |
| direct repo-tree install 旧命令 | WS1 所有 docs 和 wrapper 对齐后 |
| AI fallback 兼容语义 | 所有消费方改用新 enum 后 |
| stale current-state 旧渲染残留 | WS2 current-proof chain 通过后 |
| old done wording | WS3 done-model / README / testing 对齐后 |

### 防永久兼容机制

- 所有兼容桥必须：
  - 有唯一 owner
  - 有到期条件
  - 有删除 gate
  - 有明确“旧路径不再写入”规则

---

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| README / 项目定位 | README 与当前能力一致 | `python3 scripts/governance/check_public_entrypoint_references.py` + docs review | README 不再夸大 repo-side / external / AI 状态 | 对外叙事仍有假成熟 |
| public surface / secret / provenance | 公开面、联系点、权利边界受治理 | `python3 scripts/governance/check_public_surface_policy.py` | PASS | public-safe 边界仍可漂移 |
| public security contact truth | 平台安全入口与文档一致 | `python3 scripts/governance/check_public_contact_points.py` + `gh api .../private-vulnerability-reporting` | gate PASS 且文案不夸大平台入口 | public trust 仍有张力 |
| docs current-proof | current-state 文档与 current commit 对齐 | `python3 scripts/governance/check_docs_governance.py` | PASS | current-state 仍在撒旧谎 |
| current-proof alignment | runtime proof 是否 same-HEAD | `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS | runtime proof 仍可能消费旧 commit |
| newcomer/result proof | newcomer/result truth pack 完整 | `python3 scripts/governance/check_newcomer_result_proof.py` | PASS | 结果证明仍弱于治理证明 |
| root allowlist | 根目录未知项归零 | `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | 只允许 `.env` 这类明确 tolerated 项 | repo root 仍被本地运行态污染 |
| runtime outputs legality | 运行态只落在合法出口 | `python3 scripts/governance/check_runtime_outputs.py` | `.venv`、`node_modules`、`__pycache__` 等全部不出现 | 单出口 contract 仍是假成立 |
| source-runtime residue | 测试/脚本不往源码树漏运行残留 | `python3 scripts/runtime/clean_source_runtime_residue.py` + gate integration | PASS | repo-side 验证仍易带脏脚印 |
| runtime cache retention | `.runtime-cache` 舱位不过期、不冒充 current | `python3 scripts/governance/check_runtime_cache_retention.py` | PASS | 历史运行物仍污染当前判断 |
| eval assets | AI formal eval 资产齐 | `python3 scripts/governance/check_eval_assets.py` | PASS | AI eval 只剩文档叙事 |
| eval regression | deterministic regression fresh 通过 | `python3 scripts/evals/run_regression.py && python3 scripts/governance/check_eval_regression.py` | PASS | AI 质量回归没有 current proof |
| AI failure honesty | computer-use fallback 语义真实 | worker tests + targeted smoke | fallback/noop 不再返回 `ok` | AI feature 仍带 demo 味 |
| dependency boundary | 跨模块依赖不偷穿 | `python3 scripts/governance/check_dependency_boundaries.py` | PASS | 架构强项开始倒退 |
| contract-first | 契约面与实现面分离 | `python3 scripts/governance/check_contract_locality.py` + `check_contract_surfaces.py` | PASS | 契约治理被污染 |
| logging contract | 日志字段合同与通道成立 | `python3 scripts/governance/check_logging_contract.py` | PASS | 诊断证据面倒退 |
| upstream governance | 上游 inventory 与 same-run cohesion 成立 | `python3 scripts/governance/check_upstream_governance.py` + `check_upstream_same_run_cohesion.py` | PASS | external / provider truth 混乱 |
| remote required checks | 远端 branch protection 与 required checks 一致 | `python3 scripts/governance/check_remote_required_checks.py` | PASS | remote integrity 不可信 |
| GHCR readiness | external image lane truth 诚实 | `bash scripts/ci/check_standard_image_publish_readiness.sh` | verified 或明确 blocked/optional | external image lane 仍被口头化 |
| repo-side heavy closure | repo-side 终局收据 | `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | fresh PASS receipt exists | 不得宣称 repo-side 完成 |

---

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| Phase A | 锁定 repo truth：记录当前 blocker 栈 | 无 | 串行 | intake 与 claim ledger 固化 | 若不先锁真相，后续会对着旧结论施工 |
| Phase B | 执行 WS1：runtime surface hard cut | Phase A | 串行优先 | root/runtime-output gates 过 | 这是最前置 blocker，不先清无法判断更深 gate |
| Phase C | 执行 WS2：docs/current-proof hard cut | WS1 基本完成 | 可与 WS4 局部并行 | docs/newcomer/current-proof gates 过 | 若 WS1 未完成，receipt 容易继续脏 |
| Phase D | 执行 WS3：gate chain rebase | WS1 + WS2 基本完成 | 串行 | done-model / testing / receipts 对齐 | 过早做会把旧红灯包装进新语义 |
| Phase E | 执行 WS5：AI failure honesty | Phase A 后即可开始，最好在 WS2 后收口 docs | 可并行 | worker tests 与 AI docs 对齐 | 若先改结果证明，AI 语义仍会拉低叙事可信度 |
| Phase F | 执行 WS6：user-result proof mainline | WS2 + WS3 + WS5 基本完成 | 串行优先 | newcomer/result proof gates 过 | 若前面 truthfulness 未修，proof pack 仍会带假成功 |
| Phase G | 执行 WS4：public/external truth alignment | WS2 + WS3 基本完成 | 可并行 | public docs 与 platform truth 一致 | 早做容易把 stale current-proof 写进 public story |
| Phase H | 执行 WS7：保强项、防回退 | 全程 | 并行守护 | dependency/logging/upstream/contract gates 继续绿 | 避免无关重构扩散 |

### 必须先做

1. WS1
2. WS2
3. WS3

### 可以并行

- WS5 可在 WS2 中后段并行推进
- WS4 可在 WS2/WS3 已基本定型后并行推进
- WS7 全程作为守护型工作流并行

### 必须在 hard cut 前完成

- 把 `.venv` / `apps/web/node_modules` 从 canonical path 中除名
- 把 stale current-state 页面从 current truth 里除名
- 把 `browser_stub/no_op -> ok` 从 canonical AI semantics 中除名

### 必须在 Gate 生效后再迁移

- newcomer/result proof 必须等 WS2/WS3 truth pack 对齐后再主链化
- public/open-source 叙事必须等 current-proof truth 修好后再重写

### 必须冻结的新增项

- 冻结新增顶级项
- 冻结新增 repo-tree runtime output 路径
- 冻结新增“当前状态”类 generated 文档页面
- 冻结新增 AI fallback success 语义

---

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| 硬切 `.venv` / `apps/web/node_modules` | repo-side governance 从“看起来强”变成“现场真的干净” | 当前最前 blocker 就是它们 |
| 修复 external snapshot stale drift | docs/CI/open-source/project-signal 四条线同时恢复可信 | 当前 stale current-state 是跨维度误导源 |
| 重建 repo-side gate 语义 | “governance green” 不再被误讲成 “repo-side done” | 轻重 gate 分层恢复 |
| 去掉 AI fallback `ok` | AI feature 从 demo-like 变成 failure-honest | 作品含金量最直接提升项 |
| newcomer/result proof 补 fresh receipts | 价值证明从治理导向变成结果导向 | 直接补齐当前短板 |
| 明确 GHCR / ready / PVR truth | open-source/public 展示不再过度承诺 | 防止外部误读 |

---

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 WS1：Runtime Surface Hard Cut

- **原因**：这是当前 repo-side 最前 blocker
- **打掉的幻觉**：clean git status = clean repo
- **释放的能力**：后续所有 gate 才能重新反映仓库本来的状态，而不是本地环境落点

### 2. 先做 WS2：Current-Proof / Docs Hard Cut

- **原因**：当前最危险的误导源就是 stale current-state 页面
- **打掉的幻觉**：generated page = current truth
- **释放的能力**：README / docs / public story 才能重新可信

### 3. 先做 WS5：AI Failure Honesty Hard Cut

- **原因**：这是当前最伤项目含金量、最容易被 reviewer 质疑的单点
- **打掉的幻觉**：有 AI path + 有测试 = 已 productized
- **释放的能力**：招聘 / 展示 / AI productization 叙事显著变硬

> 如果只能做 3 件事，我不优先做 GHCR，不优先再堆 docs，不优先再讲价值故事。  
> 我会先修 **runtime 真实度、current-proof 真实度、AI failure 真实度**。

---

## [十三] 不确定性与落地前核对点

### 高置信事实

- root allowlist 当前红在 `.venv`
- runtime outputs 当前红在 `.venv` 与 `apps/web/node_modules`
- docs governance 当前红在 stale external snapshot
- runtime-cache retention 当前红在 expired `run/**` 与 stale test report
- eval regression 本轮 fresh PASS
- remote required checks 本轮 fresh PASS
- GHCR readiness 当前 `blocked`
- release evidence 当前 `ready`
- newcomer/result proof 当前 FAIL
- AI `computer_use` 当前存在 fallback/noop `ok` 语义

### 中置信反推

- `apps/web/node_modules` 与 README / local command 的冲突，说明 canonical local web install path 需要硬切而不是小修
- 当前 `check_public_contact_points.py` PASS，说明 repo 文案已部分补救 PVR mismatch，但平台 truth 仍未完全收口
- 旧计划中“runtime/cache hard cut completed”在当前 workspace 上已失效

### 落地前必须二次核对

- `apps/web/node_modules` 是否存在某个必须保留的 dev-only 兼容理由
- `.venv` 由哪些现有命令生成，是否有单一 repo-owned wrapper 可以统一改写
- AI status enum 是否被 API / Web / MCP 外露消费，避免语义切换时漏改
- newcomer/result proof 的“代表性 task receipts”究竟选哪 2-3 条最稳

### 但这些不确定性不构成暂停理由

- 主路线已经足够明确
- 不确定点只影响实施顺序中的细枝末节，不影响终局方向

---

## [十四] 执行准备状态

### Current Status

- repo archetype：`hybrid`
- current repo-side state：**green at governance-audit layer, but not yet green at repo-side-strict layer**
- current first blockers：
  - `repo-side-strict-ci` 仍未拿到 fresh PASS receipt
  - `third-party-notices` 的 host / debug-build strict drift 已修平
  - 宿主 Docker 当前已恢复，当前后台 rerun 已推进到更深 long-tests 区段
  - 最新已定位的更深 completed-run blocker 是 heavy strict 长链中的测试/coverage/contract 层，而不是治理短板
  - external GHCR lane still `blocked`
  - release evidence still `ready`
  - AI outer call-meta 仍可能把 handler-level degraded/unsupported 包装成 tool-call `status=ok`

### Next Actions

1. 等当前后台 `repo-side-strict-ci` rerun 结束，读取最终最深 blocker 或 fresh PASS receipt
2. 若 rerun PASS，立刻重渲 newcomer proof，让 `repo_side_strict_receipt=pass`
3. 若 rerun继续失败，只围绕新最深 blocker继续缩圈，不回头重做已绿治理面

### Decision Log

- 决策：采用**唯一主路线 hard cut**
- 原因：当前问题不是“缺方案”，而是旧习惯、旧语义、旧状态还在活着
- 不采用：
  - 先补展示层
  - 先继续堆 docs
  - 先模糊兼容旧路径
- `2026-03-17 02:08 PDT`
  - 采用 `2026-03-17_01-54-18__repo-final-form-master-plan.md` 作为唯一 active plan；同会话 `01-52-51` 版本降级为历史输入。
- `2026-03-17 02:12 PDT`
  - `docs/generated/external-lane-snapshot.md` 改为 tracked pointer page，不再承载 current verdict payload。
- `2026-03-17 02:15 PDT`
  - hygiene 逻辑统一下沉到 `scripts/runtime/workspace_hygiene.sh`，`bin/workspace-hygiene` 只做稳定入口与参数兼容。
- `2026-03-17 02:17 PDT`
  - `browser_stub` / `no_op` 不再返回 `status=ok`；`navigate` 的真实目标 URL 也同步修复，避免旧假成功继续掩盖真实 bug。
- `2026-03-17 02:20 PDT`
  - `prune_runtime_cache.py --apply` 同时删除 TTL 过期与 freshness 过期的 stale artifact，避免旧 report 永远卡在 current gate 前面。
- `2026-03-17 02:31 PDT`
  - `pr-llm-real-smoke` fresh 重跑成功，并把 Gemini blocker row 的 `last_verified_run_id` / `last_verified_at` 升级到当前 receipt，修复 same-run cohesion。
- `2026-03-17 02:31 PDT`
  - `SECURITY.md` / public docs 改成 capability-conditioned truth；不再把 tracked policy 文件存在偷换成平台能力一定可用。
- `2026-03-17 03:30 PDT`
  - `render_third_party_notices.py` 改成使用 throwaway temp uv env + `UV_LINK_MODE=copy`，并把生成口径固定到 `uv run --extra dev --extra e2e`。
- `2026-03-17 03:42 PDT`
  - `apps/worker/tests/test_external_proof_semantics.py` 与 `apps/worker/tests/test_supply_chain_ci_contracts.py` 对齐到 pointer-page / historical-example 新语义。
- `2026-03-17 04:18 PDT`
  - `repo-side-strict-ci` 在已清除 repo/gate blockers 后，后台重跑最终落在宿主环境错误：`Docker Desktop is unable to start`。这已是当前能力范围外的真实硬边界，而不是继续藏在仓库逻辑里的假失败。
- `2026-03-17 10:56 PDT`
  - `bin/strict-ci` wrapper 补上 per-run `complete PASS/FAIL` receipt logging，解决 strict receipt 之前天然写不出来的问题。
- `2026-03-17 11:02 PDT`
  - `apps/api/app/services/ui_audit.py` 修复 `_collect_artifacts()` 对 `Path.is_file()` / `stat()` 双次异常的容错分支，清掉 heavy strict 长链新暴露的 API 测试失败。
- `2026-03-17 11:05 PDT`
  - `docker version` / `docker info` / `docker run --rm hello-world` / `docker desktop status` 当前都表明宿主 Docker 已恢复；旧 “Docker Desktop is unable to start” 应降级为历史窗口，不再当作 current truth。

### Validation Log

| 验证项 | 当前结果 |
| --- | --- |
| `python3 scripts/governance/check_docs_governance.py` | PASS |
| `python3 scripts/governance/check_public_contact_points.py` | PASS |
| `python3 scripts/governance/check_root_allowlist.py --strict-local-private` | PASS |
| `python3 scripts/governance/check_runtime_outputs.py` | PASS |
| `python3 scripts/governance/check_runtime_cache_retention.py` | PASS |
| `python3 scripts/governance/check_runtime_cache_freshness.py` | PASS |
| `python3 scripts/governance/check_newcomer_result_proof.py` | PASS |
| `./bin/governance-audit --mode audit` | PASS |
| `python3 scripts/governance/check_eval_assets.py && python3 scripts/evals/run_regression.py && python3 scripts/governance/check_eval_regression.py` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=\"$PWD/.runtime-cache/tmp/uv-project-env\" uv run --extra dev pytest apps/worker/tests/test_llm_computer_use_step.py apps/worker/tests/test_runner_overrides.py -q` | PASS (43 tests) |
| `python3 scripts/governance/check_dependency_boundaries.py` | PASS |
| `python3 scripts/governance/check_logging_contract.py` | PASS |
| `python3 scripts/governance/check_upstream_governance.py` | PASS |
| `python3 scripts/governance/check_upstream_compat_freshness.py` | PASS |
| `python3 scripts/governance/check_upstream_same_run_cohesion.py` | PASS |
| `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS |
| `python3 scripts/governance/check_remote_required_checks.py` | PASS |
| `python3 scripts/governance/check_env_contract.py --strict` | PASS |
| `bash scripts/governance/ci_or_local_gate_doc_drift.sh --scope push` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=\"$PWD/.runtime-cache/tmp/uv-project-env\" bash scripts/ci/pr_llm_real_smoke.sh` | PASS |
| `./bin/governance-audit --mode pre-push` | PASS |
| `python3 scripts/governance/render_third_party_notices.py && python3 scripts/governance/render_third_party_notices.py --check` | PASS |
| `VD_STANDARD_ENV_ALLOW_LOCAL_BUILD=1 ./scripts/ci/run_in_standard_env.sh python3 scripts/governance/render_third_party_notices.py --check` | PASS |
| `UV_PROJECT_ENVIRONMENT=\"$PWD/.runtime-cache/tmp/uv-project-env\" PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest apps/worker/tests/test_external_proof_semantics.py apps/worker/tests/test_supply_chain_ci_contracts.py -q` | PASS (18 tests) |
| `./bin/strict-ci --mode unsupported` | FAIL as expected, and now writes per-run `complete FAIL` receipt |
| `UV_PROJECT_ENVIRONMENT=\"$PWD/.runtime-cache/tmp/uv-project-env\" PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest apps/api/tests/test_ui_audit_service_extra_coverage.py::test_ui_audit_artifact_collection_handles_limits_and_stat_errors -q` | PASS |
| `docker version` / `docker info` / `docker run --rm hello-world` / `docker desktop status` | PASS |
| `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | 当前后台 rerun still in progress；上一个 completed rerun 已将最深 blocker推进到 heavy long-tests 层（web unit/build、python tests+coverage、contract diff），不再卡治理短板 |

### Risk / Blocker Log

| 类型 | 内容 | 当前处理 |
| --- | --- | --- |
| Important | raw `uv run` 若不显式设置 `UV_PROJECT_ENVIRONMENT`，仍会在 repo root 重建 `.venv` | 已识别为 operator bypass 风险；当前通过 wrapper/hygiene 控制，后续继续收口到 WS1/WS3 |
| Important | `repo-side-strict-ci` 中 source bytecode residue 再生成问题已通过 `PYTHONPYCACHEPREFIX=.runtime-cache/tmp/pycache` 默认重定向显著压低 | 已缓解，继续观察 |
| Important | `repo_side_strict_receipt` 仍缺 current-pass 收据 | WS3/WS6 |
| Important | 当前后台 heavy strict rerun 仍在执行，尚未落出最终退出码 | 继续轮询 `.runtime-cache/tmp/repo-side-strict-final.log` / `.exit` |
| Blocker | 最新已完成的 heavy strict rerun 已把最深 blocker推进到 long-tests 层：web unit/build、python tests+coverage、contract diff local gate | 若当前 rerun仍失败，直接从这组深层测试/契约失败继续缩圈 |
| Structural | AI outer call-meta 仍可能把 handler-level degraded/unsupported 包装成 tool-call `status=ok` | WS5 余项 |
| Structural | GHCR external lane blocked | WS4 |
| Important | release evidence only ready | WS4 |

### Files Changed Log

| 类型 | 路径 / 对象 | 说明 |
| --- | --- | --- |
| New plan authority | `.agents/Plans/2026-03-17_01-54-18__repo-final-form-master-plan.md` | 当前唯一 active master plan |
| New current-proof entry | `scripts/governance/render_current_state_summary.py` | 生成 runtime-owned current-state summary |
| New hygiene entry | `bin/workspace-hygiene`, `scripts/runtime/workspace_hygiene.sh` | repo-owned residue normalize/report 入口 |
| Runtime hygiene | `scripts/env/validate_profile.sh`, `scripts/runtime/bootstrap_full_stack.sh`, `scripts/runtime/entrypoint.sh`, `scripts/runtime/run_runtime_cache_maintenance.sh` | 在 canonical entrypoint 前接入 workspace normalize |
| Strict receipt chain | `bin/strict-ci`, `scripts/governance/render_newcomer_result_proof.py` | strict per-run completion receipt 现在可写出并可被 proof 消费 |
| Heavy strict debugging | `apps/api/app/services/ui_audit.py`, `scripts/ci/python_tests.sh` | 修复 heavy strict 长链中新暴露的 API 测试失败与 coverage shard metadata 缺口 |
| Python hygiene | `scripts/governance/quality_gate.sh`, `scripts/runtime/entrypoint.sh`, `infra/config/env.contract.json`, `.env.example`, `ENVIRONMENT.md`, `docs/testing.md` | 默认把 bytecode 重定向到 `.runtime-cache/tmp/pycache`，避免 strict path 把 `__pycache__` 回写到 `apps/**` |
| Docs truth | `scripts/governance/render_docs_governance.py`, `docs/generated/external-lane-snapshot.md`, `README.md`, `docs/start-here.md`, `docs/runbook-local.md`, `docs/reference/external-lane-status.md`, `docs/reference/project-positioning.md` | current-state 从 tracked docs 硬切到 runtime-owned summary |
| Public truth | `SECURITY.md`, `docs/reference/public-repo-readiness.md`, `docs/reference/public-rights-and-provenance.md`, `docs/reference/public-privacy-and-data-boundary.md`, `docs/reference/public-artifact-exposure.md`, `docs/reference/public-brand-boundary.md` | 改成 capability-conditioned truth |
| AI honesty | `apps/worker/worker/pipeline/steps/llm_computer_use.py`, `apps/worker/tests/test_llm_computer_use_step.py`, `apps/worker/tests/test_runner_overrides.py` | `browser_stub/no_op` 不再返回 `ok` |
| Drift/env sync | `.env.example`, `infra/config/env.contract.json`, `docs/testing.md`, `docs/reference/ai-evaluation.md`, `docs/reference/value-proof.md`, `docs/reference/newcomer-result-proof.md`, `docs/reference/done-model.md`, `docs/reference/dependency-governance.md` | 同步新增 env var、runtime/current-proof/AI honesty/Web runtime hash 口径 |
| Upstream proof | `config/governance/upstream-compat-matrix.json` | 回写 fresh Gemini verified run receipt |
| Heavy-gate hardening | `scripts/ci/prepare_web_runtime.sh`, `scripts/governance/quality_gate.sh`, `THIRD_PARTY_NOTICES.md`, `artifacts/licenses/third-party-license-inventory.json` | 修正 Web runtime 旧副本复用、收紧 bytecode hygiene，并追 third-party-notices strict-context 漂移 |

### Files Planned To Change

- [README.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/README.md)
- [docs/start-here.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/start-here.md)
- [docs/runbook-local.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/runbook-local.md)
- [ENVIRONMENT.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/ENVIRONMENT.md)
- [docs/reference/cache.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/cache.md)
- [docs/reference/external-lane-status.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/external-lane-status.md)
- [docs/reference/done-model.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/done-model.md)
- [docs/reference/newcomer-result-proof.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/newcomer-result-proof.md)
- [docs/reference/public-repo-readiness.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/docs/reference/public-repo-readiness.md)
- [SECURITY.md](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/SECURITY.md)
- [apps/worker/worker/pipeline/steps/llm_computer_use.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/worker/pipeline/steps/llm_computer_use.py)
- [apps/worker/tests/test_llm_computer_use_step.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/apps/worker/tests/test_llm_computer_use_step.py)
- `scripts/governance/render_docs_governance.py`
- [scripts/governance/check_docs_governance.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_docs_governance.py)
- [scripts/governance/check_newcomer_result_proof.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_newcomer_result_proof.py)
- [scripts/governance/check_runtime_outputs.py](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/scripts/governance/check_runtime_outputs.py)
- [bin/prepare-web-runtime](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/prepare-web-runtime)
- [bin/governance-audit](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/governance-audit)
- [bin/repo-side-strict-ci](/Users/yuyifeng/Documents/VS%20Code/1_Personal_Project/%5B%E5%85%B6%E4%BB%96%E9%A1%B9%E7%9B%AE%5DUseful_Tools/%F0%9F%93%BA%E8%A7%86%E9%A2%91%E5%88%86%E6%9E%90%E6%8F%90%E5%8F%96/bin/repo-side-strict-ci)
