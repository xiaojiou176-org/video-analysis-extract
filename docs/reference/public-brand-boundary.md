# Public Brand Boundary

这页专门回答一个问题：**仓库里提到的 Gemini、YouTube、Bilibili、Resend、RSSHub、Miniflux、Nextflux 等名字，到底是什么关系。**

## Brand Rule

- 这些名称用于描述 **集成对象、上游系统、接口边界、兼容性矩阵**。
- 它们不表示官方合作、官方认证、官方代言或从属关系。
- 仓库的公开姿态是 source-first engineering repo，不是任何上游平台的官方插件、官方 SDK 分发页、或官方 hosted 产品页面。

## Allowed Public Usage

- 允许在 docs、代码、compat matrix、upstream registry 中按事实引用平台名称。
- 允许在样本与运行说明中说明“哪条链路依赖哪个平台”。
- 允许说明外部 blocker 是平台权限、配额、GHCR、workflow 或 provider 状态。

## Forbidden Public Usage

- 禁止把上游平台 logo、品牌资产、官方 UI 素材当作仓库默认公开展示面。
- 禁止使用会暗示官方 affiliation 的文案。
- 禁止把“支持某平台”偷换成“获得该平台官方认可或长期 SLA”。

## Canonical References

- 上游台账：`config/governance/upstream-registry.json`
- 上游兼容矩阵：`config/governance/upstream-compat-matrix.json`
- external lane truth entry：`docs/generated/external-lane-snapshot.md`（pointer）+ `.runtime-cache/reports/**`（current verdict）
- 项目公开姿态：`docs/reference/public-repo-readiness.md`

## Reporting Rule

对外写平台关系时，默认模板是：

- “本仓库集成 / 依赖 / 调用 `<platform>`”
- “该能力是否当前可验证，取决于 external lane current-proof”
- “这不代表与 `<platform>` 存在官方合作或托管承诺”
- “GitHub security / package capability 是否当前可用，取决于 runtime probe，而不是本仓文档是否写了入口”
