# Artifacts

这个目录只保留**长期留存**的发布证据、性能基线和其他需要进入版本控制的历史制品。

## 负责什么

- `releases/`：release 相关 manifest、checksums、rollback 证据。
- `performance/`：长期保留的性能预算与基线。
- `release-readiness/`：可提交的 release readiness 基线与占位文件。
- `templates/`：长期保留的发布/性能模板，不再单独占用根级目录。

## 不负责什么

- 不负责一次性运行时产物。
- 不负责测试过程中的临时日志、trace、截图、视频、coverage 原始件。
- 这些都必须进入 `.runtime-cache/`，而不是进入本目录。
