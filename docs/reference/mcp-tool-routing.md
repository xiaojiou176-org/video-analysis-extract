# MCP Tool Routing Guide

本指南面向 AI Agent，目标是减少工具误用与盲选。

## Tool Set (13)

- `vd.jobs.get`
- `vd.videos.list`
- `vd.videos.process`
- `vd.retrieval.search`
- `vd.workflows.run`
- `vd.ingest.poll`
- `vd.computer_use.run`
- `vd.health.get`
- `vd.subscriptions.manage`
- `vd.notifications.manage`
- `vd.artifacts.get`
- `vd.ui_audit.run`
- `vd.ui_audit.read`

## Routing Rules

- 查任务状态：先 `vd.jobs.get`，不要先查 artifacts。
- 拉取内容证据：先 `vd.artifacts.get(kind=markdown)`，图像再用 `kind=asset`。
- 查问题根因：先 `vd.retrieval.search(mode=hybrid)`，再按命中 `job_id` 调 `vd.jobs.get`。
- 触发生产动作：`vd.videos.process`、`vd.ingest.poll`、`vd.workflows.run`。
- 管理类操作：统一用 `manage` 工具，必须显式传 `action`。

## Manage Tool Quick Reference

### `vd.subscriptions.manage`
- `action=list`: 可选 `platform`, `enabled_only`
- `action=upsert`: 必填 `platform`, `source_type`, `source_value`
- `action=remove`: 必填 `id`

### `vd.notifications.manage`
- `action=get_config`
- `action=set_config`: 推荐传 `enabled`, `to_email`
- `action=send_test`: 可传 `to_email`, `subject`, `body`
- `action=daily_send`: 可传 `date`, `to_email`, `subject`, `body`

### `vd.artifacts.get`
- `kind=markdown`: 需要 `job_id` 或 `video_url`
- `kind=asset`: 必须 `job_id` + `path`，可选 `include_base64=true`

### `vd.ui_audit.read`
- `action=get`: 读取 run 摘要
- `action=list_findings`: 可带 `severity`
- `action=get_artifact`: 必填 `key`，可带 `include_base64`
- `action=autofix`: 可带 `mode`, `max_files`, `max_changed_lines`

## Workflow Examples

### 1) 检索 -> 取工件 -> 触发重跑 -> 查状态
1. `vd.retrieval.search(query=\"字幕缺失\", mode=\"hybrid\")`
2. `vd.jobs.get(job_id=<hit.job_id>)`
3. `vd.videos.process(video={...}, mode=\"refresh_llm\", force=true)`
4. `vd.jobs.get(job_id=<new_job_id>)`

### 2) UI 审计闭环
1. `vd.ui_audit.run(job_id=<job_id>)`
2. `vd.ui_audit.read(action=\"list_findings\", run_id=<run_id>, severity=\"high\")`
3. `vd.ui_audit.read(action=\"autofix\", run_id=<run_id>, mode=\"dry-run\")`

### 3) Computer Use
1. `vd.computer_use.run(instruction=..., screenshot_base64=...)`
2. 若返回 `require_confirmation=true`，由上层审批后再执行动作链。
