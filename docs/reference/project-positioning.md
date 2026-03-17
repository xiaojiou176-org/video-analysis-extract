# Project Positioning

## 这是什么

这不是一个“套了 AI 热词的视频 demo”。它是一个**本地优先的视频内容处理系统**，把视频拉取、解析、摘要、检索、分发串成一条可验证的流水线，并通过 API / MCP / Web 三类入口暴露。

## 目标用户

- 想把视频内容转成结构化知识资产的个人开发者
- 需要本地优先、可审计工作流，而不是纯托管黑盒的 AI 应用开发者
- 需要 API + Worker + MCP + Web 同时存在的 owner/operator

## 非目标用户

- 只想要开箱即用 SaaS 的终端消费者
- 不愿准备本地依赖、数据库、worker、或 provider key 的轻量试用者
- 需要完全托管发布与外部平台 SLA 的团队

## 为什么要本地优先

- 本地优先让 ingestion、worker、artifact、日志和失败诊断都可追溯
- 对这个系统来说，失败治理和 evidence 比“云上有个按钮”更重要
- 这也解释了为什么 repo-side done 与 external done 必须分层

## 为什么 API / MCP / Web 同时存在

- API：服务契约与自动化入口
- MCP：给 agent/tooling 的最小操作面
- Web：人工巡检、状态查看、管理台入口

如果只保留其中一层，系统会少一类关键使用面。

## 替代方案不足

- 单纯的脚本流：可跑，但难以审计、复盘和持续验证
- 只做 Web demo：可展示，但不够 owner-level
- 只做后台服务：可编排，但对人工运营与调试不友好

更具体的任务级对比请看：`docs/reference/value-proof.md`。

## 当前边界与 Non-goals

- 当前公开策略是**公开仓 + source-first + limited-maintenance**，不承诺镜像优先交付
- 当前目标是强工程型 applied AI mini-system，不假装是成熟 SaaS
- 当前 formal eval 追求“可判定进退”，不追求学术 benchmark 大而全
- 当前 external lane 仍需单独看 `.runtime-cache/reports/**` 下的 runtime truth；`docs/generated/external-lane-snapshot.md` 只保留 pointer / reading rule。公开仓本身不等于 GHCR / release / provider 全部闭环

## 当前最硬的价值证据

- 任务级价值对比：`docs/reference/value-proof.md`
- formal eval 与 regression：`docs/reference/ai-evaluation.md`
- repo-side 与 external done 的边界：`docs/reference/done-model.md`
