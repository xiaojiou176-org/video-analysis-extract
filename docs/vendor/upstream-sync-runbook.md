# Upstream Sync Runbook

## 1. 目标与边界

本 runbook 定义第三方依赖上游同步的唯一标准流程：

- 上游代码来源：`fork`
- 代码落地方式：`git subtree`
- 版本审计锚点：`UPSTREAM.lock`

本流程适用于 `vendor/<name>` 目录下的第三方代码同步与审计。

## 2. 强制规范

1. 所有第三方代码必须进入 `vendor/` 命名空间，禁止散落在其他目录。
2. 每个 subtree 前缀必须有且仅有一个 `UPSTREAM.lock`：
   - 位置：`<subtree_prefix>/UPSTREAM.lock`
3. `UPSTREAM.lock` 必填字段：
   - `schema_version`
   - `vendor`
   - `upstream_repo`
   - `upstream_ref`
   - `upstream_commit`
   - `subtree_prefix`
   - `sync_strategy`
   - `sync_timestamp_utc`
   - `sync_actor`
4. `sync_strategy` 必须为 `subtree`。
5. `subtree_prefix` 必须以 `vendor/` 开头。

## 3. 标准操作流（fork + subtree + lock）

1. 在 GitHub 上 fork 对应上游仓库（组织级 fork 优先）。
2. 创建同步分支（禁止直接在 `main` 操作）。
3. 先 dry-run 预览命令模板：

```bash
bash scripts/vendor/upstream_sync.sh \
  --vendor <vendor_name> \
  --upstream-url <fork_or_upstream_git_url> \
  --upstream-ref <tag_or_branch_or_sha> \
  --prefix vendor/<vendor_name> \
  --dry-run
```

4. 审查模板命令与参数后执行同步：

```bash
bash scripts/vendor/upstream_sync.sh \
  --vendor <vendor_name> \
  --upstream-url <fork_or_upstream_git_url> \
  --upstream-ref <tag_or_branch_or_sha> \
  --prefix vendor/<vendor_name> \
  --execute
```

5. 校验 lock 文件并提交：

```bash
bash scripts/vendor/validate_upstream_lock.sh --root .
git add vendor/<vendor_name> .github/workflows/vendor-governance.yml scripts/vendor docs/vendor
git commit -m "chore(vendor): sync <vendor_name> to <upstream_ref>"
```

## 4. `UPSTREAM.lock` 格式示例

```text
schema_version: 1
vendor: yt-dlp
upstream_repo: https://github.com/yt-dlp/yt-dlp.git
upstream_ref: refs/tags/2026.01.01
upstream_commit: 0123456789abcdef0123456789abcdef01234567
subtree_prefix: vendor/yt-dlp
sync_strategy: subtree
sync_timestamp_utc: 2026-02-21T00:00:00Z
sync_actor: github-actions[bot]
squash: true
```

说明：该文件是审计事实源，不允许手工删除必填字段。

## 5. 风险控制与回滚

1. 同步前工作区必须干净（默认强制检查）。
2. 默认禁止在 `main/master` 直接执行（可显式放开）。
3. 若同步引发问题，使用普通 git 回滚策略（`git revert` 对应同步 commit），禁止使用破坏性命令。

## 6. CI 治理

`vendor-governance` workflow 会在 PR / push 时自动执行：

- 脚本语法检查（`bash -n`）
- `UPSTREAM.lock` 结构与必填字段检查

若 lock 格式不合法或缺失必填字段，CI 直接失败。
