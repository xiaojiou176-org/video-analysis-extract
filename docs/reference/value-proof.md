# Value Proof

这页先讲人话：它不是讲“系统堆了多少模块”，而是讲“它比更简单的办法到底多出什么真实价值”。

## Why This Page Exists

- 防止把“工程很强”误讲成“价值一定很硬”
- 给 README / project positioning / 面试叙事一个任务级可回指的证据面
- 把“为什么值得有这套复杂度”讲成可检查的对照，而不是一句口号

## Baseline Comparisons

| 用户任务 | 更简单替代方案 | 这个仓库多出来的真实价值 | 代价 |
| --- | --- | --- | --- |
| 持续跟踪频道/订阅源并拉取新视频 | 手工打开站点、记链接、零散脚本 | 自动 ingestion、状态可追踪、失败可重跑、artifact 可回看 | 需要本地依赖和 worker |
| 把视频转成可检索知识资产 | 手工摘要、零散笔记、单次脚本导出 | 摘要、转录、embedding、引用卫生、失败边界能进入同一条流水线 | 初始环境更重 |
| 判断一次改动有没有让 AI 质量退化 | 肉眼抽查、感觉还行 | formal eval、baseline、regression report 能判断回归 | repo-side eval 仍不是 provider-heavy live benchmark |
| 判断当前仓库到底是 repo-side 绿还是 external 绿 | README 口头说明 | done-model、generated snapshot、current-proof gate 让完成语义可审计 | 需要维护控制面 |

## Task-Level Before / After

### 任务 1：订阅源到结构化产物

- Before：脚本能拉数据，但很难解释“这次为什么失败、失败后怎么重试、哪个 artifact 代表当前结果”。
- After：同一条链路会留下 worker 状态、运行日志、artifact、evidence index，能把“跑过”升级成“可复盘”。

### 任务 2：视频摘要与引用边界

- Before：摘要像一次性输出，质量退化主要靠感觉。
- After：摘要可以通过 rubric、baseline、regression report 判断是否退化，而且 current-proof 规则防止旧报告冒充当前结论。

### 任务 3：公开仓边界治理

- Before：public sample、historical example、external readiness 容易被一起讲，形成“看起来都成熟”的幻觉。
- After：public surface policy、done-model、external lane snapshot、third-party notices 分别约束公开边界、完成语义和权利账本。

## Honest Boundary

- 这页证明的是“为什么它比更简单方案更像真实工程系统”，不是证明“它已经是成熟 SaaS”。
- 这页证明的是“任务级价值与治理收益”，不是证明“外部采用已经完全无风险”。
- external lane、AI eval 厚度、provider 侧真实稳定性仍要看各自的当前证明链。
