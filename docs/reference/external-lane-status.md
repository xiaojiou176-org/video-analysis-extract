# External Lane Status

本页专门回答一个问题：**仓库内部已经绿了以后，外部世界到底认不认账。**

## Current Snapshot Source

当前 external lane 的**状态表本身**不再手写。请直接看：

- `docs/generated/external-lane-snapshot.md`
- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/release/release-evidence-attest-readiness.json`

## Verification Rules

- repo-side green 不等于 external lane green
- external lane 只在 fresh artifact + runtime metadata + same-run proof 同时满足时才算 `verified`
- 平台权限问题必须写成平台 blocker，不能伪装成仓库 bug
- 远端仓库当前是否公开、是否具备 branch protection 平台能力，也属于 external truth，不得由本地 docs 单方面宣布
- actor-sensitive remote truth 必须从 `remote-platform-truth.json` 读取，不能把一次 probe 的账号上下文偷换成永久事实

## Reading Rule

- 解释层只负责说明“为什么 blocked / verified”
- current state 只允许从 generated snapshot 或 runtime report 引用
- 如果 remote probe、GHCR readiness、release evidence readiness 与解释文档冲突，以 runtime report 为准

## Canonical Commands

Remote platform truth:

```bash
./bin/remote-platform-probe --repo xiaojiou176-org/video-analysis-extract
python3 scripts/governance/check_remote_required_checks.py
```

GHCR / external image:

```bash
./scripts/ci/check_standard_image_publish_readiness.sh
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
gh workflow run build-ci-standard-image.yml --ref main
```

Release evidence:

```bash
python3 scripts/release/check_release_evidence_attest_readiness.py --release-tag <tag>
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
