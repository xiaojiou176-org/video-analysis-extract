# Value Proof

这页先讲人话：它不是在数“这个仓库有多少模块”，而是在回答一个更朴素的问题:

> 如果你只是想做个视频摘要脚本，为什么还要保留这套 API + Worker + MCP + Web + evidence 的复杂度？

换句话说，这页是“价值证明页”，不是“宣传页”。它要让陌生读者在不听作者口头解释的情况下，看懂这套系统到底解决了哪些真实任务，以及它比更简单的替代方案多出了什么。

## How To Read This Page

可以把这页理解成“项目版病例摘要”：

- `baseline` 像“只退烧、不查病因”的简化做法，能勉强解决一点问题，但后续很难复盘。
- `after` 是这套仓库做完后的状态，重点不是更炫，而是**结果可复核、失败可解释、边界可说明**。
- `limitations` 像药品说明书里的副作用提醒，专门防止把“能证明什么”夸大成“什么都证明了”。

详细 case pack 见 [Task Result Proof Pack](../proofs/task-result-proof-pack.md)。

搭配阅读建议：

- 如果你想确认“当前 HEAD 的 repo-side newcomer / strict 收据今天拿到没有”，先看 [newcomer-result-proof.md](./newcomer-result-proof.md)。
- 如果你想确认“外部世界今天认不认账”，看 [external-lane-status.md](./external-lane-status.md) 和 runtime-owned `current-state-summary.md`。
- 如果你想确认“这套系统靠哪些 representative cases 证明自己有任务价值”，继续看 [Task Result Proof Pack](../proofs/task-result-proof-pack.md)。

## Current-safe Reading Rule

This page is intentionally **not** a current-run verdict page.

Use it like this:

- `value-proof.md` answers **why these representative results are worth caring about**,
- `Task Result Proof Pack` answers **which public-safe cases support that story**,
- `newcomer-result-proof.json` answers **whether repo-side proof is current for this head**,
- and `current-state-summary.md` answers **whether the current workspace and external lanes are actually closed today**.

In plain English:

- this page proves the repository has a meaningful task shape,
- it does **not** prove that today's external world has already accepted every claim,
- and it does **not** let a historical sample impersonate a current result.

## Why This Page Exists

- 防止把“治理很强、文档很全”误讲成“任务结果一定很硬”。
- 给 README、项目定位页、面试讲解和 reviewer 审阅提供一个统一的任务级证据入口。
- 把“为什么这套复杂度值得存在”讲成可检查的 case，而不是一句“工程化更强”。
- 明确区分“真实执行结果”与“fallback/noop 让流程看起来没坏”这两种完全不同的信号。

## Summary Matrix

| Case | 要解决的真实任务 | 更简单的 baseline | 这套仓库多出来的价值 | 当前最重要的边界 |
| --- | --- | --- | --- | --- |
| 1 | 持续发现新内容并稳定入队 | 手工盯站点、零散脚本轮询 | 订阅拉取、幂等去重、job 入队、后续处理链自动衔接 | 不等于所有外部源都永久稳定 |
| 2 | 把单条视频/文章变成结构化 digest | 一次性摘要、零散笔记 | 大纲、摘要、embedding、artifact 写入走同一条流水线 | 不等于 live provider 质量已经全闭环 |
| 3 | 失败时知道坏在哪 | 只看到“没出结果” | step ledger、degradations、evidence index 让失败可追溯 | 仍需要真实运行时证据才能判当前 run |
| 4 | 改 prompt/tool path 后判断质量有没有退化 | 肉眼抽查、感觉还行 | golden set、rubric、baseline、deterministic regression 可判进退 | 不是 provider-heavy live benchmark |
| 5 | 给陌生读者展示结果又不泄露不该公开的东西 | 直接贴原始截图、原始探针文件、历史样例 | public-safe 样本 + explicit boundary note，可看又不乱承诺 | 样本是代表性说明，不是 current external verdict |

## The Five Representative Cases

### Case 1: 订阅源到稳定入队

- `before`
  - 更像“自己记得去看一下频道有没有更新”。
  - 就算有脚本，也容易卡在重复拉取、失败重试、哪条内容已经处理过说不清。
- `after`
  - `Poll Workflow` 会拉取订阅 RSS、标准化 entry、写入 `videos` / `ingest_events` / `jobs`，再为新 job 启动 `ProcessJobWorkflow`。
  - 这让“发现新内容”不再只是拉下一条链接，而是进入可追踪、可重跑、可继续处理的系统通道。
- `why it matters`
  - 真正难的不是“抓到一个链接”，而是**长期持续跑**时还能知道哪些内容是新的、哪些失败了、哪些已经处理过。
- `limitations`
  - 这证明的是 repo 内的发现与入队设计，不证明外部平台永远稳定，也不证明所有 feed 在任何环境都能成功。

### Case 2: 单条内容到结构化 digest

- `before`
  - 更像一次性把视频看完后写一段总结，内容能看，但以后很难复用。
- `after`
  - `Process Workflow` 会按 `content_type` 走 video 9-step 或 article 5-step，把 `llm_outline`、`llm_digest`、`build_embeddings`、`write_artifacts` 收进同一条流水线。
  - 读模型还能稳定暴露 `summary_md`、`artifacts_index`、`content_type`、`steps` 等字段，让结果可被 API / MCP / Web 共同消费。
- `why it matters`
  - 这让输出不再只是“一段摘要文本”，而更像“带目录、带出处、可继续检索的知识资产”。
- `limitations`
  - 这页只能证明处理链设计与 repo-side 质量约束，不证明任何一次 live provider 输出都一定完美。

### Case 3: 失败路径也能复盘

- `before`
  - 很多脚本系统的失败长这样：命令红了，但没人知道是第几步坏了、有没有半成功、现场证据在哪。
- `after`
  - `jobs.status`、`sqlite.step_runs.status`、`degradations`、`.runtime-cache/reports/evidence-index/<run_id>.json` 会把“哪一步失败、哪些是降级完成、证据在哪”串起来。
  - 失败路径也要求进入同一套 manifest、metadata 与 evidence index，而不是只在 success path 看起来整齐。
- `why it matters`
  - 这就像快递丢件后不只是说“送件失败”，而是能看到“卡在分拣、运输还是签收”，后续才有修复价值。
- `limitations`
  - 这套能力依然依赖真实 run 写出新鲜证据；单看文档合同，不等于当前这一刻某条具体任务已经跑通。

### Case 4: AI 质量回归可以被判定

- `before`
  - 改 prompt、tool path 或 guardrail 后，团队常见做法是“随手看两条输出，感觉还行”。
- `after`
  - 仓库保留了 `golden set + rubric + baseline + deterministic regression` 最小 formal eval 套件，能判断 structured outline、grounded digest、citation hygiene、failure honesty 是否退化。
- `why it matters`
  - 对 LLM 系统来说，最贵的不是第一次做出一个像样结果，而是**第十次修改后还能知道自己有没有悄悄变差**。
- `limitations`
  - 这是 repo-side deterministic regression，不是 provider-heavy live benchmark，也不能替代真实线上稳定性验证。

### Case 5: 对外展示结果时还能守住 public-safe 边界

- `before`
  - 最容易出现的假成熟，是把原始探针文件、历史 release 样例、旧截图直接贴出来，让人误以为那就是当前官方结果。
- `after`
  - 仓库只允许 public-safe 的样本进入 tracked public tree，例如 `public_probe_summary.sample.tsv` 这种合成化摘要，或带 `historical-example` 标记的历史 manifest。
  - 这让 reviewer 有“看得见的东西”，又不会把真实路由、对象标识或旧证据误读成当前结论。
- `why it matters`
  - 对 public source-first 仓库来说，能展示什么、不能展示什么，本身就是结果证明的一部分。
- `limitations`
  - public-safe 样本只能证明“展示方法诚实”，不能替代 current external lane proof。

## Evidence Rules For This Page

这页只允许引用两类材料：

- `contract / control-plane evidence`
  - 例如 `README.md`、`docs/state-machine.md`、`docs/reference/evidence-model.md`
  - 作用：证明系统承诺了什么、结果会落在哪个结构里
- `public-safe sample evidence`
  - 例如 `evals/golden-set.sample.jsonl`
  - 例如 `artifacts/performance/rsshub/public_probe_summary.sample.tsv`
  - 例如 `artifacts/releases/v0.1.0/manifest.json`
  - 作用：给陌生读者一个“摸得着的样本”，但不泄露真实对象，也不把历史样例冒充当前 verdict

## What This Page Explicitly Does Not Prove

- 不证明这个仓库已经是成熟 SaaS。
- 不证明 external lane、GHCR、provider/live stability 已全部闭环。
- 不证明 checked-in historical example 就等于当前官方结论。
- 不证明 current-safe repo-side proof 已经天然存在；这件事必须回到 runtime-owned newcomer / current-state artifacts 去读。
- 不证明 repo-side governance 强，就自动等于用户结果、外部分发和 adoption 风险都已经解决。
- 不证明任何 `unsupported` / `degraded` / `failed` 的 AI path 可以被当成“执行成功”。

## Next Read

- 详细 case pack：[Task Result Proof Pack](../proofs/task-result-proof-pack.md)
- 项目定位：[project-positioning.md](./project-positioning.md)
- 证据模型：[evidence-model.md](./evidence-model.md)
- public-safe 边界：[public-artifact-exposure.md](./public-artifact-exposure.md)
