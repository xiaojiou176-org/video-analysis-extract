# Integrations

这个目录是仓库的**外部转接层**，只负责把外部 API、二进制、镜像和社区服务接进本仓。

## 负责什么

- `binaries/`：外部 CLI / binary 的命令构造与适配。
- 后续可扩展：
  - `providers/`
  - `reader/`
  - `runtime-images/`

## 不负责什么

- 不承载业务流程编排。
- 不承载仓库内部契约。
- 不承载 UI / API / Worker 业务逻辑。

它像“机房里的转接头和配线架”，外部线从这里进，业务层不要自己乱接。
