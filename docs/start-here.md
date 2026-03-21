# Start Here (1-Minute Onboarding)

This is the repository's only onboarding entrypoint. Copy the commands first, then lazy-load deeper docs only when you actually need them.

## AI Navigation Index (Lazy-Load)

1. Root governance (read first)

- `AGENTS.md`
- `CLAUDE.md`

2. Load modules on demand (only when you are touching that module)

- API: `apps/api/AGENTS.md`, `apps/api/CLAUDE.md`
- Worker: `apps/worker/AGENTS.md`, `apps/worker/CLAUDE.md`
- MCP: `apps/mcp/AGENTS.md`, `apps/mcp/CLAUDE.md`
- Web: `apps/web/AGENTS.md`, `apps/web/CLAUDE.md`

3. Runtime and contracts (keep reading as the problem gets deeper)

- `docs/runbook-local.md`
- `docs/state-machine.md`
- `docs/testing.md`
- `ENVIRONMENT.md`
- `docs/reference/runner-baseline.md`
- `docs/reference/root-governance.md`
- `docs/reference/architecture-governance.md`
- `docs/reference/runtime-cache-retention.md`
- `docs/reference/evidence-model.md`
- `docs/reference/upstream-governance.md`

## The 5 Things You Need To Know First

1. Workflow contract: `ProcessJobWorkflow = 3 stages + a content_type-routed pipeline` (video 9-step / article 5-step; see `docs/state-machine.md`).
2. Environment layering: the repo uses a `core + profile overlay` model. `.env` is the core layer, and `env/profiles/reader.env` is the reader profile template. Strict acceptance only recognizes the standard environment and standard-image entrypoints. The reader overlay only fills missing values and must not override reader credentials already injected into the current process.
3. Secret policy: secrets may only come from `.env` or the process environment. Shell login config must not be treated as a runtime secret source.
4. Use `python3` consistently for Python commands.
5. AI and automation must run in the standard environment: prefer `.devcontainer/devcontainer.json`, and use `infra/compose/*.compose.yml` for infrastructure.

<!-- docs:generated governance-snapshot start -->
## Generated Governance Snapshot

- High-drift facts have been pulled into `docs/generated/*.md`; entry docs now keep only the onboarding-critical surface.
- Self-hosted CI only accepts **trusted internal PRs**; fork PRs are blocked at the trust-boundary gate.
- Repo-side strict entrypoint: `./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`.
- External lane entrypoint: `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`.
- External lane truth entry: `docs/generated/external-lane-snapshot.md` (tracked pointer) plus `.runtime-cache/reports/**` (current verdict).
- Contract sources now live under `contracts/`, and long-lived tracked artifacts now live under `artifacts/`.
<!-- docs:generated governance-snapshot end -->

## Prepare Environment Files (Required)

```bash
cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
```

Notes:

- `.env.example` now keeps only the minimum startup keys plus a small set of common overrides, which is enough for one local boot in the default path.
- The standard initialization path is `.env.example -> .env`; `./bin/init-env-example` is only a helper for generating extra templates, not the default entrypoint.
- The full script argument surface is documented in `docs/reference/env-script-overrides.md` for opt-in overrides. You do not need to write every possible variable into `.env`.

## Public / Internal Boundary

- public-ready/source-first entry: `README.md`, `docs/start-here.md`
- deeper operator runbook: `docs/runbook-local.md`
- repo-side / external dual-completion model: `docs/reference/done-model.md`
- repo-side current receipt: `.runtime-cache/reports/governance/newcomer-result-proof.json`
- public-readiness boundary: `docs/reference/public-repo-readiness.md`
- local-private worktree surface: `.env`, `.runtime-cache/**`, `.agents/Plans/**`, `.agents/Conversations/**`
- The current documentation stance is **public source-first repo + dual completion lanes**, not an adoption-grade open-source distribution package and not a hosted product landing page.

If this is your first contact with the repository, stop at the public-ready/source-first entrypoints first. Do not treat `docs/runbook-local.md` as the public onboarding page on day one.
If you need to share a folder zip or screenshots externally, remove the local-private worktree surface first. The tracked public tree and the maintainer's working directory are not the same public boundary.

## One-Command Validation (Shortest Path)

```bash
./bin/validate-profile --profile local
```

If that command reports forbidden workspace runtime residue, run:

```bash
./bin/workspace-hygiene --apply
./bin/validate-profile --profile local
```

Interpretation:

- A `validate-profile` pass only means newcomer preflight has been captured.
- A `governance-audit` pass only means the repo-side control plane is standing.
- Only when a fresh strict receipt also exists is the repo-side terminal receipt actually closed.

## Initialize Quality Gates (Recommended After First Clone)

```bash
./bin/install-git-hooks
```

Optional: if you also want the `pre-commit` framework itself attached directly to the Git lifecycle, in addition to the repository-default `.githooks`, run:

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

Notes:

- The current repository-default enforced chain is:
  - `.githooks/pre-commit -> ./bin/quality-gate --mode pre-commit --profile local`
  - `.githooks/pre-push -> ./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0`
- `.pre-commit-config.yaml` defines a reusable check set that is useful for manual all-files cleanup and dependency refreshes.
- If you run `pre-commit install`, it writes hook files under the current `core.hooksPath`, so confirm team expectations first.

## Big Bang Cleanup (Optional)

```bash
pre-commit run --all-files
```

Use this before large refactors or when cleaning up a long-lived branch so format, spelling, and basic static issues are cleared in one pass.

## detect-secrets Baseline (Optional, Parallel To Current Mandatory Gates)

The mandatory secrets gate in this repository is still `gitleaks + quality_gate`. `detect-secrets` is not a default hard requirement. If you want an extra baseline workflow, run:

```bash
uv run --with detect-secrets detect-secrets scan > .secrets.baseline
uv run --with detect-secrets detect-secrets audit .secrets.baseline
uv run --with detect-secrets detect-secrets scan --baseline .secrets.baseline > .secrets.baseline
```

What those three steps mean:

- initialize: `scan > .secrets.baseline`
- review: `audit .secrets.baseline` to mark real risk vs false positives
- refresh: `scan --baseline ... > .secrets.baseline` after code changes

## Monthly pre-commit Maintenance (Optional)

```bash
pre-commit autoupdate
pre-commit run --all-files
```

Suggested cadence: once per month. After updating, run one full pass before you commit.

Optional troubleshooting command:

```bash
./bin/compose-env --profile local --write .runtime-cache/tmp/.env.resolved
```

Migration rule:

- `.env`: keep core/runtime settings and provider secrets here.
- `env/profiles/reader.env`: keep only Miniflux/Nextflux-specific variables here.

## Standard Environment Entry (Required For AI)

```bash
# VS Code: Dev Containers: Reopen in Container
# CLI:
devcontainer up --workspace-folder .
```

The standard environment is a hard prerequisite. Results produced before entering it do not count as CI-equivalent evidence.

Additional DevContainer startup topology notes (2026-03):

- `.devcontainer/post-create.sh` no longer uses `curl|sh`; it now runs `python3 -m pip install --user --upgrade "uv>=0.10,<1.0"` and directly checks whether Chromium from the strict contract can launch. On failure it reports drift immediately instead of hiding it behind `playwright install ... || true`.
- Concurrent Web E2E runs may isolate the Next.js `distDir` with `WEB_E2E_NEXT_DIST_DIR` to avoid `.next/dev/lock` conflicts. Normal development usually does not need this.
- `infra/config/strict_ci_contract.json` is now the source of truth for the standard image. `bin/strict-ci` and `./bin/run-in-standard-env` only accept digest-pinned standard images and fail immediately if the pull cannot be completed.
- `build-ci-standard-image.yml` now prepares Docker Buildx explicitly on the hosted runner before calling `scripts/ci/build_standard_image.sh`, so the image workflow no longer fails just because Buildx was never set up.
- The standard-image build chain now retries the NodeSource signing key and writes it to a temporary file before `gpg --dearmor`; this reduces transient ARM64/QEMU failures caused by empty key responses after HTTP/2 interruptions.
- Key correctness gates (`preflight-heavy`, `db-migration-smoke`, `dependency-vuln-scan`, `web-e2e-perceived`, and the hosted/fallback backend and frontend lint jobs) now run inside the standard image just like `python-tests`, `api-real-smoke`, and `web-e2e`. That means host Docker availability is now part of CI-equivalent local acceptance.
- The self-hosted runner baseline contract has been split into `infra/config/self_hosted_runner_baseline.json`. The main `ci.yml` no longer prewarms or starts runners; `runner-health.yml` owns that concern.
- Before entering `build-ci-standard-image.yml`, self-hosted runners now call `scripts/governance/runner_workspace_maintenance.sh` to clear stale `.runtime-cache`, `mutants/`, and `/tmp/video-digestor-*` directory or single-file residue, preventing old `.db` / `.db-shm` / `.db-wal` leftovers from blocking runner hygiene.
- DevContainer now mounts the workspace at `/workspace` and verifies `uv`, `node`, and cache paths against the strict contract in `post-create.sh`.
- The Web dependency tree now lives under `.runtime-cache/tmp/web-runtime/workspace/apps/web`; `apps/web/node_modules` is no longer a legitimate long-lived source-tree state.
- Generated CI/release reference pages:
  - `docs/generated/ci-topology.md`
  - `docs/generated/runner-baseline.md`
  - `docs/generated/release-evidence.md`

## 6-Step Startup (Host Fallback, For Troubleshooting Only)

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.cache/video-digestor/project-venv" uv sync --frozen --extra dev --extra e2e
./bin/prepare-web-runtime

brew services start postgresql@16
temporal server start-dev --ip 127.0.0.1 --port 7233

cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
set -a; source .env; set +a

createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql

./bin/dev-api
./bin/dev-worker
./bin/dev-mcp

curl -sS http://127.0.0.1:9000/healthz
curl -sS -X POST http://127.0.0.1:9000/api/v1/ingest/poll -H 'Content-Type: application/json' -d '{"max_new_videos": 20}'
```

Additional note: `./bin/prepare-web-runtime` is a wrapper. The real target is `scripts/ci/prepare_web_runtime.sh`. If the wrapper reports `Permission denied`, check whether the helper still has its execute bit before assuming the Web runtime workspace logic is broken.

## One-Command Path (Recommended)

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
```

Default behavior:

- `./bin/bootstrap-full-stack` starts with `./bin/workspace-hygiene --apply` and removes illegal runtime residue such as the root `.venv`, source-tree `apps/web/node_modules`, and `apps/**/__pycache__`.
- `./bin/bootstrap-full-stack` brings up core services plus Miniflux and Nextflux.
- `./bin/bootstrap-full-stack` copies `.env` only on the first run when it is missing; after that it no longer rewrites `.env` persistently. Port conflict resolution and runtime routing decisions are written to `.runtime-cache/run/full-stack/resolved.env` for the current run only.
- `core-services.compose.yml` now uses digest-pinned service images for Postgres and Temporal and prefers the `STRICT_CI_SERVICE_IMAGE_*` values exported from the strict contract. Ports and the Postgres `DB/User` still converge on the fixed defaults (`7233` / `video_analysis` / `postgres`).
- `miniflux-nextflux.compose.yml` converges Miniflux port and `DB/User/DB_NAME` onto fixed defaults (`8080` / `miniflux` / `miniflux`).
- Local routing truth comes from `API_PORT/WEB_PORT`; `VD_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` are derived target addresses.
- `./bin/full-stack up` starts in `API health -> Web -> Worker` order. Before Worker starts, it performs a Temporal preflight against `TEMPORAL_TARGET_HOST` (default `localhost:7233`) and fails fast if Temporal is unreachable.
- `bin/dev-mcp` is an interactive stdio entrypoint. It is not managed as a background daemon by `full_stack.sh`; open a separate terminal when you need local MCP debugging.
- `bin/dev-api` now uses `uv run python -m uvicorn ...` when `uv` is present, which avoids failures in environments that do not expose a `uvicorn` console entry.
- `./bin/smoke-full-stack` performs local integration smoke and includes reader-stack checks. Any core or reader failure now fails fast; the old offline fallback path is gone.
- `./bin/smoke-full-stack` is not a substitute for `api-real-smoke`; real backend Postgres integration acceptance still requires `./bin/api-real-smoke-local`.
- `./bin/api-real-smoke-local` now performs a host IPv4 loopback preflight first. If it hits `failure_kind=host_loopback_ipv4_exhausted` (commonly when local 127.0.0.1 ephemeral ports are saturated by MCP/Codex traffic), it fails fast immediately instead of booting API/Worker/Temporal and only failing later.
- For local script troubleshooting, check `.runtime-cache/logs/components/full-stack/*.log`, `.runtime-cache/run/full-stack/resolved.env`, and `.runtime-cache/logs/tests/api-real-smoke-local.log` first so you can separate routing drift from business failures.
- Logs for `pr-llm-real-smoke`, `live-smoke`, and `web-e2e` are consolidated under `.runtime-cache/logs/tests/`; diagnostics and JUnit outputs live under `.runtime-cache/reports/tests/`.

Boundary notes:

- The one-command smoke here means local integration smoke. It is not CI `live-smoke` and cannot replace strict acceptance.
- Local test surfaces must stay separated: the sqlite path is for default fast regression, while the real Postgres path is for final integration-smoke acceptance.
- CI `live-smoke` only runs as a hard requirement on `main` push or nightly schedule, and it requires complete external provider secrets. See `docs/testing.md`.
- CI trust boundary: the repository currently supports only **trusted internal PRs** on the self-hosted main lane; forked or otherwise untrusted PRs are outside the supported path.
- PRs only conditionally trigger real LLM smoke (`pr-llm-real-smoke`); `web-e2e` uses the real API by default on the CI main path, and mock API remains for local debugging only.

Strict acceptance (the only authoritative entrypoint):

```bash
./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Repo-side authoritative entrypoint under the source-first public stance:

```bash
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Gate semantics note: total coverage has a hard floor of `>=95%`; Web `lines/functions/branches` must all satisfy `global >=95%` and `core >=95%`; and `strict-full-run=1` also forces mutation `score>=0.64 / effective_ratio>=0.27 / no_tests_ratio<=0.72` while forbidding both `ci-dedupe` and `skip-mutation`. Local smoke and strict acceptance both run fail-fast now; there is no offline fallback left.

When you run the formal pinned-image strict path locally, at least one of the following must be true:

- `GHCR_WRITE_USERNAME` + `GHCR_WRITE_TOKEN` are explicitly exported for local debugging
- `GHCR_USERNAME` + `GHCR_TOKEN` are explicitly exported for local debugging
- or the current `gh auth` session can pull the target GHCR image

Hosted `build-ci-standard-image.yml` now probes the repository-level `github.actor + GITHUB_TOKEN` token path first, may fall back to explicit `GHCR_WRITE_*` credentials, and may continue in a `fallback-unverified` mode when only the real hosted build/push can provide the decisive publish evidence.

- the current `gh auth` session is usable and will be reused by repository scripts

`--debug-build` is only for troubleshooting standard-environment build problems. It does not count toward CI-equivalent completion evidence.

Optional reader stack (Miniflux + Nextflux):

```bash
./bin/bootstrap-full-stack --with-reader-stack 1 --reader-env-file env/profiles/reader.env
```

## Where To Go Next

- local operations and parameter details: `docs/runbook-local.md`
- state machine and processing contracts: `docs/state-machine.md`
- environment variable contract: `ENVIRONMENT.md`
- collaboration and doc-drift rules: `AGENTS.md`
- full documentation index: `docs/index.md`
