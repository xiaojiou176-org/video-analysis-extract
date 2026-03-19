# [🧭] Repo 终局总 Plan

## Plan Meta

- Created: `2026-03-18 16:41:47 America/Los_Angeles`
- Last Updated: `2026-03-18 17:36:00 America/Los_Angeles`
- Repo: `/Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取`
- Repo Archetype: `hybrid-repo`
- Execution Status: `In Progress`
- Current Phase: `Execution / Plan Takeover Calibrated`
- Current Workstream: `WS1 GHCR External Distribution Closure`
- Source Of Truth: `本文件`

## Workstreams 状态表

| Workstream | 状态 | 优先级 | 负责人 | 最近动作 | 下一步 | 验证状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `WS1` GHCR External Distribution Closure | `Blocked` | `P0` | `L1 Coordinator` | 已完成 fresh 本地 GHCR readiness 复核、备用 `write:packages` 账号重试，以及 current-head 远端 workflow 触发；当前 HEAD 的 GHCR workflow `23272897159` 直接失败在 `Standard image publish preflight` | 将“真平台阻塞”写入长期 blocker 台账，并继续推进所有不依赖 GHCR write auth 的 repo-side workstreams | `Current-head run confirms platform-side auth blocker` |
| `WS2` Current-Truth Fail-Close Convergence | `Verified` | `P0` | `L2 worker Raman + L1` | 已新增 summary fail-close 检查器、修正 current-state summary 渲染逻辑，并刷新 pointer/reference 语义；fresh summary 现正确显示 `workflow:ghcr-standard-image=blocked`、`workflow:release-evidence-attestation=verified` | 保持护栏，避免 stale summary 回潮 | `check_current_state_summary.py PASS; check_current_proof_commit_alignment.py PASS; test_external_proof_semantics.py 7 passed` |
| `WS3` Remote Integrity Merge Gate | `Partially Completed` | `P1` | `L2 worker Avicenna + L1` | 已把 `remote-integrity` 接入 repo-side merge-relevant CI 链，并同步 docs/generated/required-checks 语义；fresh docs/render/tests 全绿 | 记录“远端真正生效仍需后续提交/推送/平台同步”这一额外条件，并把 repo-side 部分封口 | `docs governance PASS; docs governance control-plane tests 8 passed; platform-side required context sync still pending` |
| `WS4` Runtime / Docs / Root Drift Convergence | `Partially Completed` | `P1` | `L2 worker Planck + L1` | 已收敛 `tmp/temp` 双口径，并用 `check_runtime_outputs.py` 增加文档口径防回归；fresh `workspace-hygiene` 后 `check_runtime_outputs.py` PASS | 继续处理非本轮主线的 runtime retention 旧工件与其他 residual drift | `runtime-outputs PASS; root-policy-alignment PASS; retention stale artifact still exists but out of current sub-scope` |
| `WS5` External Upstream Verification Closure | `Partially Completed` | `P1` | `L1 + validator` | 已用 fresh `repo-side-strict-ci --mode pr-llm-real-smoke` 把 `gemini-worker-llm-chain` 升为 `verified`，并重跑 upstream governance / freshness / same-run gates 全绿 | 保留唯一剩余 pending blocker `strict-ci-compose-image-set` 归并到 WS1/GHCR 平台边界 | `verified_blocker_rows=3; pending_blocker_rows=1` |

## 任务清单

- `[-]` 接管并校准当前 Plan 为唯一可信施工蓝图
  - 目标：停止依赖聊天记忆或旧 Plan
  - 变更对象：本 Plan 文件
  - 验证方式：fresh `git status`, `newcomer-result-proof`, `current-state-summary`, `external-lane-workflows`
  - 完成证据：状态/风险/决策已写回本文件
- `[-]` 执行 `WS1`：GHCR external distribution closure
  - 目标：判断 repo-side 是否还有可推进项，并把 current-head 外部证据向前推进
  - 变更对象：GHCR readiness truth、current-head workflow receipts、相关判读文档
  - 验证方式：fresh readiness replay + current-head workflow trigger / receipt 回读
  - 当前证据：备用 `write:packages` 账号下 package probe=404 但 blob upload=401；current-head `build-ci-standard-image` run `23272897159` 失败在 `Standard image publish preflight`
- `[-]` 执行 `WS2`：current-truth fail-close convergence
  - 目标：让 summary / pointer / current-proof 只在 current-head artifact 对齐时给出正向 current verdict
  - 变更对象：summary/render/pointer/current-proof 聚合相关脚本与文档
  - 验证方式：targeted tests + stale mismatch case
  - 当前状态：已完成并验证；summary/workflow/release lane 的 current-head 消费逻辑已修复
- `[-]` 执行 `WS3`：remote-integrity 入主链
  - 目标：把 GitHub 平台真相从异步巡检升级为 merge-relevant gate
  - 变更对象：`ci.yml`, `remote-integrity-audit.yml`, required-checks 相关渲染与判读
  - 验证方式：workflow/static checks + docs/render freshness
  - 当前状态：repo-side 改造已完成并验证；平台侧 required contexts 尚未同步收口
- `[-]` 执行 `WS4`：runtime/docs drift convergence
  - 目标：清掉 runtime-cache `tmp/temp` 口径漂移
  - 变更对象：runtime-cache docs/config/gates
  - 验证方式：相关 docs/runtime gate
  - 当前状态：`tmp/temp` 漂移子目标已完成并验证；runtime retention 旧工件噪音仍待后续单独处理

## [一] 3 分钟人话版

这个仓库现在最危险的问题，不是“代码太差”，也不是“功能不够多”，而是它已经长得很像成熟系统了，**很容易让人把 repo-side 的强治理误读成 external/public 也已经全部闭环**。

说得更直白一点：

- 厨房已经很强：`governance-audit`、`repo-side-strict-ci`、`newcomer-result-proof` 这些 repo-side 收据都已经拿到了。
- 菜单和制度也很强：文档控制面、generated docs、strict runtime contract、required checks 对齐都是真接线。
- 但外卖平台还没真正通：GHCR 标准镜像的 external lane 仍被真实权限边界卡住。
- 更糟的是，前台墙上的状态总览牌子有一部分是旧的：`current-state-summary.md` 还会把旧 HEAD 当 current state，制造“已经 external verified”的错觉。

所以这份 Plan 的唯一主路线不是“再润色一下”，而是：

1. **先打掉 external distribution 的真实 blocker。**
2. **再把 current-truth 聚合面做成 fail-close，彻底拆掉 stale summary 幻觉。**
3. **再把 GitHub 平台真相审计提升为主链阻断，不再让平台漂移藏在异步角落。**
4. **最后收口 runtime/cache/logging/upstream 的残余漂移，降低维护税。**

改完以后，这个仓库会从：

- `很强，但容易被读错`

变成：

- `分层清楚、误判难度高、下一位执行者可以直接接手施工`

必须这么硬的原因也很简单：

- 如果不先修 GHCR，就永远不能诚实地说“公开分发也闭环了”。
- 如果不先修 current-truth 聚合面，就会一直有人拿旧 summary 当 current truth。
- 如果不把 remote integrity 变成主链阻断，就会一直存在“本地很严、平台侧异步巡检”的信任缝。
- 如果不把残余 drift 和 pending 行收口，仓库会长期保持“看起来很成熟，但解释成本很高”的状态。

## [二] Plan Intake

### 输入材料范围

- 上游 `超级Review` 审计报告
- 上游 `## [十三] 机器可读问题账本` YAML
- 当前 Repo fresh gate 结果
- 当前 Repo tracked docs / workflows / configs / runtime reports
- `.agents/Plans/` 下历史 Plan，作为上下文，不作为当前事实源

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
  - `python3 scripts/governance/check_env_contract.py --strict` 通过
  - `./bin/validate-profile --profile local` 通过
  - `./bin/governance-audit --mode audit` 通过
  - `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` 通过
  - `newcomer-result-proof.json` 对齐当前 HEAD `eeaa587...`
  - `standard-image-publish-readiness.json` 当前仍是 `blocked/registry-auth-failure`
- **中置信**
  - stale summary 的刷新缺口来自哪条生成链，当前只证实“有冲突”，未 fresh 追根到具体触发点
  - GitHub 平台策略为何仍是 `allowed_actions=all`、`sha_pinning_required=false`，当前只知事实，不知组织级限制
- **低置信 / 需实施前再确认**
  - pending compat rows 的最短补证路径是否受外部 token / provider 窗口影响

### Repo archetype

- `hybrid-repo`
- 原因：
  - `apps/ + contracts/ + infra/ + integrations/` 证明它是实际运行系统
  - `bin/ + scripts/governance/ + scripts/runtime/ + config/governance/ + config/docs/` 证明治理控制面是一等公民

### 当前最真实定位

- `public source-first + limited-maintenance + dual completion lanes`
- `repo-side 强闭环`
- `external/public distribution 未完成`
- `可安全公开源码，不可诚实宣称 adoption-grade distribution`

### 最危险误判

- 把 `governance-audit PASS + repo-side strict PASS + public repo + generated docs fresh` 误判成“整个仓库已经 Final Form”

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
    - repo-side 很强
    - external distribution 的主 blocker 是 GHCR
    - docs/CI 已强 control-plane 化
    - current-truth 聚合面存在 stale seam
    - upstream 主要是 external compatibility governance，不是 git fork 治理
  </initial_claims>
  <known_conflicts>
    - 老 plan 仍带有 dirty-worktree / partial 叙事，但当前 HEAD 已 clean 且 strict fresh PASS
    - current-state-summary 与 newcomer-result-proof / external-lane-workflows 当前存在直接冲突
    - release evidence 的 repo-side readiness 与 current-head remote verified 不是一回事，不能混写
  </known_conflicts>
  <confidence_boundary>
    - GHCR blocker、高层 summary 漂移、remote-integrity 非主链阻断均为高置信
    - stale summary 的生成根因与 pending compat rows 的补证顺序需在执行时二次核对
  </confidence_boundary>
</plan_intake>
```

### 统一问题账本

| Canonical ID | Claim / Issue | Source | Repo Verification | Evidence Strength | Type | Severity | Impact | Root Cause | Final Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ISS-001` | GHCR external distribution 被 `registry-auth-failure` 阻断 | 上游 YAML + runtime report | 已验证 | A | fact | blocker | 直接阻断 adoption-grade 分发判断 | 平台写包权限未闭环 | 采纳 |
| `ISS-002` | current-state summary 与底层 current-proof 脱节 | 上游 YAML + runtime reports | 已验证 | A | fact | structural | 制造 false-green、污染所有上层结论 | 聚合层不是 fail-close | 采纳 |
| `ISS-003` | remote-integrity 审计未进入 PR 主链 required lane | 上游 YAML + workflow | 已验证 | A | fact | structural | GitHub 平台真相不能每次 PR 同步阻断 | 平台真相审计仍是异步巡检 | 采纳 |
| `ISS-004` | runtime cache 文档与机器真相 `tmp/temp` 漂移 | 上游 YAML + docs/config/live tree | 已验证 | A | fact | important | 持续制造“小治理已完成”的错觉 | docs 未随 config 收敛 | 采纳 |
| `ISS-005` | compat matrix 仍有 blocker 级 pending 行 | 上游 YAML + compat matrix | 已验证 | A | fact | important | 外部依赖治理容易被过度宣称 | 已建账但未全部 verified | 采纳 |
| `ISS-006` | GitHub 平台 actions policy 仍偏宽 | 上游 YAML + remote-platform-truth | 已验证 | B | fact | important | repo-side 严格性无法完全上升为平台 fail-close | 平台策略未同步收紧 | 采纳 |
| `CILL-001` | `remote-required-checks=pass` 被误读成 terminal closure | 上游幻觉账本 + docs | 已验证 | A | risk | structural | 会直接误导 CI 与 public 状态判断 | required-check integrity 与 terminal closure 被混读 | 采纳 |
| `CILL-002` | `current-state-summary.md` 被误读成 current truth | 上游幻觉账本 + runtime reports | 已验证 | A | risk | structural | 误报 external verified | summary 未 fail-close | 采纳 |
| `CILL-003` | upstream inventory 完整被误读成 external lanes 已闭环 | 上游幻觉账本 + compat matrix | 已验证 | A | risk | important | 夸大 upstream 健康度 | inventory 与 verified lane 未切开 | 采纳 |
| `OBS-001` | repo-side strict 已 fresh PASS | fresh command + newcomer proof | 已验证 | A | fact | fact | 决定主路线不该再浪费在 repo-side 控制面重修 | repo-side 已达当前阶段要求 | 采纳 |
| `OBS-002` | git worktree 当前 clean 且 local/remote 对齐 | fresh `git status` + prior closure note + newcomer proof | 已验证 | A | fact | fact | 允许主路线从 clean-state partial 转向 external/public 真问题 | 旧 partial 叙事已过时 | 采纳 |

## [三] 统一判断总览表

| 维度 | 当前状态 | 目标状态 | 证据强度 | 是否适用 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 项目定位 / 叙事 | 强项目、owner-level 信号明显，但 external 分发叙事不能夸满 | repo-side 强与 external 未闭环被明确切开 | A | 是 | 重点是防止过度宣称 |
| 开源边界 | 可安全公开源码，可审阅、可协作 | 继续保持 source-first，且不误报 distribution closure | A | 是 | MIT + notices + security truth 已成立 |
| 文档事实源 | `config/docs` 控制面 + generated render 面 + reference 判读面已接线 | 保持 control-plane 驱动并修复 current-truth seam | A | 是 | 当前 docs governance 已强 |
| CI 主链可信度 | trusted boundary、aggregate、final gate 都接线 | 将平台真相也纳入 merge-time fail-close | A | 是 | 当前最大缝在 remote-integrity 非主链阻断 |
| 架构治理 | hybrid repo，边界清楚，根目录与 runtime 输出受治理 | 继续降低 drift 与维护税 | A | 是 | 不需要大改架构范式 |
| 缓存治理 | `.runtime-cache` 真实成立，但 `tmp/temp` 口径有漂移 | 文档与机器真相完全收敛 | A | 是 | 这是低成本高价值修复 |
| 日志治理 | 结构化日志、sidecar、correlation 基本成立 | 补齐 trace 相关残缺，减少 `missing_trace` | B | 是 | 不是主 blocker |
| 根目录洁净 | allowlist/budget/zero-unknowns 已成立 | 继续冻结新增顶级项 | A | 是 | 不应再回退成堆场 |
| 外部依赖治理 | external upstream inventory 强，但 pending rows 仍在 | compat rows 逐步 verified | A | 是 | 不适用 git fork 故事 |
| 外部分发 / 供应链 | SBOM / attestation workflow 已设计，GHCR 仍 blocked | current-head external verified | A | 是 | 当前头号 blocker |

## [四] 根因与完成幻觉总表

| 根因 / 幻觉 | 表面信号 | 真实问题 | 对应动作 | 防回潮 Gate |
| --- | --- | --- | --- | --- |
| `R1` External distribution closure 未完成 | 仓库公开、SBOM/attestation workflow 都在 | GHCR current-head 发布仍被真实权限边界卡住 | `WS1` | GHCR readiness + external workflow current-head verify |
| `R2` Current-truth 聚合面非 fail-close | 有 current-state summary、有 generated snapshot | summary 可继续展示旧 HEAD，导致 false-green | `WS2` | current-proof contract + summary/source_commit mismatch fail-close |
| `R3` GitHub 平台真相仍是异步巡检 | remote-platform-truth / remote-required-checks 都有 | 这些检查不在 PR 主链 required lane | `WS3` | remote-integrity 入主链 + platform policy tighten |
| `R4` 剩余治理 drift 与维护税 | runtime cache、upstream inventory、logs 看起来都成熟 | docs/config drift、pending rows、trace gaps 仍在 | `WS4` + `WS5` | docs governance, runtime outputs gate, compat matrix verification |
| `ILL-1` required checks 幻觉 | `remote-required-checks=status=pass` | 只说明 aggregate-required-check integrity，不说明 terminal closure | `WS2` + `WS3` | `docs/generated/required-checks.md`, `done-model.md`, final gate |
| `ILL-2` summary 幻觉 | `current-state-summary.md` 自称 current state | 可能是旧 HEAD 的摘要 | `WS2` | summary refresh gate + source_commit guard |
| `ILL-3` inventory 幻觉 | `active-upstreams.json` / `compat report` 很完整 | inventory 完整不等于 external lanes verified | `WS5` | compat matrix same-run / freshness / blocker-row verify |

## [五] 绝不能妥协的红线

- 绝不再把 `ready`、`historical`、`required-checks pass` 写成 `verified`。
- 绝不再让任何 tracked 或 generated docs 承载 commit-sensitive current verdict，除非它本身带 fail-close 校验。
- 绝不允许 `.runtime-cache/` 以外新增长期 repo-side runtime 输出根。
- 绝不允许新增顶级未知项；根目录继续执行 allowlist / budget / zero-unknowns。
- 绝不允许新的 external provider / binary / platform 直接散落进 `apps/*`，必须先走 `integrations/` + governance registry。
- 绝不保留“临时兼容层无限期存在”的模糊说法；所有迁移桥都必须带删除条件和时间点。
- 绝不在 README / public docs 中保留会让陌生读者误解为“当前 external lane 已闭环”的旧叙事。

## [六] Workstreams 总表

| Workstream | 目标 | 关键改造对象 | 删除/禁用对象 | Done Definition | 优先级 |
| --- | --- | --- | --- | --- | --- |
| `WS1` GHCR External Distribution Closure | 关闭当前唯一 external distribution blocker | GHCR auth path, standard image readiness, external workflow receipts | 旧的“GHCR 只是 readiness 未补”叙事 | current HEAD 上 GHCR lane `verified` 或明确 fail-close 到更真实 blocker | P0 |
| `WS2` Current-Truth Fail-Close Convergence | 让 summary / pointer / current-proof 完全一致 | current-state-summary, external-lane snapshot reading rule, newcomer/current-proof aggregation | 任何把旧 summary 当 current truth 的路径 | 所有 current-facing summary 必须对 source_commit mismatch fail-close | P0 |
| `WS3` Remote Integrity Merge Gate | 把 GitHub 平台真相从异步巡检提升为主链阻断 | remote-integrity-audit workflow, ci.yml, required checks, platform policy | “push main 后再补审”的信任缝 | PR/merge 路径必须同步阻断 branch protection / required checks / platform truth 漂移 | P1 |
| `WS4` Runtime / Docs / Root Drift Convergence | 清掉 cache/root/logging 的残余口径漂移 | runtime-cache docs/config, root/runtime policy docs, logging trace gaps | `tmp/temp` 双口径和旧表述 | docs/config/live tree 口径统一，root/runtime/logging drift gate 全绿 | P1 |
| `WS5` External Upstream Verification Closure | 将 pending compat rows 压到 explicit verified 或 explicit blocked | upstream-compat-matrix, provider/external proof collection, same-run verification | 含糊的“已治理=已完成”叙事 | blocker rows 无模糊状态；都能解释为 verified / blocked / intentionally pending with rule | P1 |

## [七] 详细 Workstreams

### `WS1` GHCR External Distribution Closure

#### 目标

- 把当前 external distribution 的主 blocker 从 `registry-auth-failure` 推到真正的 current-head external verified，或者在失败时把失败边界缩到更准确的单点。

#### 为什么它是结构性动作

- 它不是“补个 workflow”，而是决定仓库能否从“安全公开源码”升级到“可诚实公开分发”的关键分水岭。
- 不解决它，所有 public / release / supply-chain 叙事都必须保守收口。

#### 输入

- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `.github/workflows/build-ci-standard-image.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `infra/config/strict_ci_contract.json`

#### 输出

- current HEAD 对齐的 GHCR readiness truth
- GHCR auth path 的唯一合法来源说明
- current-head external workflow verified receipt，或明确到 package ownership / org ACL 的最终 blocker 说明

#### 改造对象

- `.github/workflows/build-ci-standard-image.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- `docs/reference/external-lane-status.md`
- `config/governance/external-lane-contract.json`（仅当状态机语义需收紧）
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`（执行结果）

#### 删除 / 禁用对象

- 禁止继续用“预检已过所以 GHCR 大致没问题”这种中间态表达
- 禁止继续用旧 HEAD 的 successful/failed workflow 冒充当前 HEAD 的 external 结论

#### 迁移桥

- 短期允许保留 `blocked` 状态作为 current external truth
- 不允许用 `ready` 作为对外分发替代结论

#### 兼容桥删除条件与时点

- 条件：current HEAD 对应的 GHCR workflow `latest_run_matches_current_head=true` 且 lane=verified
- 时点：拿到 verified receipt 后，删除所有“当前仅 repo-side 完成，GHCR 另说”的临时解释语句

#### Done Definition

- `check_standard_image_publish_readiness.sh` 对当前 HEAD 不再报 `registry-auth-failure`
- `external-lane-workflows.json` 中 `ghcr-standard-image.latest_run_matches_current_head=true`
- 当前 HEAD 上 GHCR lane 为 `verified`
- README / external-lane-status 的外部分发口径随之更新

#### Fail Fast 检查点

- 若 token 路径依旧无 `packages:write`，立即停在平台 ACL，不继续做 repo-side 假修复
- 若 workflow 已到 current head 但失败签名变更，先重判 blocker 类型，再决定后续动作

#### 它会打掉什么幻觉

- “仓库公开 + workflow 在 => external distribution 也差不多完成”

#### 它会改变哪个上层判断

- 开源就绪：从“可安全公开源码，不可安全宣称公开分发”推进到“公开分发也可被验证”
- 招聘信号：增强 supply-chain / release discipline 说服力

---

### `WS2` Current-Truth Fail-Close Convergence

#### 目标

- 让所有 current-facing summary、pointer、reading-rule 页面与底层 runtime artifact 完全一致。
- 任何 source_commit mismatch 或 stale 聚合都必须 fail-close，而不是继续显示看起来完整的 summary。

#### 为什么它是结构性动作

- 这是全仓“完成幻觉”最核心的制造器。
- 不修它，任何强治理都会被错误读取，影响开源、CI、架构、产品化全部上层判断。

#### 输入

- `.runtime-cache/reports/governance/current-state-summary.md`
- `.runtime-cache/reports/governance/newcomer-result-proof.json`
- `.runtime-cache/reports/governance/external-lane-workflows.json`
- `config/governance/current-proof-contract.json`
- `config/governance/external-lane-contract.json`
- `docs/reference/done-model.md`
- `docs/generated/external-lane-snapshot.md`

#### 输出

- fail-close 的 current-state 聚合规则
- 明确的 source_commit mismatch 行为
- summary / pointer / reading-rule 统一口径

#### 改造对象

- 生成 current summary 的脚本与模板
- `docs/generated/external-lane-snapshot.md`
- `docs/reference/done-model.md`
- `docs/reference/newcomer-result-proof.md`
- 必要的测试文件，覆盖 stale summary 场景

#### 删除 / 禁用对象

- 禁止任何 summary 页在 mismatch 时继续写 `verified`
- 禁止 README 或 start-here 把 summary 页当当前唯一真相入口

#### 迁移桥

- 短期保留 summary 页，但在 mismatch 时只允许显示：
  - `historical`
  - `mismatch`
  - `rebuild required`

#### 兼容桥删除条件与时点

- 条件：所有 current-facing summary 都能从底层 artifact 自动构建并 fail-close
- 时点：通过相关 gate 与回归测试后，移除旧 wording fallback

#### Done Definition

- summary 对旧 HEAD 或 stale artifact 不再输出 green-like wording
- `current-state-summary` 与 `newcomer-result-proof` 在 current HEAD 上无冲突
- 所有 current-facing docs/summary 只在 current-proof 满足时给出 positive current verdict

#### Fail Fast 检查点

- 若 summary 脚本无法读取任何 required artifact，直接失败，不生成“空洞但看起来完整”的摘要
- 若 external lane 是 `historical`，不得写成 `verified`

#### 它会打掉什么幻觉

- “墙上的总览牌子是绿的，所以当前一定已经绿了”

#### 它会改变哪个上层判断

- 文档可信度：从高可信升级到更接近 fail-close
- 公开叙事：从容易被误读升级到难误读

---

### `WS3` Remote Integrity Merge Gate

#### 目标

- 把 `remote-platform-truth + remote-required-checks` 从独立审计升级为 merge-relevant required lane。
- 同步收紧 GitHub 平台侧 `allowed_actions` 与 `sha_pinning_required`。

#### 为什么它是结构性动作

- 当前 repo-side 很严，但平台真相仍有“隔壁房间才看”的异步 seam。
- 只要这个 seam 还在，branch protection / required checks / repo visibility 的 drift 就不会在每个 PR 上 fail-close。

#### 输入

- `.github/workflows/remote-integrity-audit.yml`
- `.github/workflows/ci.yml`
- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/remote-required-checks.json`
- `scripts/governance/check_remote_required_checks.py`
- `scripts/governance/probe_remote_platform_truth.py`

#### 输出

- merge-relevant 的 remote integrity gate
- 平台策略收紧清单
- 对 required checks integrity 与 platform truth 的主链阻断语义

#### 改造对象

- `.github/workflows/ci.yml`
- `.github/workflows/remote-integrity-audit.yml`
- `docs/generated/required-checks.md`
- `docs/reference/external-lane-status.md`
- 平台设置（仓库外动作，但必须写入 decision log）

#### 删除 / 禁用对象

- 禁止“push main 后再巡检”的主叙事
- 禁止把远端完整性仅当作月度健康检查

#### 迁移桥

- 在平台策略未收紧前，允许 repo-side `ci_workflow_strictness_guard` 继续作为第一道防线
- 但 PR 主链必须已经能看到 remote integrity 结果

#### 兼容桥删除条件与时点

- 条件：remote integrity 已进入 required lane，且平台策略收紧到目标状态
- 时点：新的 required lane 稳定运行并通过至少一次 current HEAD 验证后

#### Done Definition

- PR / merge 路径上能同步阻断 remote required checks mismatch
- PR / merge 路径上能同步阻断关键 GitHub 平台真相失配
- `allowed_actions` 与 `sha_pinning_required` 达到目标策略，或有书面化无法调整的组织级例外说明

#### Fail Fast 检查点

- 若组织策略限制导致平台设置无法收紧，必须写成显式例外，不得沉默缺席
- 若 remote platform truth 获取失败，主链直接红灯，不允许跳过

#### 它会打掉什么幻觉

- “repo-side CI 很严，所以 GitHub 平台侧也一定同样严格”

#### 它会改变哪个上层判断

- CI 可信度：从 A- 提升到更接近 A/A+
- Trusted CI：从“强”升级到“更接近平台级 fail-close”

---

### `WS4` Runtime / Docs / Root Drift Convergence

#### 目标

- 清理非主 blocker 但持续制造维护税的治理漂移，特别是 runtime cache / root / logging 口径分裂。

#### 为什么它是结构性动作

- 这些问题单独看不大，但会长期制造“看起来整齐，实际需要解释”的成本。
- 它们也是下一轮 agent 最容易被误导的地方。

#### 输入

- `docs/reference/runtime-cache-retention.md`
- `config/governance/runtime-outputs.json`
- `config/governance/root-runtime-policy.json`
- `docs/reference/root-governance.md`
- `.runtime-cache/logs/**/*.jsonl`
- `.runtime-cache/logs/**/*.meta.json`

#### 输出

- runtime cache、root runtime policy、logging correlation 的统一口径
- 更少的 manual explanation

#### 改造对象

- `docs/reference/runtime-cache-retention.md`
- `docs/reference/root-governance.md`
- `docs/reference/logging.md`
- `config/governance/runtime-outputs.json`（仅当 docs 不是错的而 config 才需要改）
- logging/correlation tests 与 governance checks

#### 删除 / 禁用对象

- 禁止继续保留 `tmp/temp` 双口径
- 禁止对 `missing_trace` 之类的相关性缺口只做口头解释不补 guard

#### 迁移桥

- 允许短期通过 docs 注释明确“旧口径已废弃”

#### 兼容桥删除条件与时点

- 条件：docs/config/live tree/log sample 完全同口径
- 时点：通过 docs governance + runtime governance gate 后

#### Done Definition

- runtime cache 文档与 config/live tree 无冲突
- root/runtime policy 文档与 gate 行为一致
- logging trace/correlation 缺口要么被修复，要么被显式降级分类并有 guard

#### Fail Fast 检查点

- 若某 drift 是设计需要而非错误，必须写入 control plane，不可只在 docs 里口头解释

#### 它会打掉什么幻觉

- “仓库很整齐，所以机器真相也一定完全一致”

#### 它会改变哪个上层判断

- 架构治理成熟度
- onboarding 成本
- 未来 agent 误读概率

---

### `WS5` External Upstream Verification Closure

#### 目标

- 把 external upstream compatibility governance 从“inventory 很全”推进到“pending 行解释清楚、关键 blocker 行逐步 verified”。

#### 为什么它是结构性动作

- 当前 upstream 叙事已经很强，但最容易被误读成“既然建账了，就差不多都完成了”。
- 这会污染开源 readiness、产品成熟度与维护成本判断。

#### 输入

- `config/governance/active-upstreams.json`
- `config/governance/upstream-compat-matrix.json`
- `.runtime-cache/reports/governance/upstream-compat-report.json`
- `docs/reference/upstream-governance.md`
- `bin/upstream-verify`

#### 输出

- 每条 pending blocker row 的唯一解释
- verified / blocked / intentionally pending 的明确分类
- same-run / freshness / lane separation 的补证计划

#### 改造对象

- `config/governance/upstream-compat-matrix.json`
- `docs/reference/upstream-governance.md`
- provider/external verification scripts
- 必要时 current-state/external-lane 判读文档

#### 删除 / 禁用对象

- 禁止再用 inventory 完整度代表 compat closure

#### 迁移桥

- 允许 pending 行存在，但必须有：
  - lane
  - last verified run
  - why pending
  - what unblocks it

#### 兼容桥删除条件与时点

- 条件：所有 blocker rows 都有无歧义 current classification
- 时点：至少 blocker rows 不再出现“既像已完成、又像未完成”的语义模糊

#### Done Definition

- `upstream-compat-matrix` 中 blocker rows 只有三种清晰状态：
  - verified
  - blocked
  - intentionally pending with explicit rule
- 文档与 report 不再把 inventory completeness 写成 maturity completion

#### Fail Fast 检查点

- 若某 row 无法在当前周期内补证，必须降级为 explicit pending/blocker，不得维持暧昧 wording

#### 它会打掉什么幻觉

- “有 active-upstreams 台账，所以 external upstream 已经健康”

#### 它会改变哪个上层判断

- upstream 健康度判断
- external/public readiness 判断

## [八] 硬切与迁移方案

### 立即废弃项

- 废弃任何把 `current-state-summary.md` 当当前唯一真相源的叙事
- 废弃任何把 `remote-required-checks=pass` 写成 terminal closure 的表达
- 废弃任何把 `ready` 或旧 HEAD remote success 写成当前 external verified 的表达
- 废弃 `tmp/temp` 双口径并存的 docs 说法

### 迁移桥

- `current-state-summary.md` 保留，但在 mismatch 时只允许输出 fail-close 信息
- `external-lane-snapshot.md` 保留 pointer 角色，不提升为 current verdict 载体
- compat pending 行允许短期存在，但必须显式写出 why pending / how to verify

### 禁写时点

- 从 `WS2` 开工起，任何 summary / doc / report 都不得新增“verified”字样，除非 current-head artifact 明确支撑
- 从 `WS4` 开工起，任何新文档都不得再写 `temp/` 分舱，统一只认最终口径

### 只读时点

- 老的 historical release evidence 继续保留只读，不允许作为 current verdict surface 被重新包装

### 删除时点

- `WS2` 完成后，删除 summary 中所有能在 mismatch 时继续看起来像正向 verdict 的 fallback
- `WS4` 完成后，删除 `tmp/temp` 双口径遗留文本
- `WS3` 完成后，删除“remote integrity 独立巡检即可”的过渡性说明

### 防永久兼容机制

- 所有迁移桥必须绑定 gate：
  - source_commit mismatch => fail-close
  - docs drift => fail
  - compat pending without rule => fail
- 所有过渡语义都必须写入 decision log，不允许默认永久保留

## [九] 验证闭环与 Gate

| 维度 | 验证项 | Gate / 命令 / CI / Policy | 通过条件 | 未通过意味着什么 |
| --- | --- | --- | --- | --- |
| Repo-side 完成 | env / newcomer / governance / strict | `python3 scripts/governance/check_env_contract.py --strict`; `./bin/validate-profile --profile local`; `./bin/governance-audit --mode audit`; `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` | 全部 fresh PASS，且 current-head 对齐 | repo-side 仍未完全站稳 |
| current truth | summary / newcomer / workflow receipts 一致 | current-proof contract + summary rebuild + targeted tests | source_commit 一致；mismatch 时 fail-close | 仍存在 false-green 风险 |
| public surface | open-source pack / security / notices / freshness | `env-governance.yml`; `check_open_source_audit_freshness.py`; remote platform probe | MIT / notices / gitleaks freshness / PVR truth 对齐当前 HEAD | 不可安全对外宣称 public-readiness |
| external distribution | GHCR lane | `./scripts/ci/check_standard_image_publish_readiness.sh`; `build-ci-standard-image.yml` current-head receipt | status=verified 且 current-head 匹配 | 不能宣称公开分发闭环 |
| docs 事实源 | control plane / render freshness / semantic invariants | `python3 scripts/governance/check_docs_governance.py`; `scripts/governance/ci_or_local_gate_doc_drift.sh` | control plane、render、manual boundary 全绿 | 文档可信度不足 |
| required checks integrity | generated required checks vs branch protection | `python3 scripts/governance/check_remote_required_checks.py` | missing/extra contexts 为空 | GitHub branch protection 与 repo truth 漂移 |
| trusted CI | untrusted PR blocked before self-hosted | `.github/workflows/ci.yml` `trusted-pr-boundary` + GitHub Actions run | fork/untrusted PR 不进入 privileged self-hosted 路径 | trusted CI 是假象 |
| remote platform truth | visibility / branch protection / actions policy / security features | `./bin/remote-platform-probe --repo ...` | current-head report fresh，关键字段满足目标策略 | 平台真相不可作为 current proof 使用 |
| root allowlist | 顶级项 / 本地私有容忍 / runtime root | `check_root_zero_unknowns.py`; `check_root_policy_alignment.py` | 无未知顶级项，无非法 runtime residue | 根目录治理回潮 |
| runtime outputs | `.runtime-cache` 唯一合法 runtime root | `check_runtime_outputs.py`; runtime outputs config | 输出根、分舱、TTL、sidecar 一致 | cache/runtime 治理是假成熟 |
| logging correlation | run_id/trace_id/request_id/gate_run_id 等字段 | `check_structured_logs.py`; `check_log_correlation.py` 等 | 关键通道字段齐全，缺口被显式处理 | 日志体系难以诊断 |
| upstream compat | blocker rows 分类清晰 | `bin/upstream-verify`; compat freshness/same-run checks | verified / blocked / explicit pending 清晰 | external dependency 治理仍模糊 |

## [十] 执行时序总表

| 阶段 | 动作 | 前置条件 | 并行性 | 完成标志 | 风险 |
| --- | --- | --- | --- | --- | --- |
| Phase 1 | `WS1` GHCR external blocker 定位与 current-head receipt 追平 | 当前 HEAD clean，repo-side strict fresh PASS | 可与 `WS2` 的纯文档/聚合设计并行，但最终合流前要统一 verdict 语义 | GHCR lane 取得 verified 或更精确 blocker | 受平台 ACL / token 约束 |
| Phase 2 | `WS2` current-truth fail-close 聚合收口 | 需要当前底层 runtime artifacts 可读 | 可与 `WS1` 并行设计，但提交时要等待 GHCR 实际状态 | summary/source_commit 行为一致并有测试 | 若误删旧 pointer 可能影响阅读流 |
| Phase 3 | `WS3` remote integrity 入主链 + 平台策略收紧 | 需先明确 `WS2` 的 current-truth 语义 | 部分可并行：workflow 改造与平台设置申请可并行 | remote truth 成为 merge-relevant gate | 可能受组织级 GitHub policy 限制 |
| Phase 4 | `WS4` runtime/docs/root drift 收口 | `WS2` 已确定哪些 summary 是 current-truth，哪些是 pointer | 可并行处理 docs/config/logging 三个子面 | `tmp/temp`、logging 缺口、root/runtime docs 口径统一 | 容易被误当次要而拖延 |
| Phase 5 | `WS5` compat pending 行闭环 | `WS1-WS3` 已固定 external/platform truth 语义 | 可按 row 并行补证，但 blocker rows 优先 | compat rows 只有 verified/blocked/explicit pending | 受 provider/time-window 影响 |
| Phase 6 | Narrative hardening / public wording finalize | 前 5 个阶段至少完成 P0/P1 | 不建议提前 | README / docs / summaries 叙事与真实能力完全对齐 | 若过早改写，易再次失真 |

## [十一] 改造动作 -> 上层判断改变 映射表

| 动作 | 改变什么判断 | 为什么 |
| --- | --- | --- |
| 关闭 GHCR blocker | 开源 readiness / public distribution 判断 | 决定是否能从 source-first 走向可验证分发 |
| 修复 current-truth 聚合面 | 文档可信 / 完成语义可信 / public 叙事可信 | 防止 stale summary 继续制造 false-green |
| 把 remote integrity 纳入主链 | CI 可信度 / trusted CI 判断 | 平台真相不再是异步 seam |
| 对齐 runtime/docs drift | 架构治理成熟度 / onboarding 成本 | 降低解释税与 future agent 误读 |
| 收口 compat pending 行 | upstream 健康度 / external maturity 判断 | “已建账”不再被误读成“已闭环” |

## [十二] 如果只允许做 3 件事，先做什么

### 1. 先做 `WS1` GHCR External Distribution Closure

- **为什么先做**
  - 这是唯一明确的 external/public blocker
- **打掉什么幻觉**
  - “仓库公开了，所以公开分发也差不多好了”
- **释放什么能力**
  - 让外部分发与 supply-chain 叙事可以诚实升级

### 2. 再做 `WS2` Current-Truth Fail-Close Convergence

- **为什么第二**
  - 这是所有高层判断的读数表
- **打掉什么幻觉**
  - “总览牌子是绿的，所以现在一定是绿的”
- **释放什么能力**
  - 让所有 public / docs / CI / completion 判断重新可信

### 3. 第三做 `WS3` Remote Integrity Merge Gate

- **为什么第三**
  - 这一步把 repo-side 的严谨性提升到平台边界
- **打掉什么幻觉**
  - “本地/仓库里很严，所以 GitHub 平台也一定一样严”
- **释放什么能力**
  - 让 CI 信任边界从强，升级到更接近 fail-close

## [十三] 不确定性与落地前核对点

- **高置信事实**
  - 当前 HEAD `eeaa587...` clean 且 repo-side strict fresh PASS
  - GHCR current external distribution 仍 blocked
  - current-state-summary 与底层 runtime reports 存在冲突
  - remote integrity 仍是独立 workflow
- **中置信反推**
  - current-state-summary 的 stale 根因来自聚合刷新链缺口
  - GitHub 平台 policy 可以被进一步收紧，而不是完全受限于组织
- **落地前需二次核对**
  - stale summary 的具体生成入口与刷新触发条件
  - GHCR package ownership / token path 的最终修复方式
  - pending compat rows 哪些适合并行补证，哪些必须等 WS1/WS3 稳定后再做
- **但不能因此逃避设计**
  - 主路线已经足够明确：先 external blocker，再 truth seam，再 platform gate，再治理 drift

## [十四] 执行准备状态

### Current Status

- `git status --short --branch` 当前处于多文件施工态，不再是单纯“只有 Plan 文件未纳入仓库记录”
- HEAD = `eeaa58784f9363781543d0eca1a4713665897d54`
- repo-side:
  - `check_env_contract` PASS
  - `validate-profile` PASS
  - `governance-audit` PASS
  - `repo-side-strict-ci` PASS
- external:
  - GHCR readiness `blocked/registry-auth-failure`
  - release evidence repo-side readiness `ready`
  - `release-evidence-attestation` remote workflow current-head `verified`
  - `ghcr-standard-image` remote workflow current-head `blocked`
  - `remote-required-checks` current runtime truth `blocked`（missing `remote-integrity` in remote branch protection）
- current-truth seam:
  - `current-state-summary.md` 已对齐当前 HEAD `eeaa587...`
  - `current-state-summary.md` 对 `workflow:ghcr-standard-image` / `workflow:release-evidence-attestation` 的 current-head 状态渲染已修正
  - `current-state-summary.md` 现在也会诚实显示 `remote-required-checks=blocked`
  - 当前 remaining seam 已从“summary stale”收敛为“worktree 真实处于多文件施工态 + 远端 platform contexts 未同步”

### Next Actions

1. 将剩余唯一未闭环项收口为真实边界：`WS1` / `strict-ci-compose-image-set` / `remote-required-checks` 平台同步都受同一“未提交生效 + 远端 branch protection 未更新 / GHCR 写权限未打通”的边界约束。
2. 若下一轮获得 commit/push 授权，先推送当前 repo-side 改动，再同步 GitHub branch protection required contexts，最后重跑 `check_remote_required_checks.py` 与 GHCR workflow。
3. 若下一轮仍无远端生效权限，则保持 repo-side 已完成状态，不再在本地重复空转 GHCR/platform blocker。

### Decision Log

- `2026-03-18 16:49 America/Los_Angeles`：正式接管本 Plan 作为唯一施工蓝图；执行状态从 `Ready For Execution` 升级到 `In Progress`。原因：已经开始按 Workstream 实际施工，后续一切状态更新只以本文件为准。未选替代方案：继续依赖上一轮聊天文本或旧 Plan。影响：全局状态机统一到本文件。
- `2026-03-18 16:49 America/Los_Angeles`：校准 live worktree 状态为“仅本 Plan 文件新增导致 dirty”，不再沿用“worktree 干净”的旧描述。原因：fresh `git status --short --branch` 显示只有本文件为未跟踪变更；若不写回，会让 Plan 与 Repo 实际状态失真。未选替代方案：口头说明而不回写。影响：后续 clean/dirty 判断都必须把“Plan 自身新增未入库”单独列账。
- `2026-03-18 16:49 America/Los_Angeles`：确认 `WS1` 仍是最高优先级，但执行策略改为“先判断是否还有 repo-side 可推进项，再把纯外部权限阻塞留在 blocker 台账中”。原因：fresh 读取显示 GHCR readiness 仍 blocked，但也暴露 `source_commit=null` 等收据层异常，需要先排除 repo-side 解释面缺口。未选替代方案：直接把 WS1 完全外包给平台条件后停工。影响：WS1 本地主链继续，WS2/WS3/WS4 可并行推进。
- `2026-03-18 16:56 America/Los_Angeles`：完成 WS1 的最小暴露面备用账号复核。结果：在本机现有 `terryyifeng` 账号（具 `write:packages`）下，GHCR package API 仍只返回 404，blob upload probe 返回 401；因此 WS1 的真实边界已从“可能缺少本地 token path”收紧为“存在可用 token，但平台 blob 写权限仍未打通”。未选替代方案：继续在 repo-side 假设“只是脚本没走到正确 token”。影响：WS1 接下来转向触发 current-head 远端 workflow 获取更强外部证据，同时不再把本地 token path 当主嫌疑。
- `2026-03-18 16:58 America/Los_Angeles`：已触发 current-head 的 `build-ci-standard-image.yml` 与 `release-evidence-attest.yml`。结果：`release-evidence-attest` 当前 HEAD run `23272897723` 成功；`build-ci-standard-image` 当前 HEAD run `23272897159` 失败，失败 job=`publish`，失败 step=`Standard image publish preflight`。未选替代方案：继续依赖旧 head 历史 workflow 结果。影响：WS1 的 current-head 外部证据已就位，可把 GHCR 阻塞正式标记为真实平台 blocker。
- `2026-03-18 16:59 America/Los_Angeles`：fresh 执行 `probe_external_lane_workflows.py` 与 `render_current_state_summary.py` 后，发现 `external-lane-workflows.json` 已对齐当前 HEAD，但 `current-state-summary.md` 仍把 `workflow:*` 行渲染为 historical，且 `release-evidence-attestation` 仍显示 `ready` 而非 `verified`。未选替代方案：把 summary 误差继续当“只是旧产物没刷新”。影响：WS2 从“语义增强”升级为明确的 repo-side 渲染/聚合缺陷修复。
- `2026-03-18 17:04 America/Los_Angeles`：WS4 的 `tmp/temp` 漂移已经被 repo-side 收口：文档改为只认 `tmp/`，`check_runtime_outputs.py` 增加 docs-vs-config 防回归检查，fresh `workspace-hygiene --apply` 后 `check_runtime_outputs.py` PASS。未选替代方案：只改文档而不让 gate 审文档口径。影响：WS4 的 runtime-cache 口径子目标已闭合，但 retention 旧工件仍单列为后续噪音。
- `2026-03-18 17:07 America/Los_Angeles`：WS3 的 repo-side merge-gate 改造已完成：`remote-integrity-audit.yml` 改为 `workflow_call + workflow_dispatch`，`ci.yml` 已消费这条 remote-integrity lane，docs/generated/required-checks 与 external-lane-status 语义已同步收紧。未选替代方案：继续保留 `push main` 后异步巡检为主叙事。影响：WS3 可以从进行中降为“repo-side 已完成，平台侧待收口”。 
- `2026-03-18 17:08 America/Los_Angeles`：WS2 的 current-truth fail-close 已完成并验证：新增 `scripts/governance/check_current_state_summary.py`，修正 `render_current_state_summary.py` 对 fresh external workflow 结果的消费逻辑，fresh rerender 后 summary 与 runtime artifacts 一致。未选替代方案：继续把 summary 问题当成 docs wording 小修。影响：WS2 可正式标记为 `Verified`，summary 幻觉不再是当前 repo-side 未修缺陷。
- `2026-03-18 17:15 America/Los_Angeles`：校准当前 worktree 语义：现在已不是“仅 Plan 文件导致 dirty”，而是进入真实多文件施工态，至少包含 WS2/WS3/WS4 的 repo-side 代码与文档改动。未选替代方案：继续沿用早前的“只有 Plan 文件未跟踪”描述。影响：current-state-summary 中 `worktree dirty=true` 现在是诚实状态，后续 clean-state 相关说法必须等待这些变更提交/清理后再升级。
- `2026-03-18 17:16 America/Los_Angeles`：确认 WS3 的 remaining gap 不只是“平台策略待收紧”，还包括“本地 workflow 改造尚未通过 commit/push 进入远端默认分支，因此 branch protection required contexts 当前不可能立刻反映新 `remote-integrity` context”。未选替代方案：把这个限制误写成 repo-side 未完成。影响：WS3 保持 `Partially Completed`，并把“未获授权 commit/push”视为当前能力边界之一。
- `2026-03-18 17:22 America/Los_Angeles`：WS5 取得真实推进：`./bin/repo-side-strict-ci --mode pr-llm-real-smoke` fresh PASS，`pr-llm-real-smoke-result.json.meta.json` 给出 current-head run id `cea93c0b9a2b46b3916d356d0372525b`。据此把 `config/governance/upstream-compat-matrix.json` 中 `gemini-worker-llm-chain` 从 `pending` 升为 `verified`，并重跑 `check_upstream_governance.py`、`check_upstream_compat_freshness.py`、`check_upstream_same_run_cohesion.py` 全部 PASS。未选替代方案：继续把该行保持为模糊 pending。影响：WS5 从 `Not Started` 升为 `Partially Completed`，当前只剩 `strict-ci-compose-image-set` 一个 pending blocker 行。
- `2026-03-18 17:28 America/Los_Angeles`：根据 reviewer 提示补上 non-workflow 行的 summary fail-close 覆盖：`check_current_state_summary.py` 现在会校验 `remote-platform-integrity` 与 `remote-required-checks` 两条聚合行是否与底层 runtime report 一致；在 fresh `check_remote_required_checks.py` 将 report 打成 `blocked` 后，重新渲染 summary，当前 `current-state-summary.md` 已诚实显示 `remote-required-checks=blocked`。未选替代方案：只在 Plan 里口头记账，不让 summary 自己变诚实。影响：reviewer 指出的 repo-side blocker 已解除，剩下的 `remote-required-checks` 红灯被收口为平台同步边界而非 summary 漏报。
- `2026-03-18 17:31 America/Los_Angeles`：fresh `runtime-cache-maintenance --apply` 清除了 ttl-expired runtime artifacts，随后 `./bin/governance-audit --mode audit` 对当前 worktree 再次 PASS。未选替代方案：把 runtime-cache 过期工件留给下轮。影响：本轮 repo-side 可修红灯已全部收口，剩下的未闭环项只剩外部/平台边界。
- 决定不再把 repo-side 控制面当主战场，因为 fresh strict 已 PASS。
- 决定以 external blocker / current-truth seam / remote-integrity seam 为唯一主路线。
- 决定不输出多方案，避免把治理裁决外包给下轮执行者。

### Validation Log

- `python3 scripts/governance/check_env_contract.py --strict` => PASS
- `./bin/validate-profile --profile local` => PASS
- `./bin/governance-audit --mode audit` => PASS
- `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` => PASS
- `current-state-summary.md` 与 `external-lane-workflows.json` / `newcomer-result-proof.json` 交叉比对 => 证实 stale summary seam
- `git status --short --branch` => only `?? .agents/Plans/2026-03-18_16-41-47__repo-ultimate-verified-execution-master-plan.md`
- `standard-image-publish-readiness.json` => `status=blocked`, `blocker_type=registry-auth-failure`, `source_commit=null`
- `external-lane-workflows.json` => `ghcr-standard-image.latest_run_matches_current_head=false`
- `external-lane-workflows.json` => `release-evidence-attestation.latest_run_matches_current_head=false`
- 备用 `write:packages` 账号最小暴露面复核 => `token_mode=ghcr-token`, `token_scope_ok=true`, `package_probe_status=404`, `blob_probe_status=401`, 仍 `status=blocked`
- `gh workflow run build-ci-standard-image.yml --ref main` => current-head run `23272897159`, `conclusion=failure`
- `gh workflow run release-evidence-attest.yml --ref main -f release_tag=v0.1.0` => current-head run `23272897723`, `conclusion=success`
- `python3 scripts/governance/probe_external_lane_workflows.py` => PASS；`ghcr-standard-image: blocked run_id=23272897159`, `release-evidence-attestation: verified run_id=23272897723`
- `python3 scripts/governance/render_current_state_summary.py` => regenerated summary but still rendered stale workflow semantics
- `python3 scripts/governance/check_current_proof_commit_alignment.py` => PASS (6 artifacts)
- `python3 scripts/governance/check_current_state_summary.py` => PASS
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/governance/check_docs_governance.py` => PASS
- `python3 scripts/governance/render_docs_governance.py --check` => PASS
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run pytest apps/worker/tests/test_external_proof_semantics.py -q` => PASS (7 passed, 2 warnings)
- `PYTHONPATH="$PWD:$PWD/apps/worker" uv run pytest apps/worker/tests/test_docs_governance_control_plane.py -q` => PASS (8 passed, 2 warnings)
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/governance/check_runtime_outputs.py` => PASS
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/governance/check_root_policy_alignment.py` => PASS
- `./bin/workspace-hygiene --apply` => PASS（两次，用于清理 `.venv` 与 `__pycache__` 现场残留）
- `git status --short` => 当前已进入多文件施工态，变更范围覆盖 WS2/WS3/WS4 相关 workflow/docs/scripts/tests
- `./bin/repo-side-strict-ci --mode pr-llm-real-smoke` => PASS
- `python3 scripts/governance/check_upstream_governance.py` => PASS
- `python3 scripts/governance/check_upstream_compat_freshness.py` => PASS (`verified_rows=6 skipped_non_verified=1`)
- `python3 scripts/governance/check_upstream_same_run_cohesion.py` => PASS (`verified_blocker_rows=3 pending_blocker_rows=1`)
- `python3 scripts/governance/check_remote_required_checks.py` => FAIL (`missing required checks: remote-integrity`)；该红灯已被 fresh 写回 runtime report 与 current-state summary
- `python3 scripts/governance/render_current_state_summary.py && python3 scripts/governance/check_current_state_summary.py` => PASS（在 `remote-required-checks=blocked` 场景下仍诚实通过）
- `./bin/runtime-cache-maintenance --apply` => PASS
- `./bin/governance-audit --mode audit` => PASS

### Risk / Blocker Log

- `P0`: GHCR `registry-auth-failure`
- `P2`: runtime cache `tmp/temp` drift
- `P2`: compat matrix 仍剩 1 条 pending blocker row（`strict-ci-compose-image-set`）
- `P2`: 当前 worktree 进入多文件施工态；在未 commit / 未清理前，任何 clean-state 结论都只能保守处理
- `P1`: GHCR lane 当前缺的已不是“找不到本地 token path”，而是 blob upload 仍被平台 401/403 拒绝；后续本地 repo-side 修补空间明显缩小
- `P2`: `uv run pytest` 会在根目录重新生成 `.venv` 与若干 `__pycache__`；每次验证后都必须执行 `./bin/workspace-hygiene --apply` 收口现场
- `P1`: WS3 的平台侧最终生效还依赖后续 commit/push 与 branch protection 同步；在当前“未获授权提交/推送”的边界下，它不能被宣称 fully verified
- `P1`: 剩余唯一未闭环的 upstream blocker `strict-ci-compose-image-set` 与 WS1 共用同一 GHCR/platform 写权限边界，当前 repo 内继续打转价值很低
- `P1`: `remote-required-checks=blocked` 现在是诚实红灯，不再是 summary 漏报；但它的解除依赖远端 branch protection 真正加入 `remote-integrity` 上下文，这同样超出当前无 commit/push 授权的能力边界

### Files Planned To Change

- `.github/workflows/build-ci-standard-image.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/remote-integrity-audit.yml`
- `scripts/ci/check_standard_image_publish_readiness.sh`
- summary / current-proof 渲染脚本
- `docs/reference/done-model.md`
- `docs/reference/external-lane-status.md`
- `docs/reference/newcomer-result-proof.md`
- `docs/generated/external-lane-snapshot.md`
- `docs/reference/runtime-cache-retention.md`
- `config/governance/external-lane-contract.json`（如需）
- `config/governance/current-proof-contract.json`（如需）
- `config/governance/upstream-compat-matrix.json`
- `.agents/Plans/2026-03-18_16-41-47__repo-ultimate-verified-execution-master-plan.md`
