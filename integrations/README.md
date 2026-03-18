# Integrations

这个目录是仓库的**外部转接层**，只负责把外部 API、二进制、镜像和社区服务接进本仓。

## 负责什么

- `binaries/`：外部 CLI / binary 的命令构造与适配。
- `providers/`：外部 HTTP/API/provider 协议层与 request/response helper。
- 后续可扩展：
  - `reader/`
  - `runtime-images/`

当前已收口的 provider 样例：

- `providers/article_fetch.py`
- `providers/rsshub.py`
- `providers/youtube_comments.py`
- `providers/bilibili_comments.py`

## 不负责什么

- 不承载业务流程编排。
- 不承载仓库内部契约。
- 不承载 UI / API / Worker 业务逻辑。

它像“机房里的转接头和配线架”，外部线从这里进，业务层不要自己乱接。

## Bridge Governance

- 如果某个转接面需要长期把 repo 入口、runtime 输出、或外部状态桥接到受治理路径，必须登记到 `config/governance/bridges.json`。
- `integrations/` 是外部能力接入层；`bridges.json` 负责回答“哪些桥接面仍然活着、写向哪里、何时必须收口或删除”。
