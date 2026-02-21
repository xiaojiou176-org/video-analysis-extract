# Vendor Governance

本目录用于管理第三方上游同步治理文档与执行入口。

## 文件说明

- `docs/vendor/upstream-sync-runbook.md`: fork + subtree + `UPSTREAM.lock` 标准流程（含回滚与审计要求）。
- `scripts/vendor/upstream_sync.sh`: 上游同步脚本（参数校验、dry-run、安全检查、命令模板输出）。
- `scripts/vendor/validate_upstream_lock.sh`: `UPSTREAM.lock` 格式与必填字段校验脚本。
- `.github/workflows/vendor-governance.yml`: CI 自动校验 `UPSTREAM.lock`。

## 快速使用

1. 先做 dry-run（不改仓库）：

```bash
bash scripts/vendor/upstream_sync.sh \
  --vendor yt-dlp \
  --upstream-url https://github.com/yt-dlp/yt-dlp.git \
  --upstream-ref refs/tags/2026.01.01 \
  --prefix vendor/yt-dlp \
  --dry-run
```

2. 确认命令模板后执行真实同步：

```bash
bash scripts/vendor/upstream_sync.sh \
  --vendor yt-dlp \
  --upstream-url https://github.com/yt-dlp/yt-dlp.git \
  --upstream-ref refs/tags/2026.01.01 \
  --prefix vendor/yt-dlp \
  --execute
```

3. 本地校验 lock 文件：

```bash
bash scripts/vendor/validate_upstream_lock.sh --root .
```

