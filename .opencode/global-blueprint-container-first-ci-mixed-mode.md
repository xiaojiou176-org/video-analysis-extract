# Blueprint

## 1. Goal
### Scope
- 在范围内：建立 repo-pinned 标准环境容器入口；让 strict local validation 与 CI 重任务统一走 `scripts/run_in_standard_env.sh`；把长 workflow shell orchestration 抽到 repo scripts；同步 mixed-mode 文档；完成本地验证证据收集。
- 不在范围内：业务功能重写；删除现有 host-friendly 开发入口；新增外部镜像仓库发布链；放宽 mutation/coverage/live-smoke 门禁。

### Minimal Verifiable Slice
- 一个可运行的 `scripts/run_in_standard_env.sh` + `scripts/lib/standard_env.sh`
- `scripts/quality_gate.sh --mode pre-push --strict-full-run 1 ...` 能在宿主发起、在标准环境内重执行
- `.github/workflows/ci.yml` 至少让 backend strict jobs 改为通过该标准环境入口运行

### Key Risks
- 共享文件集中在 `.github/workflows/ci.yml`、`scripts/quality_gate.sh`、`.devcontainer/Dockerfile`，若无明确归属会产生冲突
- 当前主工作树已有大量未提交改动，必须隔离 worktree 实施，避免把 mutation 收尾现场与环境改造混写
- 现有 contract tests 会卡住任何随意重构；必须先扩充测试再改生产脚本
- live smoke 与 web e2e 对宿主/容器网络、secrets、Temporal 依赖敏感，需分波次推进，不能一口气混改

## 2. Task Matrix
| # | Task | Owner | Wave | Input Dependency | Definition of Done |
|:--|:-----|:------|:-----|:-----------------|:-------------------|
| 1 | 锁定标准环境容器契约（tests first） | l3-implementer | Wave 1 | Plan + Blueprint | 新增/更新 contract tests，先红后绿；`run_in_standard_env.sh` 与 helper 存在；`quality_gate.sh` strict 模式具备容器重执行入口 |
| 2 | 抽取后端 CI 容器脚本 | l3-implementer | Wave 2 | #1 | 新增 `scripts/ci_python_tests.sh`；backend strict jobs 改经标准环境执行；相关 contract tests 通过 |
| 3 | 抽取 Web 与 live smoke 容器脚本 | l3-implementer | Wave 3 | #1, #2 | 新增 `scripts/ci_web_e2e.sh` / `scripts/ci_live_smoke.sh`；相关 workflow job 改经标准环境执行；contract tests 通过 |
| 4 | 同步 mixed-mode 文档 | l3-implementer | Wave 4 | #2, #3 | `README.md`、`docs/start-here.md`、`docs/runbook-local.md`、`docs/testing.md` 文案与代码一致；docs parity 通过 |
| 5 | 执行全链路验证矩阵 | l3-implementer | Wave 5 | #2, #3, #4 | focused contract tests、wrapper smoke、backend parity path、至少一个 browser 的 web parity path、strict local chain 有证据输出 |

## 3. Coordination Notes
### File Ownership Boundaries
- `apps/api/tests/test_quality_gate_script_contract.py`: Wave 1 owner only
- `apps/api/tests/test_api_real_smoke_script_contract.py`: Wave 2 owner only
- `apps/worker/tests/test_standard_env_wrapper_contract.py`: Wave 1 owner only
- `apps/worker/tests/test_ci_workflow_strictness.py`: 串行共享文件，按 Wave 1 → Wave 2 → Wave 3 顺序单 owner 修改
- `.devcontainer/Dockerfile`: Wave 1 owner only
- `.devcontainer/devcontainer.json`: Wave 1 owner only
- `scripts/lib/standard_env.sh`: Wave 1 owner only
- `scripts/run_in_standard_env.sh`: Wave 1 owner only
- `scripts/quality_gate.sh`: shared-file law applies，Wave 1 owner only
- `.github/workflows/ci.yml`: shared-file law applies，Wave 2 then Wave 3 serial only
- `scripts/ci_python_tests.sh`: Wave 2 owner only
- `scripts/ci_web_e2e.sh`: Wave 3 owner only
- `scripts/ci_live_smoke.sh`: Wave 3 owner only
- `README.md`, `docs/start-here.md`, `docs/runbook-local.md`, `docs/testing.md`: Wave 4 owner only

### Expected Blockers
- 可能无现成 `.worktrees/` 目录，需要使用 agent isolation worktree
- 某些 local verification 在当前宿主可能因 Docker / Playwright / secrets 缺失失败；需区分“契约正确但环境缺依赖”与“实现错误”
- 当前主工作树脏，不能依赖主工作树的 git status 作为环境改造验收依据

### Escalation Path
- L3 self-repair → L1 arbitration
- 本次不直接唤醒 L2 product/backend/frontend lead 写架构工件，因为 contract 已在计划与 Blueprint 锁定；若出现 CI/shared-file 冲突，再由 L1 重排

### Shared-File Rules
- `scripts/quality_gate.sh`、`.github/workflows/ci.yml`、`.devcontainer/Dockerfile` 为共享关键文件
- 这些文件的改动只允许最小化服务于标准环境统一入口
- 对这些文件的每次波次修改后必须保留：相关 contract test 通过证据 + 若适用的 wrapper smoke 证据

## 4. Verification Plan
### Diff Review / LSP / Build / Test
- Wave 1：运行新增/更新的 contract tests，验证 RED→GREEN；做 wrapper smoke
- Wave 2：运行 backend contract tests + backend container path scripts
- Wave 3：运行 workflow strictness tests + web/live smoke container scripts 的最小可行验证
- Wave 4：运行 docs parity / doc drift checks
- Wave 5：汇总 focused contract tests + strict local chain

### Review / Acceptance Gate
- 每个波次必须满足：diff 符合该波次文件边界；无未授权共享文件改动；相关测试通过；没有用弱化门禁换取通过
- 最终 Global Done 需满足：标准环境入口存在、strict local validation 与 CI 重任务统一经该入口、文档同步完成、验证证据齐全

### Evidence to Collect
- `docs/plans/2026-03-10-container-first-ci-mixed-mode.md`
- `.opencode/global-blueprint-container-first-ci-mixed-mode.md`
- 各波次相关 pytest 输出
- `./scripts/run_in_standard_env.sh` smoke 输出
- `./scripts/quality_gate.sh --mode pre-push --strict-full-run 1 ...` 重执行证据
- 如执行成功：backend/web/live smoke container-path 输出摘要
