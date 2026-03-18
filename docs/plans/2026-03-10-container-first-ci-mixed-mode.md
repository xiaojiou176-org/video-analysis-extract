# Container-First CI Mixed-Mode Environment Parity Implementation Plan

> Historical note: this plan describes the transition state that introduced `run_in_standard_env.sh`. The current repository target is stricter: `scripts/strict_ci_entry.sh` + the pinned standard image are the authority for CI-parity validation, and mixed-mode host execution is no longer the normative gate path.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move strict CI and strict local validation onto one repo-pinned Docker environment while keeping host-friendly local development scripts.

**Architecture:** Build one standard environment image from repo-controlled files and execute strict gates through a new `scripts/ci/run_in_standard_env.sh` wrapper. Keep `scripts/full_stack.sh`, `scripts/ci/api_real_smoke_local.sh`, and `scripts/ci/smoke_full_stack.sh` as ergonomic local entrypoints, but make CI jobs and strict local gates call the same repo scripts from inside the standard container so host drift stops mattering.

**Tech Stack:** GitHub Actions, Docker, DevContainer, Bash, uv, pytest, Playwright, FastAPI, Next.js

---

## Locked Design Decisions

1. **Chosen approach: repo-local standard-env Docker wrapper**
   - Use a repo-controlled Docker image plus `docker build`/`docker run` wrapper.
   - Do **not** introduce GHCR publishing in this pass.
   - Do **not** rely on GitHub Actions job-level `container:` yet.

2. **Mixed mode stays intentional**
   - Daily local dev (`dev_api.sh`, `dev_worker.sh`, `full_stack.sh up`) stays host-friendly.
   - Strict validation (`quality_gate.sh --strict-full-run 1`) and strict CI jobs run in the container path.

3. **YAML becomes orchestration, not business logic**
   - Long shell blocks move out of `.github/workflows/ci.yml` into repo scripts.
   - CI must call repo scripts so local and CI use the same executable logic.

4. **Bootstrap jobs may remain host-level**
   - `changes`, `required-ci-secrets`, and lightweight preflight/bootstrap jobs can stay host-level because they are responsible for deciding whether containerized work should run.
   - Heavy correctness gates (`quality-gate-pre-push`, `python-tests`, `api-real-smoke`, `web-e2e`, `live-smoke`) must move to the standard env path.

## Non-Goals

- Do not rewrite app business logic.
- Do not replace local dev ergonomics with mandatory container-only development.
- Do not add a registry publishing pipeline in this pass.
- Do not weaken current coverage/mutation/live-smoke gates.

---

### Task 1: Lock the new standard-env contract with failing tests

**Files:**
- Create: `apps/worker/tests/test_standard_env_wrapper_contract.py`
- Modify: `apps/api/tests/test_quality_gate_script_contract.py`
- Modify: `apps/worker/tests/test_ci_workflow_strictness.py`

**Step 1: Write the failing tests**

```python
from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_standard_env_wrapper_builds_repo_pinned_image() -> None:
    script = (_repo_root() / "scripts" / "run_in_standard_env.sh").read_text(encoding="utf-8")

    assert ".devcontainer/Dockerfile" in script
    assert "docker build" in script
    assert "docker run --rm" in script
    assert "/var/run/docker.sock" in script
    assert "VD_IN_STANDARD_ENV" in script
    assert "--network host" in script
```

```python
def test_quality_gate_strict_full_run_reexecs_in_standard_env() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert "run_in_standard_env.sh" in script
    assert "STRICT_FULL_RUN" in script
    assert "VD_IN_STANDARD_ENV" in script
```

```python
def test_strict_ci_jobs_use_standard_env_wrapper_and_drop_host_bootstrap() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    for job_name in ("quality-gate-pre-push", "python-tests", "api-real-smoke", "web-e2e", "live-smoke"):
        assert "scripts/ci/run_in_standard_env.sh" in workflow

    assert "sudo apt-get install -y postgresql-client" not in workflow
    assert "actions/setup-python" in workflow  # bootstrap jobs may still use it
```

**Step 2: Run tests to verify they fail**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest \
  apps/worker/tests/test_standard_env_wrapper_contract.py \
  apps/api/tests/test_quality_gate_script_contract.py \
  apps/worker/tests/test_ci_workflow_strictness.py -q
```

Expected: FAIL because the wrapper script does not exist yet and the workflow/script strings are not present yet.

**Step 3: Write minimal implementation placeholders**

- Create `scripts/ci/run_in_standard_env.sh` with `usage`, `docker build`, and `docker run` skeleton.
- Add the minimal `quality_gate.sh` hook point for strict re-exec.
- Add placeholder workflow calls to the wrapper before removing old host bootstrap logic.

**Step 4: Run tests to verify they pass**

Run the same command as Step 2.

Expected: PASS for the new contract expectations.

**Step 5: Commit**

```bash
git add \
  apps/worker/tests/test_standard_env_wrapper_contract.py \
  apps/api/tests/test_quality_gate_script_contract.py \
  apps/worker/tests/test_ci_workflow_strictness.py \
  scripts/ci/run_in_standard_env.sh \
  scripts/quality_gate.sh \
  .github/workflows/ci.yml
git commit -m "test: lock standard env container contract"
```

---

### Task 2: Build the shared standard environment image and wrapper

**Files:**
- Modify: `.devcontainer/Dockerfile`
- Modify: `.devcontainer/devcontainer.json`
- Create: `scripts/lib/standard_env.sh`
- Create: `scripts/ci/run_in_standard_env.sh`
- Test: `apps/worker/tests/test_standard_env_wrapper_contract.py`

**Step 1: Write the failing test for the helper library contract**

```python
def test_standard_env_wrapper_uses_helper_library_and_recursion_guard() -> None:
    script = (_repo_root() / "scripts" / "run_in_standard_env.sh").read_text(encoding="utf-8")
    helper = (_repo_root() / "scripts" / "lib" / "standard_env.sh").read_text(encoding="utf-8")

    assert 'source "$ROOT_DIR/scripts/lib/standard_env.sh"' in script
    assert 'if [[ "${VD_IN_STANDARD_ENV:-0}" == "1" ]]' in script
    assert 'build_standard_env_image' in helper
    assert 'run_in_standard_env' in helper
```

**Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests/test_standard_env_wrapper_contract.py -q
```

Expected: FAIL because `scripts/lib/standard_env.sh` does not exist yet.

**Step 3: Write minimal implementation**

`./scripts/lib/standard_env.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STANDARD_ENV_IMAGE="${VD_STANDARD_ENV_IMAGE:-video-analysis-standard-env:local}"

build_standard_env_image() {
  docker build -f "$ROOT_DIR/.devcontainer/Dockerfile" -t "$STANDARD_ENV_IMAGE" "$ROOT_DIR"
}

run_in_standard_env() {
  local command=("$@")
  docker run --rm --init \
    --network host \
    -v "$ROOT_DIR:/workspace" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -w /workspace \
    -e VD_IN_STANDARD_ENV=1 \
    -e CI="${CI:-}" \
    -e GITHUB_ACTIONS="${GITHUB_ACTIONS:-}" \
    "$STANDARD_ENV_IMAGE" \
    "${command[@]}"
}
```

`./scripts/ci/run_in_standard_env.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/standard_env.sh"

if [[ "${VD_IN_STANDARD_ENV:-0}" == "1" ]]; then
  exec "$@"
fi

build_standard_env_image
run_in_standard_env "$@"
```

`./.devcontainer/Dockerfile`
```dockerfile
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

ARG UV_VERSION=0.6.6
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    jq \
    postgresql-client \
    sqlite3 \
    ripgrep \
  && python3 -m pip install --no-cache-dir "uv==${UV_VERSION}" \
  && rm -rf /var/lib/apt/lists/*

ENV VD_IN_STANDARD_ENV=1
WORKDIR /workspace
```

`./.devcontainer/devcontainer.json`
```json
{
  "name": "video-analysis-standard-env",
  "build": {
    "dockerfile": "Dockerfile",
    "context": ".."
  },
  "remoteUser": "vscode",
  "workspaceFolder": "/workspaces/${localWorkspaceFolderBasename}",
  "mounts": [
    "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind"
  ],
  "features": {
    "ghcr.io/devcontainers/features/docker-outside-of-docker:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  }
}
```

**Step 4: Run tests to verify they pass**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests/test_standard_env_wrapper_contract.py -q
```

Expected: PASS.

**Step 5: Smoke the wrapper itself**

Run:
```bash
./scripts/ci/run_in_standard_env.sh bash -lc 'python3 --version && uv --version && pwd'
```

Expected: container boots, versions print, working directory is `/workspace`.

**Step 6: Commit**

```bash
git add .devcontainer/Dockerfile .devcontainer/devcontainer.json scripts/lib/standard_env.sh scripts/ci/run_in_standard_env.sh apps/worker/tests/test_standard_env_wrapper_contract.py
git commit -m "feat(env): add shared standard environment wrapper"
```

---

### Task 3: Make strict local gates re-exec through the standard environment

**Files:**
- Modify: `scripts/quality_gate.sh`
- Modify: `apps/api/tests/test_quality_gate_script_contract.py`
- Test: `apps/worker/tests/test_standard_env_wrapper_contract.py`

**Step 1: Write the failing test**

```python
def test_quality_gate_supports_containerized_strict_mode_without_recursion() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")

    assert 'CONTAINERIZED="auto"' in script
    assert '--containerized 0|1|auto' in script
    assert 'if [[ "${VD_IN_STANDARD_ENV:-0}" != "1" ]]' in script
    assert 'exec "$ROOT_DIR/scripts/ci/run_in_standard_env.sh"' in script
```

**Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/api/tests/test_quality_gate_script_contract.py -q
```

Expected: FAIL because the containerized strict-mode contract is not present yet.

**Step 3: Write minimal implementation**

Add to `scripts/quality_gate.sh`:
```bash
CONTAINERIZED="auto"

# parse --containerized 0|1|auto

if [[ "$MODE" == "pre-push" && "$STRICT_FULL_RUN" == "1" && "$CONTAINERIZED" != "0" && "${VD_IN_STANDARD_ENV:-0}" != "1" ]]; then
  exec "$ROOT_DIR/scripts/ci/run_in_standard_env.sh" \
    bash -lc "./scripts/quality_gate.sh $* --containerized 0"
fi
```

Rules:
- `pre-commit` stays host-friendly by default.
- `pre-push --strict-full-run 1` re-execs through container unless already inside standard env.
- `--containerized 0` exists for debugging and to avoid recursion.

**Step 4: Run tests to verify they pass**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/api/tests/test_quality_gate_script_contract.py apps/worker/tests/test_standard_env_wrapper_contract.py -q
```

Expected: PASS.

**Step 5: Run the profile-only local smoke in container**

Run:
```bash
./scripts/quality_gate.sh --mode pre-commit --profile local --profile-only
./scripts/quality_gate.sh --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0 --skip-mutation 1
```

Expected: the first remains host-friendly; the second re-execs through `run_in_standard_env.sh`.

**Step 6: Commit**

```bash
git add scripts/quality_gate.sh apps/api/tests/test_quality_gate_script_contract.py apps/worker/tests/test_standard_env_wrapper_contract.py
git commit -m "feat(gate): re-exec strict validation in standard env"
```

---

### Task 4: Extract backend CI execution into repo scripts and run it in the standard environment

**Files:**
- Create: `scripts/ci_python_tests.sh`
- Modify: `scripts/ci/api_real_smoke_local.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `apps/worker/tests/test_ci_workflow_strictness.py`
- Modify: `apps/api/tests/test_api_real_smoke_script_contract.py`

**Step 1: Write the failing tests**

```python
def test_python_tests_job_calls_repo_script_in_standard_env() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/ci_python_tests.sh" in workflow
    assert "./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_python_tests.sh'" in workflow
```

```python
def test_api_real_smoke_script_can_run_inside_standard_env_without_host_specific_bootstrap() -> None:
    script = (_repo_root() / "scripts" / "api_real_smoke_local.sh").read_text(encoding="utf-8")
    assert 'VD_IN_STANDARD_ENV' in script or 'run_in_standard_env.sh' not in script
    assert 'preflight_loopback_ipv4_connectivity' in script
```

**Step 2: Run tests to verify they fail**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest \
  apps/worker/tests/test_ci_workflow_strictness.py \
  apps/api/tests/test_api_real_smoke_script_contract.py -q
```

Expected: FAIL because the repo script and wrapper calls are not present yet.

**Step 3: Write minimal implementation**

Create `scripts/ci_python_tests.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

mkdir -p .runtime-cache
uv sync --frozen --extra dev --extra e2e
uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q -rA -n 2 \
  --cov=apps/worker/worker \
  --cov=apps/api/app \
  --cov=apps/mcp/server.py \
  --cov=apps/mcp/tools \
  --cov-report=term-missing:skip-covered \
  --cov-report=xml:.runtime-cache/reports/python/python-coverage.xml \
  --cov-fail-under=95 \
  --junitxml=.runtime-cache/reports/python/python-tests-junit.xml
uv run coverage report \
  --include="apps/worker/worker/pipeline/orchestrator.py,*/apps/worker/worker/pipeline/orchestrator.py,apps/worker/worker/pipeline/policies.py,*/apps/worker/worker/pipeline/policies.py,apps/worker/worker/pipeline/runner.py,*/apps/worker/worker/pipeline/runner.py,apps/worker/worker/pipeline/types.py,*/apps/worker/worker/pipeline/types.py" \
  --show-missing \
  --fail-under=95
uv run coverage report \
  --include="apps/api/app/routers/ingest.py,*/apps/api/app/routers/ingest.py,apps/api/app/routers/jobs.py,*/apps/api/app/routers/jobs.py,apps/api/app/routers/subscriptions.py,*/apps/api/app/routers/subscriptions.py,apps/api/app/routers/videos.py,*/apps/api/app/routers/videos.py,apps/api/app/services/jobs.py,*/apps/api/app/services/jobs.py,apps/api/app/services/subscriptions.py,*/apps/api/app/services/subscriptions.py,apps/api/app/services/videos.py,*/apps/api/app/services/videos.py" \
  --show-missing \
  --fail-under=95
```

Make `python-tests` and `api-real-smoke` jobs thin in `.github/workflows/ci.yml`:
```yaml
- name: Run python tests in standard env
  run: ./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_python_tests.sh'

- name: Run API real smoke in standard env
  run: ./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci/api_real_smoke_local.sh'
```

Remove from those jobs:
- repeated `actions/setup-python` inside strict jobs,
- repeated `sudo apt-get install -y postgresql-client`,
- repeated inline long bash blocks that now live in repo scripts.

**Step 4: Run tests to verify they pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Run the extracted backend repo scripts locally in the container path**

Run:
```bash
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_python_tests.sh'
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci/api_real_smoke_local.sh'
```

Expected: commands execute through the same container path CI will use.

**Step 6: Commit**

```bash
git add scripts/ci_python_tests.sh scripts/ci/api_real_smoke_local.sh .github/workflows/ci.yml apps/worker/tests/test_ci_workflow_strictness.py apps/api/tests/test_api_real_smoke_script_contract.py
git commit -m "feat(ci): run backend validation through standard env"
```

---

### Task 5: Extract web E2E execution into repo scripts and run it in the standard environment

**Files:**
- Create: `scripts/ci_web_e2e.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `apps/worker/tests/test_ci_workflow_strictness.py`
- Modify: `apps/web/tests/e2e/test_subscriptions.py` only if existing assertions still drift after environment parity work

**Step 1: Write the failing test**

```python
def test_web_e2e_job_calls_repo_script_in_standard_env() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "scripts/ci_web_e2e.sh" in workflow
    assert "./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_web_e2e.sh" in workflow
    assert "Install Temporal CLI" not in workflow
```

**Step 2: Run test to verify it fails**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests/test_ci_workflow_strictness.py -q
```

Expected: FAIL because `scripts/ci_web_e2e.sh` is not referenced yet.

**Step 3: Write minimal implementation**

Create `scripts/ci_web_e2e.sh` with the existing web E2E orchestration moved out of YAML:
```bash
#!/usr/bin/env bash
set -euo pipefail

BROWSER="${1:-chromium}"
mkdir -p .runtime-cache
uv sync --frozen --extra dev --extra e2e
bash scripts/ci/prepare_web_runtime.sh
# allocate ports
# start temporal
# run migrations
# start api
# start worker
# run pytest apps/web/tests/e2e -q for the selected browser
# stop processes on exit
```

Make `.github/workflows/ci.yml` call the repo script:
```yaml
- name: Run web e2e in standard env
  run: ./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_web_e2e.sh ${{ matrix.browser }}'
```

Rules:
- Port allocation stays inside the repo script.
- The job matrix stays in YAML.
- Start/stop logic moves into the repo script.
- No job-local `apt-get` / curl install / Temporal download logic remains in YAML.

**Step 4: Run test to verify it passes**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Run the repo script locally in the container path**

Run:
```bash
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_web_e2e.sh chromium'
```

Expected: the same orchestration path CI uses runs locally.

**Step 6: Commit**

```bash
git add scripts/ci_web_e2e.sh .github/workflows/ci.yml apps/worker/tests/test_ci_workflow_strictness.py
git commit -m "feat(web-ci): run web e2e through standard env"
```

---

### Task 6: Move live smoke onto the same repo-script + standard-env path

**Files:**
- Create: `scripts/ci_live_smoke.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `apps/worker/tests/test_ci_workflow_strictness.py`
- Test: `apps/worker/tests/test_full_stack_env_runtime_regression.py`

**Step 1: Write the failing tests**

```python
def test_live_smoke_job_calls_repo_script_in_standard_env() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/ci_live_smoke.sh" in workflow
    assert "./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_live_smoke.sh'" in workflow
```

```python
def test_strict_local_validation_chain_still_references_live_smoke_and_real_postgres() -> None:
    script = (_repo_root() / "scripts" / "quality_gate.sh").read_text(encoding="utf-8")
    assert "api_real_smoke_local" in script
    assert "smoke_full_stack" in script
```

**Step 2: Run tests to verify they fail**

Run:
```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest apps/worker/tests/test_ci_workflow_strictness.py apps/worker/tests/test_full_stack_env_runtime_regression.py -q
```

Expected: FAIL because the live smoke repo script is not wired yet.

**Step 3: Write minimal implementation**

Create `scripts/ci_live_smoke.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

mkdir -p .runtime-cache
uv sync --frozen --extra dev --extra e2e
# run migrations
# start temporal
# start api + worker
# validate secrets
# run scripts/ci/e2e_live_smoke.sh with the same strict flags from ci.yml
# stop processes on exit
```

Make `.github/workflows/ci.yml` call it:
```yaml
- name: Run live smoke in standard env
  run: ./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_live_smoke.sh'
```

Rules:
- Keep secret gating in the workflow/job env.
- Move runtime orchestration into the repo script.
- Preserve current strict flags: `--require-api 1`, `--require-secrets 1`, `--computer-use-strict 1`, `--computer-use-skip 0`.

**Step 4: Run tests to verify they pass**

Run the same command as Step 2.

Expected: PASS.

**Step 5: Run live smoke locally only if required secrets are present**

Run:
```bash
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_live_smoke.sh'
```

Expected: PASS when secrets exist; otherwise fail for the correct reason (missing secrets), not because of host drift.

**Step 6: Commit**

```bash
git add scripts/ci_live_smoke.sh .github/workflows/ci.yml apps/worker/tests/test_ci_workflow_strictness.py apps/worker/tests/test_full_stack_env_runtime_regression.py
git commit -m "feat(live-smoke): run strict smoke through standard env"
```

---

### Task 7: Update docs to make mixed mode explicit and auditable

**Files:**
- Modify: `README.md`
- Modify: `docs/start-here.md`
- Modify: `docs/runbook-local.md`
- Modify: `docs/testing.md`

**Step 1: Write the failing doc-drift assertion mentally before editing**

The docs must state all of the following after the change:
- local daily development remains host-friendly,
- strict CI and strict local validation use `scripts/ci/run_in_standard_env.sh`,
- `.devcontainer/Dockerfile` is the repo-pinned standard environment base,
- CI workflow shell logic moved into repo scripts,
- the strict validation chain is unchanged in semantics, only in execution environment.

**Step 2: Update the docs minimally**

Add these ideas:

`README.md`
```md
- Daily local development can still use `./scripts/full_stack.sh up` on the host.
- Strict validation and CI parity use `./scripts/ci/run_in_standard_env.sh ...`.
```

`docs/start-here.md`
```md
- Mixed mode: host for day-to-day dev, standard container for strict validation.
- Use `./scripts/ci/run_in_standard_env.sh bash -lc './scripts/quality_gate.sh --mode pre-push --strict-full-run 1 ...'` for CI-parity local validation.
```

`docs/runbook-local.md`
```md
- `scripts/ci/run_in_standard_env.sh` is the mandatory path for CI-parity runs.
- `full_stack.sh` remains the convenience path for interactive local development.
```

`docs/testing.md`
```md
- CI heavy jobs now call repo scripts inside the standard environment container.
- The fixed strict chain remains `full_stack.sh up -> api_real_smoke_local.sh -> smoke_full_stack.sh --offline-fallback 0 -> quality_gate.sh --mode pre-push --strict-full-run 1 ...`.
```

**Step 3: Verify docs and code agree**

Run:
```bash
python3 scripts/governance/check_contract_surfaces.py
bash scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged
```

Expected: PASS.

**Step 4: Commit**

```bash
git add README.md docs/start-here.md docs/runbook-local.md docs/testing.md
git commit -m "docs: explain mixed-mode standard env workflow"
```

---

### Task 8: Run the full verification matrix before push

**Files:**
- No new files required; update docs/tests only if verification reveals real drift.

**Step 1: Run focused contract tests first**

```bash
PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' \
uv run pytest \
  apps/api/tests/test_quality_gate_script_contract.py \
  apps/api/tests/test_api_real_smoke_script_contract.py \
  apps/worker/tests/test_standard_env_wrapper_contract.py \
  apps/worker/tests/test_full_stack_env_runtime_regression.py \
  apps/worker/tests/test_ci_workflow_strictness.py -q
```

Expected: PASS.

**Step 2: Smoke the standard environment wrapper directly**

```bash
./scripts/ci/run_in_standard_env.sh bash -lc 'python3 --version && uv --version && env | rg "^(CI|GITHUB_ACTIONS|VD_IN_STANDARD_ENV)=" || true'
```

Expected: `VD_IN_STANDARD_ENV=1` is visible in-container.

**Step 3: Run backend parity path**

```bash
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_python_tests.sh'
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci/api_real_smoke_local.sh'
```

Expected: PASS.

**Step 4: Run web parity path**

```bash
./scripts/ci/run_in_standard_env.sh bash -lc './scripts/ci_web_e2e.sh chromium'
```

Expected: PASS for at least one browser locally before matrix fan-out in CI.

**Step 5: Run strict local chain**

```bash
./scripts/full_stack.sh up
./scripts/ci/api_real_smoke_local.sh
./scripts/ci/smoke_full_stack.sh --offline-fallback 0
./scripts/quality_gate.sh --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

Expected: PASS. If any step fails, fix the underlying drift instead of weakening the gate.

**Step 6: Only after local green, push and observe remote CI**

```bash
git status --short
git push origin <branch>
```

Expected: remote CI is now a confirmation layer, not the first place environment mismatch is discovered.

**Step 7: Final commit cleanup if needed**

```bash
git status --short
```

Expected: clean working tree before merge or final handoff.

---

## Execution Notes

- Preserve existing gate semantics; change *where* they run, not *what* they require.
- Do not weaken mutation, coverage, or live-smoke thresholds to get the container path green.
- Keep bootstrap jobs host-level only when they are deciding whether heavier containerized jobs should run.
- Prefer extracting long YAML shell blocks into repo scripts over embedding more bash into workflow YAML.
- If a new container/image requirement forces doc drift, update docs in the same task rather than batching all drift to the end.
- If a step needs a new shared file beyond those listed here, update the plan before editing to avoid scope creep.
