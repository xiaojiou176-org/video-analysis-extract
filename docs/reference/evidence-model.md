# Evidence Model

运行时证据统一由三类 artifact 构成：

- `.runtime-cache/logs/**`
- `.runtime-cache/reports/**`
- `.runtime-cache/evidence/**`

## Evidence Index

每个 `run_id` 都应生成：

- `.runtime-cache/reports/evidence-index/<run_id>.json`

索引内容最少包括：

- 对应 run 的 logs
- 对应 run 的 reports
- 对应 run 的 evidence

## 元数据要求

每个 logs/reports/evidence artifact 必须有 sidecar metadata，至少声明：

- `source_run_id`
- `source_entrypoint`
- `source_commit`
- `verification_scope`
- `created_at`

## 门禁

```bash
python3 scripts/governance/check_public_entrypoint_manifests.py
python3 scripts/governance/check_runtime_artifact_writer_coverage.py
python3 scripts/runtime/build_evidence_index.py --rebuild-all
python3 scripts/governance/check_no_unindexed_evidence.py
python3 scripts/governance/check_log_correlation_completeness.py
```

`check_public_entrypoint_manifests.py` 像“前台值班表检查器”，它不看历史脏数据，而是直接检查 `bin/*` 这些正式入口是否都在运行前写下 run manifest。先把正式入口做成会登记“案号台账”的入口，后面新的 logs/reports/evidence 才会自然带着 manifest 收口。

`check_runtime_artifact_writer_coverage.py` 的作用很朴素：它像“巡检员”，专门找那些还在直接往 `.runtime-cache/reports/` 或 `.runtime-cache/evidence/` 里写文件、却没有经过受治理 helper 或显式 metadata 写入的脚本，避免 runtime artifact 继续靠人工记忆收口。

## 设计目标

- 任何一轮 strict/smoke/live-smoke/governance run 都能通过 `run_id` 找到整案证据。
- 历史 artifact 不能伪装成当前证明。
