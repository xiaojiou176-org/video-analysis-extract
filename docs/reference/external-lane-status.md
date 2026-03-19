# External Lane Status

本页专门回答一个问题：**仓库内部已经绿了以后，外部世界到底认不认账。**

## Current Snapshot Source

当前 external lane 的**状态表本身**不再写进 tracked docs。请直接看：

- `.runtime-cache/reports/governance/remote-platform-truth.json`
- `.runtime-cache/reports/governance/standard-image-publish-readiness.json`
- `.runtime-cache/reports/release/release-evidence-attest-readiness.json`

`docs/generated/external-lane-snapshot.md` 现在只保留 pointer / reading rule，不再承载 current verdict payload。

当前 canonical lane 名称仍然是：

- GHCR standard image
- Release evidence attestation
- `rsshub-youtube-ingest-chain`
- `resend-digest-delivery-chain`

这些 current-state artifact 还必须满足一条额外规则：

- runtime metadata 的 `source_commit` 必须和当前 HEAD 对齐；旧 commit 产物只能当历史档案，不能当 current snapshot

## Verification Rules

- repo-side green 不等于 external lane green
- `governance-audit PASS` 也不等于 external lane green；它连 repo-side strict current receipt 都不能单独替代
- `remote-required-checks=status=pass` 只证明 merge-relevant required-check integrity，也就是 `docs/generated/required-checks.md` 与远端 branch protection required checks 没漂移；它回答的是“PR/merge 会看的 required lane 清单有没有对齐”，其中现在包含 `remote-integrity`，但它仍不证明 `ci-final-gate`、`live-smoke` 或 nightly terminal closure
- external lane 只在 fresh artifact + runtime metadata + same-run proof 同时满足时才算 `verified`
- 对消费 remote workflow 结果的 lane，`verified` 还必须满足：最新成功 run 的 `headSha == 当前 HEAD`
- 如果 remote workflow 成功的是旧 commit，那份 run 只能算历史证据，不能升级当前状态
- 平台权限问题必须写成平台 blocker，不能伪装成仓库 bug
- GHCR lane 若 workflow artifact 记录 `failed_step_name=Build and push strict CI standard image` 且 `failure_signature=blob-head-403-forbidden`，应解释为：preflight 已过，真正失败落在 registry blob write 边界
- `check_standard_image_publish_readiness.sh` 现在不仅检查 token 路径和 GitHub Packages API 可见性；当显式 token 路径可用时，它还会预探 `ghcr.io/v2/<repo>/blobs/uploads/`。`202` 才算 blob write 预检通过；`401/403` 应直接按平台写权限 blocker 处理
- GHCR 预检会优先对齐 workflow secret 路径：`GHCR_WRITE_USERNAME` / `GHCR_WRITE_TOKEN`，其次才是本地调试用的 `GHCR_USERNAME` / `GHCR_TOKEN`，最后才退回 GitHub Actions / `gh auth` 上下文
- 远端仓库当前是否公开、是否具备 branch protection 平台能力，也属于 external truth，不得由本地 docs 单方面宣布
- actor-sensitive remote truth 必须从 `remote-platform-truth.json` 读取，不能把一次 probe 的账号上下文偷换成永久事实
- `ready` / `queued` / `in_progress` 只能表示“尚未闭环完成”，不能包装成 external done

## Reading Rule

- 解释层只负责说明“为什么 blocked / verified”
- repo-side newcomer / strict receipt 请看 `.runtime-cache/reports/governance/newcomer-result-proof.json`；本页不负责替 repo-side done 兜底
- current state 只允许从 runtime report 引用；tracked generated docs 只能当 pointer / reading rule
- `.runtime-cache/reports/governance/current-state-summary.md` 这类 runtime 聚合页也必须先过“票据日期检查”：先看它自己的 `.meta.json` `source_commit` 是否等于当前 HEAD；如果不是，它只能算 historical snapshot
- 如果 runtime report 的 `source_commit` 不等于当前 HEAD，这份 report 只能当历史证据，不得当 current state
- 如果 remote probe、GHCR readiness、release evidence readiness 与解释文档冲突，以 runtime report 为准
- `remote-required-checks` 是 external reading rule 里的“merge-relevant required lane 清单对齐检查”，不是 terminal CI 收据；`ci-final-gate`、`live-smoke`、nightly lanes 仍要分别看它们自己的 current runtime/workflow 证据
- 如果 GHCR blocked 的当前 run 已明确给出 failed step / failure signature，优先用这些字段判断失败是在 preflight、buildx setup，还是 build-and-push 的最后一跳
- 如果 remote workflow 还是旧 head，summary/pointer 最多只能诚实到 `historical`、`ready` 或 `blocked`；绝不能把这份旧 run 包装成当前 `verified`

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
- 对 GHCR lane，若当前 workflow 已提供 failed job/step 或 failure signature，汇报里必须带上这些字段
- 不得用 repo-side governance 或 newcomer receipt 替 external lane 补票
