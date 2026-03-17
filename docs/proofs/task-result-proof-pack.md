# Task Result Proof Pack

这份 proof pack 先讲人话：它像一份“项目证据卷宗”，专门回答 5 个问题：

1. 输入是什么？
2. 处理中间到底做了什么？
3. 输出是什么？
4. 它为什么比更简单的 baseline 更有价值？
5. 它的失败边界和不能夸大的地方是什么？

如果只看 [value-proof.md](../reference/value-proof.md)，你能知道“这套系统大概值不值得”。  
如果继续看这份文档，你能知道“具体靠哪些公开可读的证据来支撑这个判断”。

## Reading Rules

- 这不是 marketing case study；它不会假装每个 case 都已经拿到了 live 运行截图。
- 这也不是 current external verdict；凡是 historical example、synthetic sample、repo-side contract，都必须显式写出边界。
- 这里优先复用仓库里已经 public-safe 的材料，不编造用户故事、不伪造外部采用、不虚构性能提升。

## How To Pair This Pack With Current Truth

- 想知道“当前 HEAD 的 repo-side newcomer / strict 收据今天拿到没有”，先看 [newcomer-result-proof.md](../reference/newcomer-result-proof.md)。
- 想知道“外部世界今天认不认账”，看 [external-lane-status.md](../reference/external-lane-status.md) 与 runtime-owned `current-state-summary.md`。
- 想知道“这套系统到底靠什么 representative cases 证明自己有任务价值”，再回来看这份 pack。
- 换句话说：`newcomer-result-proof` 负责**今天的 repo-side 收据**，`Task Result Proof Pack` 负责**代表性结果案例**；两者要一起读，不能互相冒充。

## Source Inventory

| 证据源 | 类型 | 为什么可公开 | 在 proof pack 里的用途 |
| --- | --- | --- | --- |
| `README.md` | contract / positioning | 公开入口文档，不含私有数据 | 说明系统目标、处理面与对外姿态 |
| `docs/state-machine.md` | processing contract | 处理流程合同，不含真实用户内容 | 解释输入如何进入 pipeline、输出如何落盘 |
| `docs/reference/evidence-model.md` | evidence contract | 运行时证据模型，不含私有样本 | 解释失败/成功如何被记录与追溯 |
| `docs/reference/ai-evaluation.md` | evaluation contract | formal eval 说明文档，可公开 | 解释质量回归如何被判定 |
| `evals/golden-set.sample.jsonl` | synthetic sample | 样例 prompt/fixture 为公开样本 | 展示“grounded digest / failure honesty”被如何检查 |
| `evals/baseline.json` | baseline contract | 只含阈值与规则，不含私有数据 | 展示 regression 不是凭感觉 |
| `artifacts/performance/rsshub/public_probe_summary.sample.tsv` | synthetic public-safe sample | 已脱敏、去 route、去 identifier | 展示 public-safe 样本如何保留结果形状 |
| `artifacts/releases/v0.1.0/manifest.json` | historical example | 明确标记 `historical-example` | 展示历史样例如何公开但不冒充当前 verdict |
| `docs/reference/newcomer-result-proof.md` | repo-side proof reading rule | 只说明读数规则，不含敏感运行数据 | 帮 reviewer 区分“有治理收据”和“有当前 strict 收据” |

## Representative Case 1: `rep-case-01-ingest-queue` 持续发现新内容并稳定入队

### 这类任务在现实里是什么

一句话版：不是“偶尔抓一次视频”，而是“长期跟踪一个来源，有新内容就稳定进入处理链”。

### Input

- 订阅 RSS / feed entry
- 视频或文章来源标识
- 幂等所需的标准化字段，例如 `video_uid`、`entry_hash`、`idempotency_key`

### Processing Chain

- `PollFeedsWorkflow`
- `poll_feeds_activity`
- entry 标准化
- 写入 `videos`、`ingest_events`、`jobs`
- 为每个新 job 启动 `ProcessJobWorkflow`

### Output

- 新 job 被创建并入队
- 后续 `ProcessJobWorkflow` 可以接手继续处理
- read model 可继续暴露到 feed/digest 入口

### Baseline

- 手工打开 YouTube / Bilibili / RSS 页面，看有没有更新
- 或者写一个只负责抓链接的小脚本

### After

- 新内容发现不再停留在“看到了没”，而是直接进入一条可重复、可追踪、可去重的处理通道
- 这对持续订阅型任务很关键，因为真正麻烦的是长期重复运行时的稳定性，而不是第一次跑通

### Why It Matters

- 这解决的是“持续运营”问题，不只是“抓一次数据”
- 后续摘要、embedding、artifact 写入，都建立在这里先把入队做稳的前提上

### Limitations And Failure Path

- 这只能证明 repo 对发现与入队的设计是成体系的
- 不证明所有外部来源都一直可用
- 不证明 live feed 当下没有风控、平台波动或 provider 限制

### Sources

- [README.md](../../README.md)
- [state-machine.md](../state-machine.md)

### Why Public-safe

- 这一 case 只引用处理合同与系统入口说明，没有引用真实用户订阅、真实频道身份、真实产物内容

### Why Representative

- 所有下游价值都要先经过“发现并入队”这一关
- 如果这关不稳，后面的 digest、eval、artifact 证明都会变成空中楼阁

## Representative Case 2: `rep-case-02-structured-digest` 单条内容被处理成结构化 digest，而不是一次性笔记

### 这类任务在现实里是什么

一句话版：把一条视频或文章，从“我看完后写个摘要”升级成“能进入知识资产链的结构化结果”。

### Input

- 单条视频或文章内容
- `content_type`
- 可选的 process `mode` 与 `overrides`

### Processing Chain

- `ProcessJobWorkflow`
- video 9-step pipeline:
  - `fetch_metadata`
  - `download_media`
  - `collect_subtitles`
  - `collect_comments`
  - `extract_frames`
  - `llm_outline`
  - `llm_digest`
  - `build_embeddings`
  - `write_artifacts`
- article 5-step pipeline:
  - `fetch_article_content`
  - `llm_outline`
  - `llm_digest`
  - `build_embeddings`
  - `write_artifacts`

### Output

- `summary_md`
- `artifacts_index`
- `content_type`
- `steps`
- 可供 API / MCP / Web 共同消费的 read model 字段

### Baseline

- 一次性人工摘要
- 单次导出的 markdown 或零散笔记
- 没有 embedding，也没有统一 artifact 结构

### After

- 结果不只是“有一段摘要”，而是有 outline、digest、embedding、artifact 的成套输出
- 更重要的是，这些输出在同一条处理链里形成关系，而不是分别散落在脚本、笔记和临时文件里

### Why It Matters

- 这让结果更像“可持续使用的知识资产”，而不是一次性的阅读感想
- API / MCP / Web 共用一套读模型，也让结果更容易被继续消费

### Limitations And Failure Path

- 这页证明的是处理链结构、输出形态和 repo-side 任务价值
- 不证明任何单次 live provider 输出都一定高质量
- 真实运行时质量仍要结合 current-proof 和 external lane 去看

### Sources

- [README.md](../../README.md)
- [state-machine.md](../state-machine.md)
- [golden-set.sample.jsonl](../../evals/golden-set.sample.jsonl)

### Why Public-safe

- 这里引用的是处理合同和 synthetic eval fixture
- 没有公开真实视频内容、真实用户摘要、真实引用片段

### Why Representative

- “把视频内容变成结构化 digest”本来就是仓库最核心的承诺之一
- 如果这个 case 站不住，整个项目就只剩治理外壳，没有任务结果内核

## Representative Case 3: `rep-case-03-failure-replayability` 失败时能解释坏在哪，而不是只知道“没出结果”

### 这类任务在现实里是什么

一句话版：当处理链失败时，操作者不是只拿到一个红色报错，而是能知道问题卡在什么阶段、有没有降级完成、证据在哪。

### Input

- 一次 pipeline run
- 运行中各 step 的状态变化
- 日志、reports、evidence sidecar metadata

### Processing Chain

- `jobs.status` 负责总状态
- `sqlite.step_runs.status` 负责 step ledger
- `degradations` 记录可降级失败
- `.runtime-cache/reports/evidence-index/<run_id>.json` 收拢 logs / reports / evidence

### Output

- `step_summary`
- `pipeline_final_status`
- `degradations`
- evidence index
- 统一 metadata 字段：`source_run_id`、`source_entrypoint`、`source_commit`、`verification_scope`、`created_at`

### Baseline

- shell 脚本报错
- 临时日志散落
- 事后很难区分“完全失败”“半成功”“旧产物残留”

### After

- 失败路径也进入同一套证据模型，不会只让成功路径看起来很工整
- 对 operator 来说，这相当于从“只知道发烧了”变成“知道是扁桃体、流感还是肺炎”，后续动作才有依据

### Why It Matters

- 真正落地的系统一定会失败；失败时是否可复盘，决定它是玩具还是可运营系统
- 对 reviewer 来说，这类证据也能解释“为什么这个项目的复杂度不是装饰”

### Limitations And Failure Path

- 合同能说明失败如何被记录，但不能替代某次当前 run 的新鲜运行证据
- 如果需要判断“当前 HEAD 这次运行是不是已经恢复”，仍要看 fresh runtime artifact

### Sources

- [state-machine.md](../state-machine.md)
- [evidence-model.md](../reference/evidence-model.md)

### Why Public-safe

- 使用的是字段合同、目录合同与证据模型说明
- 没有把真实 log、真实 trace、真实用户对象直接带入公开文档

### Why Representative

- 这是区分“脚本能跑”和“系统可运营”的最硬差别之一
- 对长期运行的视频处理系统，这个差别比单次 demo 更重要

## Representative Case 4: `rep-case-04-ai-regression-detectability` 改 prompt 或 tool path 后，质量回归可以被判定

### 这类任务在现实里是什么

一句话版：模型相关逻辑改完之后，不再靠“感觉没问题”来判断，而是用固定考卷做回归检查。

### Input

- `evals/golden-set.sample.jsonl`
- `evals/rubric.md`
- `evals/baseline.json`
- deterministic regression runner

### Processing Chain

- 用 golden set 的 `fixture_response` 做 deterministic 评分
- 按 rubric 的维度评分
- 用 baseline 检查 pass rate 和关键维度是否掉线

### Output

- regression report
- pass / fail 结论
- 维度级别的质量读数:
  - `factuality`
  - `coverage`
  - `citation_hygiene`
  - `failure_honesty`

### Baseline

- 改完 prompt 后随手看几条输出
- 团队成员各自凭经验判断“差不多”

### After

- 至少在 repo-side 可以回答“有没有退化”“退化在哪个维度”
- 这比“模型好像更聪明了”要诚实得多，也更利于长期迭代

### Why It Matters

- LLM 系统最容易出现的不是完全坏掉，而是悄悄变差
- 有 baseline 和 regression，才能把“主观观感”变成“可讨论的质量差异”

### Limitations And Failure Path

- 这不是 provider-heavy live eval
- 这不是学术 benchmark
- 它的作用是给 repo-side 变更提供最小可判定进退面，而不是给出最终线上质量背书

### Sources

- [ai-evaluation.md](../reference/ai-evaluation.md)
- [evals/README.md](../../evals/README.md)
- [evals/baseline.json](../../evals/baseline.json)
- [evals/golden-set.sample.jsonl](../../evals/golden-set.sample.jsonl)

### Why Public-safe

- golden set 和 baseline 都是公开样本与阈值规则
- 它们不依赖真实 provider key、真实用户内容或私有运行截图

### Why Representative

- 仓库里最核心的 AI 任务就是 outline 与 digest
- 如果连回归都无法判定，这类系统很难在真实维护中站住脚

## Representative Case 5: `rep-case-05-public-safe-evidence` 给陌生读者展示结果时，既要具体，也要 public-safe

### 这类任务在现实里是什么

一句话版：你想向 reviewer 证明“仓库确实有真实结果形状”，但又不能把真实路由、对象标识、历史 run 冒充成当前结论。

### Input

- public-safe 样本分类规则
- sanitized / synthetic performance sample
- historical release example with boundary note
- newcomer result proof reading rule

### Processing Chain

- 用 `public-artifact-exposure.md` 判断哪些样本能进 tracked public tree
- 保留 `public_probe_summary.sample.tsv` 这类 synthetic sample
- 保留带 `historical-example` 标记的 release manifest
- 用 `newcomer-result-proof.md` 提醒读者：fresh strict receipt 与 governance receipt 不是一回事

### Output

- reviewer 能看到具体样本
- reviewer 也能明确知道这些样本是不是当前官方结论
- 仓库对“可公开展示的结果”给出边界，而不是留给作者临场解释

### Baseline

- 直接贴原始探针文件
- 直接贴历史 release 样例
- 直接贴没有 boundary note 的截图或日志

### After

- 仓库允许公开的是 synthetic / sanitized sample 或 historical example with note
- 这既保留了“可以具体看”的证据，又降低了误导和泄露风险

### Why It Matters

- public source-first 项目最容易输在这一步：有内容可展示，但展示方式不诚实
- 对面试官、评审者和陌生读者来说，能不能快速看懂“这是什么证据、边界在哪”非常关键

### Limitations And Failure Path

- public-safe 样本不是 current external proof
- historical example 不是 current release verdict
- 如果要判断 live external lane，当轮 fresh artifact 仍然是唯一可信来源

### Sources

- [public-artifact-exposure.md](../reference/public-artifact-exposure.md)
- [public-rights-and-provenance.md](../reference/public-rights-and-provenance.md)
- [public-privacy-and-data-boundary.md](../reference/public-privacy-and-data-boundary.md)
- [newcomer-result-proof.md](../reference/newcomer-result-proof.md)
- [public_probe_summary.sample.tsv](../../artifacts/performance/rsshub/public_probe_summary.sample.tsv)
- [manifest.json](../../artifacts/releases/v0.1.0/manifest.json)

### Why Public-safe

- RSSHub 样本明确写了 `synthetic public-safe sample`
- historical manifest 明确写了 `historical_example=true` 与 `evidence_scope=historical-example`
- 文档本身也反复要求“不得把历史样例冒充当前 verdict”

### Why Representative

- 这份 proof pack 本身就是给陌生读者看的
- 如果连“公开展示结果”的边界都没有处理好，那么这份 proof pack 本身就会失去可信度

## What This Pack Proves

- 这套系统的价值不只在“工程治理很强”，还在于它把若干真实任务做成了可复核的结构
- 这些真实任务至少覆盖：
  - 新内容发现与入队
  - 内容到结构化 digest
  - 失败复盘
  - AI 质量回归判断
  - public-safe 结果展示

## What This Pack Does Not Prove

- 不证明 external lane 全绿
- 不证明 GHCR / release / provider live path 已经全部 current-run 闭环
- 不证明这就是 adoption-grade SaaS
- 不证明 synthetic sample 或 historical example 等于 live production result
