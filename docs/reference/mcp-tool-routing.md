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

- `action=list`: 可选 `platform`, `category`, `enabled_only`
- `action=upsert`: 必填 `platform`, `source_type`, `source_value`
  - 可选 `adapter_type`（`rsshub_route|rss_generic`）
  - 当 `adapter_type=rss_generic` 时建议显式传 `source_url`
  - 可选 `category`, `tags`
- `action=remove`: 必填 `id`
- 常见失败:
  - `action` 缺失或非法 -> 参数校验失败（4xx）
  - `remove` 目标不存在 -> 幂等删除（建议上层按成功处理）

### `vd.notifications.manage`

- `action=get_config`
- `action=set_config`: 推荐传 `enabled`, `to_email`
- `action=send_test`: 可传 `to_email`, `subject`, `body`
- `action=daily_send`: 可传 `date`, `to_email`, `subject`, `body`
- 常见失败:
  - Webhook/邮件服务不可达 -> 可重试错误
  - 目标邮箱缺失或配置无效 -> 不可重试错误（先修配置）

### `vd.artifacts.get`

- `kind=markdown`: 需要 `job_id` 或 `video_url`
- `kind=asset`: 必须 `job_id` + `path`，可选 `include_base64=true`
- 常见失败:
  - 产物不存在 -> 返回 404 语义，先用 `vd.jobs.get` 校验任务状态
  - `kind=asset` 丢 `path` -> 参数错误（4xx）

### `vd.ui_audit.read`

- `action=get`: 读取 run 摘要
- `action=list_findings`: 可带 `severity`
- `action=get_artifact`: 必填 `key`，可带 `include_base64`
- `action=autofix`: 可带 `mode`, `max_files`, `max_changed_lines`
- 常见失败:
  - `run_id` 不存在 -> 404
  - `autofix` 超出限制 -> 4xx（请收紧 `max_files/max_changed_lines`）

## I/O Example Snippets

### `vd.jobs.get`

- 输入:

```json
{"job_id":"00000000-0000-4000-8000-000000000001"}
```

- 关键输出字段:

```json
{
  "status": "succeeded",
  "mode": "standard",
  "steps": [],
  "degradations": [],
  "artifacts_index": {"digest": "/abs/path/digest.md"}
}
```

### `vd.retrieval.search`

- 输入:

```json
{"query":"provider timeout","mode":"hybrid","top_k":5}
```

- 关键输出字段:

```json
{
  "items": [
    {"job_id":"...","source":"digest","score":0.82,"snippet":"..."}
  ]
}
```

### `vd.notifications.manage(action=set_config)`

- 输入:

```json
{
  "action":"set_config",
  "enabled":true,
  "to_email":"you@example.com",
  "daily_digest_enabled":true,
  "daily_digest_hour_utc":8
}
```

- 关键输出字段:

```json
{"ok":true,"enabled":true,"to_email":"you@example.com"}
```

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
