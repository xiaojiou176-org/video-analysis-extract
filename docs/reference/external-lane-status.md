# External Lane Status

本页专门回答一个问题：**仓库内部已经绿了以后，外部世界到底认不认账。**

## Current External Lanes

| Lane | Target | Current State | Current Blocker Type |
| --- | --- | --- | --- |
| GHCR standard image | `ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard` | blocked | workflow + runner hygiene |
| Release evidence attestation | `release-evidence-attest.yml` current-run bundle | blocked | workflow runtime compatibility |
| RSSHub provider chain | `rsshub-youtube-ingest-chain` | verified | provider smoke passed |
| Resend provider chain | `resend-digest-delivery-chain` | verified | current account's testing-recipient boundary passed |

## Verification Rules

- repo-side green 不等于 external lane green
- external lane 只在 fresh artifact + runtime metadata + same-run proof 同时满足时才算 `verified`
- 平台权限问题必须写成平台 blocker，不能伪装成仓库 bug

## Fresh Evidence Snapshot

- `build-ci-standard-image.yml` 已从 disabled 恢复到 active，并成功触发了一次 `workflow_dispatch`；当前最新失败点在 `Enforce runner disk budget`，原因是 `runner_workspace_maintenance.sh` 对匹配到的单文件 stale path 删除不完整。
- `release-evidence-attest.yml` 可触发，但最新失败点在 `Capture release evidence bundle inputs`，远端日志显示 runner 的 Python 3.10 无法导入 `datetime.UTC`。
- `rsshub-youtube-ingest-chain` 已在本地 full stack + reader stack 下 fresh 通过，证据主件是 `.runtime-cache/logs/tests/smoke-full-stack.jsonl`（run id `77c0ba15cbeb41ca849b4297d41d881b`）。
- `resend-digest-delivery-chain` 已在当前 provider 账号允许的 testing-recipient 边界内 fresh 发送成功，证据主件是 `.runtime-cache/logs/tests/compat-resend-daily-sent.log`（run id `cb66852c15274544b9ec0dae829d1296`）。
- 所以当前 external lane 剩余 blocker 已收敛到两条：**GHCR build/publish** 与 **release evidence attestation**。两者都属于仓库 workflow/runtime compatibility + 平台执行面，而不是 provider 链本身。

## Canonical Commands

GHCR / external image:

```bash
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
gh workflow run build-ci-standard-image.yml --ref main
```

Release evidence:

```bash
gh workflow run release-evidence-attest.yml --ref main -f release_tag=v0.1.0
gh attestation verify <bundle> --repo xiaojiou176-org/video-analysis-extract
```

Provider lanes:

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
./bin/run-daily-digest --to-email <verified-recipient>
./bin/run-failure-alerts --to-email <verified-recipient>
```

## Reporting Rule

最终汇报 external lane 时，必须至少写出：

- 成功到哪一步
- 哪个 artifact / log / run id 是证据
- 如果失败，最后一跳卡在平台权限、provider 账户、还是仓库脚本
