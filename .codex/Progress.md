# Strict CI Mixed Mode Progress

> Updated: 2026-03-11 (America/Los_Angeles)

## 三层完成定义 (Layer 1/2/3)

### Layer 1: 本地确定性 CI
- 定义：在不依赖外部 GHCR 写权限和第三方 live provider 的前提下，本仓库硬门禁可在本地重复通过。
- 关注入口：`scripts/strict_ci_entry.sh`、`scripts/quality_gate.sh`、`scripts/env/final_governance_check.sh`。

### Layer 2: 本地容器闭环
- 定义：严格标准镜像被真实消费（不是旁路 host 模式），并完成容器内门禁与 smoke 链路。
- 关注入口：`scripts/run_in_standard_env.sh`、`scripts/lib/standard_env.sh`、`scripts/api_real_smoke_local.sh`。

### Layer 3: 外部平台闭环
- 定义：GHCR 远端推拉/写回 + GitHub Actions 远端运行 + 真实 secrets/live provider 全量复验。
- 备注：本次仅记录边界，不在本次本地收敛中判定完成。

## 本次实证通过命令与结果

1. `bash -n scripts/strict_ci_entry.sh scripts/quality_gate.sh scripts/api_real_smoke_local.sh scripts/run_in_standard_env.sh scripts/lib/standard_env.sh scripts/bootstrap_strict_ci_runtime.sh`
   - 结果：退出码 `0`（脚本语法检查通过）。

2. `uv sync --frozen --extra dev --extra e2e`
   - 结果：退出码 `0`，补齐依赖（本次输出新增安装 25 个包）。

3. `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_standard_env_wrapper_contract.py apps/api/tests/test_quality_gate_script_contract.py apps/api/tests/test_api_real_smoke_script_contract.py -q`
   - 结果：退出码 `0`，`16 passed in 0.57s`。

## 关键 Blocker 时间线/清单

1. 2026-03-11 00:24-01:55（提交链路：`fdca110` -> `34d5141`）完成 strict CI closeout 主线，目标从混合路径收敛到 strict 标准环境路径。
2. 标准环境检测分叉导致重入判断不一致：
   - 修复点：`scripts/lib/standard_env.sh` 新增 `is_running_inside_standard_env`，并被 `scripts/strict_ci_entry.sh` 与 `scripts/run_in_standard_env.sh` 共用。
3. strict 模式运行时依赖未统一预热：
   - 修复点：新增 `scripts/bootstrap_strict_ci_runtime.sh`，在 strict 入口统一 `uv sync` + web `npm ci` 条件化预热。
4. `api_real_smoke_local` 在容器场景易受 Temporal 可达性阻断：
   - 修复点：`scripts/api_real_smoke_local.sh` 新增可达性探测与临时 Temporal dev server 自举/清理逻辑。
5. contract diff 导出依赖 DB 环境导致门禁脆弱：
   - 修复点：`scripts/quality_gate.sh` 在 `run_contract_diff_local_gate()` 注入最小 `DATABASE_URL=sqlite+pysqlite:///:memory:`。
6. smoke 本地门禁缺少 host/container 双态默认值：
   - 修复点：`scripts/quality_gate.sh` 为 `DATABASE_URL`/`TEMPORAL_TARGET_HOST`/workspace/artifact 路径提供双态默认。
7. 本次写入过程中的真实阻塞：
   - 现象：首次运行合同测试报错 `ModuleNotFoundError: No module named 'fastapi'`。
   - 处理：执行 `uv sync --frozen --extra dev --extra e2e` 后重跑，16 项合同测试通过。

## 当前边界 (Layer 3 未验证项)

- GHCR 远端 push/writeback 未在本次复跑验证。
- GitHub Actions 远端最终绿灯未在本次复跑验证。
- live smoke 的外部 provider secrets 路径未在本次复跑验证。

## 下次继续时优先读取/执行

### 先读文件
1. `scripts/lib/standard_env.sh`
2. `scripts/strict_ci_entry.sh`
3. `scripts/quality_gate.sh`
4. `scripts/api_real_smoke_local.sh`
5. `scripts/bootstrap_strict_ci_runtime.sh`
6. `apps/worker/tests/test_standard_env_wrapper_contract.py`
7. `apps/api/tests/test_quality_gate_script_contract.py`
8. `apps/api/tests/test_api_real_smoke_script_contract.py`

### 先跑命令
1. `uv sync --frozen --extra dev --extra e2e`
2. `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests/test_standard_env_wrapper_contract.py apps/api/tests/test_quality_gate_script_contract.py apps/api/tests/test_api_real_smoke_script_contract.py -q`
3. `./scripts/strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0`
4. `bash scripts/env/final_governance_check.sh`

## 最终完成态摘要

### Layer 1
- 状态：PASS
- 已真实通过：
  - `./scripts/quality_gate.sh --mode pre-commit --profile local`
  - `./scripts/strict_ci_entry.sh --mode web-test-build`
  - `./scripts/strict_ci_entry.sh --mode pre-push --strict-full-run 1 --ci-dedupe 0`
  - `bash scripts/env/final_governance_check.sh`

### Layer 2
- 状态：PASS
- 已真实通过：
  - `docker pull ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard@sha256:d8088536c52e0e572407f8983255a1d8b97556009642cc16a71191c8aedfa7a9`
  - `VD_STANDARD_ENV_BUILD_PLATFORMS='linux/arm64' ./scripts/build_ci_standard_image.sh --load --tag local-arm64-mixedfix`
  - `VD_STANDARD_ENV_IMAGE='ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard:local-arm64-mixedfix' ./scripts/run_in_standard_env.sh ...`
  - `VD_STANDARD_ENV_IMAGE='ghcr.io/xiaojiou176-org/video-analysis-extract-ci-standard:local-arm64-mixedfix' ./scripts/run_in_standard_env.sh bash -lc 'source ./scripts/bootstrap_strict_ci_runtime.sh && ... ./scripts/api_real_smoke_local.sh'`
  - local registry round-trip:
    - push 成功：`127.0.0.1:5101/video-analysis-extract-ci-standard:roundtrip-arm64`
    - pull 成功：`127.0.0.1:5101/video-analysis-extract-ci-standard:roundtrip-arm64`
    - run 探针成功：`docker run --rm 127.0.0.1:5101/video-analysis-extract-ci-standard:roundtrip-arm64 bash -lc '... node --version; uv --version; temporal --version'`
    - observed digest：`sha256:f6c2b1be3a7ca6bca63b85d25c5773fd3cf0368a12ae683d41a70041faa5a9da`

### Layer 3
- 状态：NOT VERIFIED
- 未在本次 closeout 中复跑：
  - GHCR push/writeback 最终再验证
  - GitHub Actions 远端最终验收
  - live/provider secret 路径

## 结论
- 本地可确定性全量 CI：全绿
- 本地容器闭环：完成
- 外部平台闭环：未实证，但与本地完成态严格分离
