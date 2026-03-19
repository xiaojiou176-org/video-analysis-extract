# MCP Tool Routing Guide

This guide is for AI agents. Its goal is to reduce tool misuse and blind tool selection.

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

- To inspect job state, call `vd.jobs.get` before touching artifacts.
- To fetch content evidence, call `vd.artifacts.get(kind=markdown)` first and then `kind=asset` for images.
- To find a root cause, start with `vd.retrieval.search(mode=hybrid)` and then follow matching `job_id` values into `vd.jobs.get`.
- Production-triggering actions live behind `vd.videos.process`, `vd.ingest.poll`, and `vd.workflows.run`.
- Management actions must go through the `manage` tools with an explicit `action`.

## Manage Tool Quick Reference

### `vd.subscriptions.manage`

- `action=list`: optional `platform`, `category`, `enabled_only`
- `action=upsert`: required `platform`, `source_type`, `source_value`
  - optional `adapter_type` (`rsshub_route|rss_generic`)
  - when `adapter_type=rss_generic`, prefer sending `source_url` explicitly
  - optional `category`, `tags`
- `action=remove`: required `id`
- Common failures:
  - missing or invalid `action` -> parameter validation failure (4xx)
  - missing remove target -> idempotent delete; upper layers should usually treat it as success

### `vd.notifications.manage`

- `action=get_config`
- `action=set_config`: prefer `enabled`, `to_email`
- `action=send_test`: optional `to_email`, `subject`, `body`
- `action=daily_send`: optional `date`, `to_email`, `subject`, `body`
- Common failures:
  - webhook or email service unreachable -> retryable error
  - missing target mailbox or invalid config -> non-retryable error; fix configuration first

### `vd.artifacts.get`

- `kind=markdown`: requires `job_id` or `video_url`
- `kind=asset`: requires `job_id` + `path`, optional `include_base64=true`
- Common failures:
  - missing artifact -> 404 semantics; verify task state with `vd.jobs.get` first
  - missing `path` for `kind=asset` -> parameter error (4xx)

### `vd.ui_audit.read`

- `action=get`: reads the run summary (including `gemini_review.status/reason_code/provider_status/model`)
- `action=list_findings`: optional `severity`
- `action=get_artifact`: required `key`, optional `include_base64`
- `action=autofix`: optional `mode`, `max_files`, `max_changed_lines`
- Common failures:
  - unknown `run_id` -> 404
  - `autofix` exceeds limits -> 4xx; tighten `max_files/max_changed_lines`
  - `action=get` returning `status=completed_with_gemini_failure` means the base evidence was collected but the Gemini deep review failed, so do not treat it as a deep-review pass

## I/O Example Snippets

### `vd.jobs.get`

- Input:

```json
{"job_id":"00000000-0000-4000-8000-000000000001"}
```

- Key output fields:

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

- Input:

```json
{"query":"provider timeout","mode":"hybrid","top_k":5}
```

- Key output fields:

```json
{
  "items": [
    {"job_id":"...","source":"digest","score":0.82,"snippet":"..."}
  ]
}
```

### `vd.notifications.manage(action=set_config)`

- Input:

```json
{
  "action":"set_config",
  "enabled":true,
  "to_email":"you@example.com",
  "daily_digest_enabled":true,
  "daily_digest_hour_utc":8
}
```

- Key output fields:

```json
{"ok":true,"enabled":true,"to_email":"you@example.com"}
```

## Workflow Examples

### 1) Search -> Fetch Artifact -> Trigger Re-run -> Check Status

1. `vd.retrieval.search(query=\"subtitle missing\", mode=\"hybrid\")`
2. `vd.jobs.get(job_id=<hit.job_id>)`
3. `vd.videos.process(video={...}, mode=\"refresh_llm\", force=true)`
4. `vd.jobs.get(job_id=<new_job_id>)`

### 2) UI Audit Loop

1. `vd.ui_audit.run(job_id=<job_id>)`
2. `vd.ui_audit.read(action=\"list_findings\", run_id=<run_id>, severity=\"high\")`
3. `vd.ui_audit.read(action=\"autofix\", run_id=<run_id>, mode=\"dry-run\")`

### 3) Computer Use

1. `vd.computer_use.run(instruction=..., screenshot_base64=...)`
2. If it returns `require_confirmation=true`, wait for upper-layer approval before executing the action chain.
