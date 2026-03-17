# Public Rights And Provenance

这页专门回答一个问题：**仓库里哪些内容是本项目自己的，哪些是第三方依赖、第三方平台引用、历史样例，公开时各自按什么边界解释。**

## Canonical Sources

- 项目许可：`LICENSE`
- 第三方权利账本：`THIRD_PARTY_NOTICES.md`
- 第三方依赖明细：`artifacts/licenses/third-party-license-inventory.json`
- public-safe 样本边界：`docs/reference/public-artifact-exposure.md`
- 对外公开姿态：`docs/reference/public-repo-readiness.md`

## Rights Model

- **源码与仓库治理文档**：按仓库当前公开许可解释。
- **第三方依赖**：不因为仓库根许可而自动变成“本项目原创内容”；它们的许可与 notice 义务以 `THIRD_PARTY_NOTICES.md` 和生成 inventory 为准。
- **平台名称与接口引用**：只是说明系统依赖了哪些外部平台，不代表官方合作、隶属或代言关系。
- **历史 release evidence / performance 样例**：可作为文档样例公开，但不能冒充“当前官方 release verdict”。

## Historical Examples Rule

- `artifacts/releases/*` 中的 checked-in 样例是**历史文档样例**，不是当前 release 的正式裁决。
- 当前 release / attestation / external lane 结论只允许引用 current-run runtime artifacts 与 generated snapshot。
- 如果一个样例需要公开保留，必须显式带有“historical example / not canonical verdict”语义。

## Third-party Content Rule

- 不允许把第三方依赖、第三方平台能力、或第三方工具链描述成“仓库自带原创能力”。
- 对第三方依赖的许可、notice、attribution，不允许手写长表；必须以机器生成账本为准。
- 如果未来引入新的 vendored / copied / patched third-party content，必须先补权利来源说明，再允许进入 tracked public tree。

## Decision Boundary

- **可以公开**：源码、合同、治理控制面、sanitized performance 样本、historical examples with boundary note。
- **不能直接当官方当前证明**：checked-in historical release evidence、旧 run 的 external workflow 成功记录、任何缺 current-proof 对齐的历史 artifact。
- **不能因为仓库 public 就自动推断**：镜像分发已成熟、平台许可已完全闭环、品牌关系已成立。
- **不能因为 tracked 政策文件存在就自动推断**：GitHub 私密漏洞上报、GHCR 包权限、release distribution UI 等平台能力当前一定可用。

## Reporting Rule

对外说明权利与来源时，必须至少同时写出：

- 当前仓库许可入口
- 第三方权利账本入口
- 历史样例与当前证明的边界
- 平台引用不等于官方关系
