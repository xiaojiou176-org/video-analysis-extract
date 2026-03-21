# Video Analysis Extraction (Phase3)

This repository is a local-first video analysis system with four layers: `API + Worker + MCP + Web`.

- `apps/api`: the FastAPI control plane that serves `/api/v1/*`
- `apps/worker`: the Temporal worker that runs poll + pipeline flows
- `apps/mcp`: the FastMCP tool layer that forwards API capabilities
- `apps/web`: the Next.js admin console

## Public Status

This repository is currently operated as a **public source-first + limited-maintenance engineering repo**, not as a mirror-first product release and not as a high-confidence adoptable open-source product package.

- Default public positioning: **strong-engineering applied AI mini-system / owner-level candidate**
- Current public message: **the remote repository is already public, while repo-side and external-lane acceptance continue as separate lanes**. Whether it is safe for high-confidence adoption still depends on current-run evidence from the external lane, not on the repo simply being public.
- Public maintenance mode: **limited-maintenance**
- Repo-side completion standard: `docs/reference/done-model.md`
- Current repo-side strict receipt entry: `.runtime-cache/reports/governance/newcomer-result-proof.json`; `governance-audit PASS` only proves that the control plane is standing and does not equal repo-side done on its own
- External-lane status reference: `docs/reference/external-lane-status.md`; `docs/generated/external-lane-snapshot.md` is now only a tracked pointer, and the current verdict must come from `.runtime-cache/reports/**`
- Public-readiness overview: `docs/reference/public-repo-readiness.md`
- Rights and provenance boundary: `docs/reference/public-rights-and-provenance.md`
- Contributor and automation rights model: `docs/reference/contributor-rights-model.md`
- Data and privacy boundary: `docs/reference/public-privacy-and-data-boundary.md`
- Platform and brand boundary: `docs/reference/public-brand-boundary.md`
- Current platform security state: read `.runtime-cache/reports/governance/remote-platform-truth.json`; `private_vulnerability_reporting` may only be described as `enabled|disabled|unverified`
- Current open-source security freshness state: read `.runtime-cache/reports/governance/open-source-audit-freshness.json`; old-commit gitleaks receipts must not be presented as current proof
- Project positioning and intended users: `docs/reference/project-positioning.md`
- Public-safe value proof entry: `docs/generated/public-value-proof.md`
- AI formal-eval minimal system: `docs/reference/ai-evaluation.md`

Default public-facing acceptance commands:

```bash
./bin/governance-audit --mode audit
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Reading rules:

- `./bin/governance-audit --mode audit` is the repo-side control-plane master gate. It is not a standalone repo-side done receipt.
- A fresh PASS receipt from `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` is the decisive vote for repo-side terminal acceptance.
- If you want the current HEAD repo-side newcomer / strict receipt, read `.runtime-cache/reports/governance/newcomer-result-proof.json`.
- If you want the external lane current state, read `.runtime-cache/reports/governance/current-state-summary.md` together with the underlying runtime reports; `ready` does not mean `verified`.
- The repository is currently **publicly reviewable**, but that does not automatically mean **safe for open-source distribution**. Read `docs/reference/public-repo-readiness.md`, `docs/reference/public-rights-and-provenance.md`, and `docs/reference/contributor-rights-model.md` together for the collaboration and rights boundary.
- The git-tracked tree may be publicly reviewable, but that does not mean the maintainer's current working directory can be shared as a complete bundle. Local `.env`, `.runtime-cache/**`, `.agents/Plans/**`, and `.agents/Conversations/**` belong to the private/internal worktree surface and are outside the public-safe narrative.

## Project Purpose

- Turn video content into actionable structured information: fetch, parse, summarize, search, and distribute.
- Provide one consistent entry surface for automation and humans: API for service access, MCP for tool access, and Web for an admin surface.
- Stay local-first and verifiable: commands should be reproducible and tests / gates should stay traceable.

## Stack Overview

- Backend: Python, FastAPI, SQLAlchemy
- Execution: Temporal Worker with `content_type` routing (video 9-step / article 5-step)
- Tool layer: FastMCP
- Frontend: Next.js
- Storage: PostgreSQL (with pgvector for vector retrieval) + SQLite (for state)
- Quality gates: uv, pytest, Playwright, ruff, npm lint/test, git hooks

## 1-Minute Entry

Start with `docs/start-here.md`. It is the only onboarding entrypoint and collects startup commands, boundary wording, and the follow-up doc map.

<!-- docs:generated governance-snapshot start -->
## Governance Snapshot

- **Docs control plane**: `config/docs/*.json` is the source of truth for docs governance, and `docs/generated/*.md` is the render layer.
- **CI trust boundary**: `trusted_internal_pr_only`. Fork and untrusted PRs must not enter the privileged self-hosted path.
- **Strict CI source of truth**: `infra/config/strict_ci_contract.json`.
- **Repo-side done model**: `docs/reference/done-model.md`.
- **Generated references**: `docs/generated/ci-topology.md`, `docs/generated/runner-baseline.md`, `docs/generated/release-evidence.md`, and `docs/generated/external-lane-snapshot.md`.
<!-- docs:generated governance-snapshot end -->

## Quick First Run After Clone (Recommended)

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
```

Those three steps move the repository into a "runnable + verifiable" local-first state.

Notes:

- `./bin/bootstrap-full-stack` now starts with `./bin/workspace-hygiene --apply`, which removes illegal runtime residue such as the root `.venv`, source-tree `apps/web/node_modules`, and `apps/**/__pycache__` before dependency installation and environment preparation continue.
- `bootstrap_full_stack.sh` starts core services (Postgres / Temporal) and the reader stack (Miniflux / Nextflux) by default.
- Except for the first-time case where `.env` does not yet exist, `bootstrap_full_stack.sh` no longer rewrites `.env` persistently. Port conflicts and runtime route decisions are written to `.runtime-cache/run/full-stack/resolved.env` and apply only to the current run.
- `full_stack.sh` manages API / Worker / Web by default. `bin/dev-mcp` remains an interactive stdio entrypoint and should be started in a separate terminal when needed.
- When starting Web, `full_stack.sh` injects the current API port into `NEXT_PUBLIC_API_BASE_URL` automatically so the dev page no longer falls back to `127.0.0.1:9000` under 18000 / 18001 port layouts.
- The local routing source of truth is `API_PORT/WEB_PORT`; `VD_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` are derived destination addresses.
- `full_stack.sh` starts services in `API health -> Web -> Worker` order. Before Worker starts it performs a Temporal preflight against `TEMPORAL_TARGET_HOST` (default `localhost:7233`) and fails fast if Temporal is unreachable.
- `smoke_full_stack.sh` validates the reader stack by default and performs one `AI Feed -> Miniflux` write-back check. Any core or reader failure now fails fast; there is no offline fallback path anymore.
- The reader overlay only fills missing `MINIFLUX_*` / `NEXTFLUX_*` variables. Reader credentials explicitly injected into the current shell always win and are not overridden by the `env/profiles/reader.env` template.
- If you temporarily do not want to check the reader stack: `./bin/smoke-full-stack --require-reader 0`
- `smoke_full_stack.sh` is local integration smoke, not a substitute for `api-real-smoke`; real backend Postgres integration acceptance still requires `./bin/api-real-smoke-local`.
- `./bin/api-real-smoke-local` now tries `127.0.0.1:18080` by default. If that port is occupied and `--api-port` is not explicitly set, the script auto-selects the next free port and records that decision in the logs.
- `./bin/api-real-smoke-local` now temporarily starts a local worker for the cleanup workflow closure probe and automatically cleans it up on exit, so you no longer have to start Worker manually beforehand.
- `./bin/api-real-smoke-local` now checks host IPv4 loopback first. If it reports `failure_kind=host_loopback_ipv4_exhausted`, the issue is with the host's `127.0.0.1` self-connectivity and should be treated as a machine-level problem before chasing business logs.
- When troubleshooting `full_stack.sh` or `api_real_smoke_local.sh`, inspect `.runtime-cache/logs/components/full-stack/*.log` and `.runtime-cache/logs/tests/api-real-smoke-local.log` first instead of guessing whether the problem is application logic or host port drift.
- `UI audit` results are written to `.runtime-cache/evidence/tests/ui-audit-runs/` by default; `autofix` currently returns only a persisted dry-run plan and does not pretend to have written code changes.
- `./bin/smoke-computer-use-local` now uses a strict interpretation by default: if the provider does not support computer use, the command fails outright. Only an explicit `--allow-unsupported-skip=1` allows a skip verdict.
- Self-hosted runner baseline source of truth: `infra/config/self_hosted_runner_baseline.json`; documentation lives in `docs/reference/runner-baseline.md`. The main `ci.yml` no longer owns runner operations; `runner-health.yml` now handles runner health checks.

## Local Acceptance Layers (Must Stay Distinct)

- `sqlite+pysqlite:///:memory:`: default fast-regression path (speed first, allows integration smoke to `xfail` by contract when the environment is not ready).
- `postgresql+psycopg://...`: real Postgres integration-smoke path aligned with CI `api-real-smoke`, used for unambiguous backend acceptance.

Standard strict acceptance (recommended order):

```bash
./bin/full-stack up
./bin/api-real-smoke-local
./bin/smoke-full-stack
./bin/quality-gate --mode pre-push --strict-full-run 1 --profile ci --profile live-smoke --ci-dedupe 0
```

Repo-side / external dual completion signals:

- repo-side canonical path: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- external-lane path: `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- explanation doc: `docs/reference/done-model.md`
- external-lane status page: `docs/reference/external-lane-status.md`

Governance control-plane entrypoints:

```bash
./bin/governance-audit --mode pre-commit
./bin/governance-audit --mode pre-push
./bin/governance-audit --mode audit
```

Daily local fast-regression path (speed first):

```bash
./bin/quality-gate --mode pre-push --profile ci --profile live-smoke --ci-dedupe 0
```

## IaC And The Standard Environment (Required For AI)

Current reproducible-environment surfaces in this repository:

- Docker Compose (infrastructure source of truth): `infra/compose/core-services.compose.yml` (core-service images have been converged to digest-pinned service images and now align directly with the strict contract), `infra/compose/miniflux-nextflux.compose.yml`
- DevContainer (AI / automation standard execution environment): `.devcontainer/devcontainer.json`. Floating DevContainer feature dependencies have been removed; `post-create.sh` directly checks that `uv/node/chromium` from the strict contract are available instead of hiding drift behind best-effort browser installation.
- Strict CI standard-image source of truth: `infra/config/strict_ci_contract.json`. `bin/strict-ci` and `./bin/run-in-standard-env` now accept only digest-pinned standard images and no longer silently fall back to old local tag-based images.
- `build-ci-standard-image.yml` now explicitly prepares Docker Buildx on the hosted runner before calling `scripts/ci/build_standard_image.sh` for multi-arch standard-image builds, preventing image-workflow failures caused by missing Buildx setup.
- The standard-image build chain now retries the NodeSource signing key and writes it to a temporary file before `gpg --dearmor`, which avoids ARM64/QEMU Buildx paths feeding a transient empty response directly into `gpg`.
- Standard-image supply-chain hardening: `build-ci-standard-image.yml` now emits an image SBOM artifact and creates GitHub attestations for both the image and the SBOM.
- Self-hosted runner pre-clean now handles both directories and single-file residue under `/tmp/video-digestor-*`, and restores user write permission before deletion, preventing stale `.db/.db-shm/.db-wal` files from blocking the runner-hygiene phase in `build-ci-standard-image.yml`.
- Release-evidence attestation: a new `release-evidence-attest.yml` package now attests the manifest / checksums / rollback evidence under `artifacts/releases/<tag>/`.
- Generated governance references:
  - CI main chain and aggregate gate: `docs/generated/ci-topology.md`
  - self-hosted runner baseline: `docs/generated/runner-baseline.md`
  - release-evidence canonical rules: `docs/generated/release-evidence.md`

Enter the standard environment before running local integration or strict acceptance. The only authoritative strict-acceptance entrypoint is the repository standard image, not ad-hoc host commands:

```bash
# 1) In VS Code: Dev Containers: Reopen in Container
# or with the devcontainer CLI:
devcontainer up --workspace-folder .

# 2) Inside the container (dev / integration)
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack

# 3) Inside the standard image (CI-equivalent strict acceptance)
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Operational risks:

- Existing `scripts/deploy/core_services.sh` and `./bin/reader-stack` are already bound to those compose files. No script change is needed.
- Risk 1: DevContainer depends on host Docker through `/var/run/docker.sock`. If host Docker is not running, compose cannot be started from inside the container.
- Risk 1.1: The strict-acceptance entrypoint `bin/strict-ci` also depends on host Docker and on being able to pull the contract-declared standard image. If Docker is not running or the digest image cannot be fetched, the script now fails fast instead of falling back to an old local image.
- Risk 1.2: Local execution of the pinned-image strict chain now requires usable GHCR pull identity. Current priority is: explicit `GHCR_WRITE_USERNAME/GHCR_WRITE_TOKEN` -> local-debug `GHCR_USERNAME/GHCR_TOKEN` -> current `gh auth` login state. If all three are missing, the command fails fast. Hosted `build-ci-standard-image.yml` now probes `github.actor + GITHUB_TOKEN` first, may fall back to explicit `GHCR_WRITE_*` credentials, and may continue in a `fallback-unverified` mode when the explicit writer path still cannot prove blob upload during preflight but the hosted build/push run is needed for decisive evidence.
- Risk 1.4: The external lane still depends on GitHub Actions workflow state and package permissions. If `build-ci-standard-image.yml` is disabled, or the current GitHub token lacks `read:packages/write:packages`, the external image path is platform-blocked and cannot be rescued by repo-side gates.
- Risk 1.3: DevContainer now mounts the workspace at `/workspace` and reuses cache paths from the strict contract. Any local script still assuming the old `/workspaces/...` path must be updated separately.
- `--debug-build` is for local diagnosis of standard-environment problems only and does not count as release or pre-push completion evidence.
- Risk 2: live smoke depends on real external API keys such as `GEMINI_API_KEY`. The standard environment guarantees execution consistency, not external resource availability.
- Risk 3: Do not mix bare-host and container paths within the same acceptance run. Residual ports, databases, and caches will break CI equivalence.

If you have already left illegal runtime residue in the workspace, you can manually run:

```bash
./bin/workspace-hygiene --apply
```

## Processing Flow (Unified Contract)

`ProcessJobWorkflow` consists of three stages:

1. `mark_running`
2. `run_pipeline_activity` (routed by `content_type`)
3. `mark_succeeded` or `mark_failed`

Video pipeline (`videos.content_type='video'`):

1. `fetch_metadata`
2. `download_media`
3. `collect_subtitles`
4. `collect_comments`
5. `extract_frames`
6. `llm_outline`
7. `llm_digest`
8. `build_embeddings`
9. `write_artifacts`

Article pipeline (`videos.content_type='article'`):

1. `fetch_article_content`
2. `llm_outline`
3. `llm_digest`
4. `build_embeddings`
5. `write_artifacts`

For state-machine details, see `docs/state-machine.md`.

`GET /api/v1/feed/digests` currently accepts `source/category/sub/limit/cursor/since`, and each response item now returns `content_type` so Web can distinguish video and article entries.

## Model Strategy (Gemini-only)

- Provider is fixed to `gemini`; `llm_outline` and `llm_digest` do not support other providers.
- Structured output is fixed to JSON: `response_mime_type=application/json` plus schema validation with strict `extra=forbid`.
- Function calling:
  - `llm_outline` / `llm_digest` enable tools for evidence citation and frame selection.
  - The translation fallback path disables function calling.
- Computer Use safety gate for function-call rounds:
  - Only `select_supporting_frames` and `build_evidence_citations` are allowed; non-whitelisted calls are marked `blocked`.
  - The `computer_use` entry is controlled by `GEMINI_COMPUTER_USE_*` and `overrides.llm*.enable_computer_use`; when `GEMINI_COMPUTER_USE_ENABLED=false`, request-level overrides must not force it on.
  - When `enable_computer_use=true` and no handler is explicitly provided, the pipeline injects `build_default_computer_use_handler` by default.
  - `computer_use_require_confirmation` defaults to `true`; even after a future handler integration, unconfirmed requests still return `computer_use_confirmation_required`.
  - Maximum function-call rounds are controlled by `max_function_call_rounds` (default `2`, overridable by `overrides.llm.max_function_call_rounds`, `overrides.llm_outline.max_function_call_rounds`, and `overrides.llm_digest.max_function_call_rounds`).
  - When the limit is reached, the round ends with `termination_reason=max_function_call_rounds_reached`.
- Thinking strategy:
  - Controlled by `GEMINI_THINKING_LEVEL` by default.
  - Complex tasks require `include_thoughts=true`; missing thought signatures count as a hard failure.
  - Request-level overrides may set `overrides.llm.thinking_level`.
- Context cache:
  - Controlled by `GEMINI_CONTEXT_CACHE_ENABLED/TTL_SECONDS/MIN_CHARS`.
- Media-resolution inputs:
  - Supports `low|medium|high|ultra_high`.
  - `PIPELINE_LLM_INPUT_MODE` (`auto|text|video_text|frames_text`)
  - `PIPELINE_MAX_FRAMES` and `overrides.frames.max_frames`
  - Runtime `llm_media_input` (`video_available`, `frame_count`)

### Embedding / Retrieval Entry

- Embedding configuration entry: `GEMINI_EMBEDDING_MODEL`
- Retrieval entry at the current stage: `artifacts_index` from `GET /api/v1/jobs/{job_id}` (also exposed via MCP `vd.jobs.get`)

### Thought Metadata / Signatures Visibility

- API: `steps[].result.llm_meta.thinking` from `GET /api/v1/jobs/{job_id}` includes:
  - `thought_count`
  - `thought_signatures`
  - `thought_signature_digest`
  - `usage` (token stats)
- MCP: `vd.jobs.get` preserves the same structure under `steps[].result`.
- Normalized field: `steps[].thought_metadata` is normalized into a stable structure from `result.thought_metadata|thinking_metadata|thoughts_metadata|thoughts|llm_meta.thinking`; when absent, it returns an empty structure rather than `null`.

## Local Run (Standard 6 Steps)

### 1) Install dependencies

Prerequisites: Python 3.11+, `uv`, PostgreSQL 16, Temporal dev server.

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.cache/video-digestor/project-venv" uv sync --frozen --extra dev --extra e2e
./bin/prepare-web-runtime
```

Additional note: `./bin/prepare-web-runtime` is the stable wrapper layer; the real target is `scripts/ci/prepare_web_runtime.sh`. If the entrypoint reports `Permission denied`, check whether the helper still has execute permission before suspecting the Web runtime workspace logic.

### 2) Start base services (Host Fallback, emergency use only)

```bash
brew services start postgresql@16
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3) Initialize environment variables

```bash
cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
set -a; source .env; set +a
```

Notes: the standard initialization path is `.env.example -> .env`; `./bin/init-env-example` is only for generating helper templates on demand. `./bin/dev-*` automatically loads the repository-root `.env`. Reader-specific command paths, such as `./bin/run-ai-feed-sync` and the reader checks in `./bin/smoke-full-stack`, additionally read `env/profiles/reader.env` to fill missing reader variables, but they do not override values already injected into the current shell. Prefer explicit environment-variable injection in the current shell for extra configuration.
Additional note: `.env.example` has been reduced to a minimum startup template; for the full script parameter surface, see `docs/reference/env-script-overrides.md`.

### 4) Initialize databases

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

Note: `20260222_000010_phase4_status_contract.sql` already includes defensive normalization for historical dirty states, so old databases do not fail migrations just because legacy status values still exist.

### 5) Start application processes

Start these in three separate terminals:

```bash
./bin/dev-api
./bin/dev-worker
./bin/dev-mcp
```

Script entry arguments (Batch C):

- `./bin/dev-api --app apps.api.app.main:app --no-reload`
- `./bin/dev-worker --worker-dir "$PWD/apps/worker" --entry worker.main --command run-worker --no-show-hints`
- `./bin/dev-mcp --entry apps.mcp.server --mcp-dir "$PWD/apps/mcp"`
- optional helper template command: `./bin/init-env-example --output "$PWD/.env.generated.example" --force`

Additional note:

- `./bin/dev-api` now delegates to the internal launcher and uses `uv run python -m uvicorn ...` when `uv` is available instead of relying on a `uvicorn` console entry. This is more stable in self-hosted runners and minimal Python environments.

### 6) Minimum acceptance

```bash
curl -sS http://127.0.0.1:9000/healthz
curl -sS -X POST http://127.0.0.1:9000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 20}'
```

Stable fields on `GET /api/v1/jobs/{job_id}` and `vd.jobs.get`:

- `step_summary`
- `steps`
- `degradations`
- `pipeline_final_status`
- `artifacts_index`
- `mode`

## Test Entry Points

```bash
python3 scripts/governance/check_test_assertions.py

./bin/quality-gate

./bin/install-git-hooks

./bin/python-tests

uv run --with playwright python -m playwright install chromium
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q

# critical frontend control flows (feed/dashboard/subscriptions)
uv run --with pytest --with playwright pytest \
  apps/web/tests/e2e/test_feed.py \
  apps/web/tests/e2e/test_dashboard.py \
  apps/web/tests/e2e/test_subscriptions.py \
  -q -rA --web-e2e-browser chromium --web-e2e-use-mock-api=1
```

Note: `scripts/governance/check_test_assertions.py` forbids `toBeDefined()` by default. Only exceptional cases may opt out with an explicit `allow-low-value-assertion: toBeDefined` comment.

Updated testing and gate semantics (2026-02):

- Remote CI cost governance: before triggering or rerunning GitHub Actions, you must first pass `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0` locally.
- For a local final acceptance run with the same semantics as CI, use `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`; Host Fallback and sqlite fast-regression runs do not count as CI-equivalent evidence.
- `strict-full-run=1` forces `ci-dedupe` off and forbids `skip-mutation`, ensuring the local run is the full gate rather than a trimmed version.
- After a remote failure, reproduce and fix locally before triggering the next remote run. Consecutive blind reruns are forbidden.
- CI preflight is now split into `preflight-fast` + `preflight-heavy`, so most jobs can start from the fast gate while the aggregate gate still requires both.
- `quality-gate-pre-push` now runs on all CI events (PR / push / schedule) with `--changed-*` passthrough as the heaviest remote gate; mutation runs in a separate `mutation-testing` job and cross-validates lint / unit / coverage in parallel.
- `web-test-build` now runs by default on PR / push / schedule as long as `preflight-fast` and `changes` succeed, preventing change-detection mistakes from skipping critical Web gates.
- Coverage bar upgrade: total repository coverage has a hard gate of `>=95%`, and core modules remain at `>=95%`.
- Web coverage no longer checks only lines: `lines/functions/branches` must all meet `global >=95%` and `core >=95%`.
- Web interaction coverage has been split into a more honest three-part model: `combined=1.0`, `e2e>=0.6`, and `unit>=0.93`; E2E and unit are no longer blended into a fake 100%.
- When Web or dependency changes are hit, CI also runs a blocking `Gemini UI/UX audit`; it passes only with `status=passed`, `reason_code=ok`, full batch success, and real `model_attempts`.
- Local `pre-push` now adds hard gates for `api cors preflight smoke (OPTIONS DELETE)` and `contract diff local gate (base vs head)` to catch cross-surface regressions before remote CI.
- Local `pre-push` is now further aligned with remote `preflight-fast` + `web-test-build`: `contract surface gate`, `docs env canonical guard`, `provider residual guard`, `worker line limits`, `schema parity`, `web design token guard`, `web build`, and `web button coverage`.
- Local acceptance remains layered: the sqlite path is for default fast regression; real Postgres integration acceptance must still run `./bin/api-real-smoke-local` to match CI `api-real-smoke`.
- Web E2E is now lighter by default: trace defaults to `off`, video defaults to `retain-on-failure`, and heavy artifacts upload only on failure.
- Test-layer responsibility is explicit: API owns field-level contract assertions, Web E2E focuses on user journeys, and MCP focuses on tool semantics and routing behavior.

## Git Hooks And pre-commit Coordination (Initialization And Maintenance)

Current default execution chain:

- `.githooks/pre-commit`, `.githooks/pre-push`, and `.githooks/commit-msg` are the Git-lifecycle entrypoints.
- Those hooks run the mandatory gates via `./bin/quality-gate`, `./bin/strict-ci`, and `commitlint`.
- `.pre-commit-config.yaml` defines a reusable set of checks and is not called directly by `.githooks` by default.

First-time initialization (recommended):

```bash
./bin/install-git-hooks
```

Optional: if you want to activate the pre-commit framework hook files directly under the current `core.hooksPath`:

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Big Bang full cleanup (recommended before large changes):

```bash
pre-commit run --all-files
```

detect-secrets baseline (optional supplement; the mandatory secrets gate is still gitleaks):

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

Monthly maintenance (recommended monthly):

```bash
pre-commit autoupdate
pre-commit run --all-files
```

Additional testing semantics aligned with CI:

- `web-e2e` uses Playwright + the real API on the CI main path. It is not mock API and not a "real external website smoke" test.
- The main `web-e2e` path now includes `subscriptions`; it is no longer covered only in the nightly flaky subset.
- `external-playwright-smoke` is a separate job that really visits an external site in CI (currently `https://example.com`) to validate browser outbound access.
  Default parameters: `browser=chromium`, `expect_text="Example Domain"`, `timeout_ms=45000`, `retries=2`.
- `pr-llm-real-smoke` runs conditionally only on PRs that satisfy `pull_request && same-repo-pr && backend_changed`; otherwise it may be `skipped` without blocking the aggregate gate.
- `Gemini UI/UX audit` is a blocking CI main-path gate: it passes only when `status=passed`, `reason_code=ok`, `successful_batches==batch_count`, and `model_attempts>0`, and it uploads `.runtime-cache/reports/ui-audit/*` artifacts so "green without a real audit" cannot happen.
- `GEMINI_API_KEY` is a runtime-required secret for that job and is not part of the workflow `if` expression; once the job is triggered, missing it causes failure.
- `external-playwright-smoke` only runs on `push` to `main` or nightly `schedule`; on PRs it is usually `skipped`, and the aggregate gate accepts `success|skipped`.
- `web-e2e` injects the real API by default through `NEXT_PUBLIC_API_BASE_URL`, supplied by `--web-e2e-api-base-url` (default `http://127.0.0.1:18080`); it switches to mock API only when `--web-e2e-use-mock-api=1` or `WEB_E2E_USE_MOCK_API=1` is explicitly set.
- To reuse an external Web instance, run: `uv run --with pytest --with playwright pytest apps/web/tests/e2e -q --web-e2e-base-url 'http://127.0.0.1:3000'`.
- PRs do not require `live-smoke`; `main` pushes and nightly schedules do require `live-smoke=success`.
- `live-smoke` is the real LLM/provider chain; CI requires `GEMINI_API_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `YOUTUBE_API_KEY`, and the workflow brings up local API / Worker while targeting `http://127.0.0.1:18080`.
- `./bin/smoke-full-stack` is local integration smoke and does not equal the mandatory CI `live-smoke` gate.
- `./bin/smoke-full-stack` is also not a replacement for `api-real-smoke`; real backend Postgres integration acceptance still requires `./bin/api-real-smoke-local`.
- See "Reproduce the two real Smoke classes locally (same semantics as CI)" in `docs/testing.md` for the local reproduction commands.

## API Routes And Admin Endpoint Contract

System and business routes (FastAPI):

- `GET /healthz`
- `GET /readyz`
- `GET /metrics`
- `GET /api/v1/subscriptions`
- `POST /api/v1/subscriptions`
- `POST /api/v1/subscriptions/batch-update-category`
- `DELETE /api/v1/subscriptions/{id}`
- `GET /api/v1/feed/digests`
- `POST /api/v1/ingest/poll`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/videos`
- `POST /api/v1/videos/process`
- `GET /api/v1/notifications/config`
- `PUT /api/v1/notifications/config`
- `POST /api/v1/notifications/test`
- `POST /api/v1/notifications/category/send`
- `POST /api/v1/reports/daily/send`
- `GET /api/v1/artifacts/markdown`
- `GET /api/v1/artifacts/assets`
- `GET /api/v1/health/providers`
- `POST /api/v1/workflows/run`
- `POST /api/v1/retrieval/search`
- `POST /api/v1/computer-use/run`
- `POST /api/v1/ui-audit/run`
- `GET /api/v1/ui-audit/{run_id}`
- `GET /api/v1/ui-audit/{run_id}/findings`
- `GET /api/v1/ui-audit/{run_id}/artifacts`
- `GET /api/v1/ui-audit/{run_id}/artifact`
- `POST /api/v1/ui-audit/{run_id}/autofix`

Admin-endpoint authentication (controlled by `VD_API_KEY` + `VD_ALLOW_UNAUTH_WRITE`):

- Safe default: even when `VD_API_KEY` is empty or unset, write operations still require a token.
- Token-free writes are allowed only in these two testing scenarios, and only when `VD_API_KEY` is empty: `PYTEST_CURRENT_TEST` exists, or GitHub Actions CI simultaneously satisfies `VD_ALLOW_UNAUTH_WRITE=true`, `CI=true`, `GITHUB_ACTIONS=true`, and `VD_CI_ALLOW_UNAUTH_WRITE=true`.
- The following endpoints must carry a token or they return `401/403`:
  - `POST /api/v1/subscriptions`
  - `POST /api/v1/subscriptions/batch-update-category`
  - `DELETE /api/v1/subscriptions/{id}`
  - `POST /api/v1/ingest/poll`
  - `POST /api/v1/videos/process`
  - `PUT /api/v1/notifications/config`
  - `POST /api/v1/notifications/test`
  - `POST /api/v1/notifications/category/send`
  - `POST /api/v1/reports/daily/send`
  - `POST /api/v1/workflows/run`
  - `POST /api/v1/computer-use/run`
  - `POST /api/v1/ui-audit/run`
  - `POST /api/v1/ui-audit/{run_id}/autofix`
- Supported transport styles:
  - `Authorization: Bearer <VD_API_KEY>`
  - `X-API-Key: <VD_API_KEY>`

## P1 Added Capabilities (2026-02-23)

- Subscriptions now support categories and tags:
  - fields: `category` (`tech|creator|macro|ops|misc`), `tags` (string array)
  - API:
    - `GET /api/v1/subscriptions?category=tech`
    - `POST /api/v1/subscriptions` supports `category/tags`
- Notifications now support category rules and category-based sending:
  - config field: `category_rules` (JSON)
  - new endpoint: `POST /api/v1/notifications/category/send`

## P2 Added Capabilities (2026-02-23)

- Source adapters for subscriptions:
  - new fields: `adapter_type` (`rsshub_route|rss_generic`), `source_url`
  - behavior:
    - `adapter_type=rsshub_route`: uses `rsshub_route`
    - `adapter_type=rss_generic`: fetches RSS directly from `source_url`
  - goal: move from platform-specific hardcoded inputs toward the `adapter + source_url` model

## Optional: Reader Stack (Miniflux + Nextflux)

If you want an "AI processing pipeline + polished reader UI + multi-device access" stack, the repository already includes an optional deployment lane:

- Compose: `infra/compose/miniflux-nextflux.compose.yml`
- Script: `./bin/reader-stack`
- GCE guide: `docs/deploy/miniflux-nextflux-gce.md`

Quick start:

```bash
# Edit env/profiles/reader.env and set at least MINIFLUX_DB_PASSWORD / MINIFLUX_ADMIN_PASSWORD / MINIFLUX_BASE_URL
./bin/reader-stack up --env-file env/profiles/reader.env
./bin/reader-stack status --env-file env/profiles/reader.env
```

## Optional: Real-Time Stable Push Workflows

The repository includes `./bin/start-ops-workflows` to start or ensure these long-running workflows in one shot:

- `daily_digest`
- `notification_retry`
- `provider_canary`
- `cleanup_workspace`

Basic usage:

```bash
./bin/start-ops-workflows
```

Common arguments:

```bash
./bin/start-ops-workflows \
  --daily-local-hour 9 \
  --daily-timezone Asia/Shanghai \
  --notification-interval-minutes 5 \
  --notification-retry-batch-limit 100 \
  --canary-interval-hours 1 \
  --canary-timeout-seconds 8 \
  --cleanup-interval-hours 6 \
  --cleanup-older-than-hours 24
```

For the full parameter reference, see `docs/runbook-local.md`.

## Pre-Release Inspection (Release Readiness)

```bash
# 1) Generate pre-release evidence (tag / changelog / perf / rum / rollback / canary)
python3 scripts/release/generate_release_prechecks.py

# 2) Merge into the release-readiness report
python3 scripts/release/build_readiness_report.py \
  --kpi-json .runtime-cache/reports/release-readiness/ci-kpi-summary.json \
  --check-json .runtime-cache/reports/release-readiness/prechecks.json \
  --json-out .runtime-cache/reports/release-readiness/release-readiness.json \
  --md-out .runtime-cache/reports/release-readiness/release-readiness.md

# 3) Capture the N-1 rollback artifact manifest (run before release)
scripts/release/capture_release_manifest.sh <release-tag>

# 4) DB rollback-chain gate (missing down / invalid down / uncleared blockers all block the release)
python3 scripts/release/verify_db_rollback_readiness.py \
  --release-tag <release-tag> \
  --output artifacts/releases/<release-tag>/rollback/db-rollback-readiness.json
```

## Documentation Map

- 1-minute entry: `docs/start-here.md`
- full docs index: `docs/index.md`
- local operations: `docs/runbook-local.md`
- state machine: `docs/state-machine.md`
- environment governance: `ENVIRONMENT.md`
- environment layering and precedence: `ENVIRONMENT.md` (`Core/Profile Overlay Architecture`)
- legacy environment migration guide: `ENVIRONMENT.md` (`Migration Guide: Legacy .env.example -> Core/Profile Overlay`)
- reference docs: `docs/reference/logging.md`, `docs/reference/cache.md`, `docs/reference/dependency-governance.md`
- MCP routing: `docs/reference/mcp-tool-routing.md` (`13 tools`, action routing, composition examples)


<!-- doc-sync: api/worker reliability + auth guard update (2026-03-03) -->


<!-- doc-sync: mcp/web contract and schema alignment (2026-03-03) -->


<!-- doc-sync: mcp api-client redaction fixture adjustment (2026-03-03) -->


<!-- doc-sync: integration smoke uses xfail instead of skip when env unmet (2026-03-03) -->


<!-- doc-sync: ci failure fixes (integration smoke auth + ci_autofix timezone compatibility) (2026-03-03) -->
