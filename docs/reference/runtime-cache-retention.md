# Runtime Cache Retention

`.runtime-cache/` 是唯一合法 repo-side 运行时输出根。

## 真相源

- `config/governance/runtime-outputs.json`

## 固定语义分舱

- `run/`
- `logs/`
- `reports/`
- `evidence/`
- `tmp/`
- `temp/`

每个舱位都必须声明：

- `owner`
- `classification`
- `ttl_days`
- `max_total_size_mb`
- `max_file_count`
- `rebuild_entrypoint`
- `freshness_required`

## 元数据规则

`reports/**` 与 `evidence/**` 的 artifact 必须伴随 sidecar metadata，至少包含：

- `created_at`
- `source_entrypoint`
- `source_run_id`
- `source_commit`
- `verification_scope`
- `freshness_window_hours`

## 门禁与维护入口

```bash
python3 scripts/runtime/prune_runtime_cache.py --assert-clean
python3 scripts/governance/check_runtime_cache_retention.py
python3 scripts/governance/check_runtime_cache_freshness.py
bash scripts/runtime/run_runtime_cache_maintenance.sh --normalize-only
```

## 硬规则

- 历史 artifact 过 freshness window 后不得再作为 current verification。
- 删除 `.runtime-cache/**` 后，仓库必须可以通过标准入口重建。
