# Repository Collaboration Contract

This file defines the human/AI collaboration rules for this repository. The goal is simple:

- reach the source of truth in 1 minute,
- complete a truthful local boot in 10 minutes,
- and keep docs, gates, and runtime truth aligned.

## -1. 15 Mandatory Standards (MUST)

These 15 rules are mandatory. `AGENTS.md` and `CLAUDE.md` must stay identical and must use MUST language.

1. The project purpose, tech stack, and navigation entrypoints MUST be explicit.
2. Documentation sources of truth and conflict priority MUST be explicit.
3. Startup modes MUST offer two paths: manual 6-step and one-command full-stack.
4. Golden commands MUST be directly executable and must match repository scripts.
5. Safety boundaries MUST explicitly list forbidden and confirmation-required actions.
6. Doc drift triggers MUST be defined and linked to code changes.
7. Git hooks alignment rules MUST be explicit and traceable to actual scripts.
8. The minimum DoD MUST include standard environment, env/test/lint/smoke gates.
9. Delivery format MUST stay fixed as four sections: changed files / executed commands / results / risks and follow-up.
10. Large modules (`apps/api`, `apps/worker`, `apps/mcp`, `apps/web`) MUST maintain both `AGENTS.md` and `CLAUDE.md`, and they MUST stay consistent.
11. Live tests that depend on external systems MUST use real keys, real browsers, and real external APIs/pages.
12. Pre-commit MUST block all linter errors and placebo assertions.
13. Coverage and mutation gates MUST satisfy: total coverage `>=95%`, important-module coverage `>=95%`, Python core mutation score `>=0.64`.
14. Long-running tests MUST emit heartbeats; short tests MUST run before long tests; parallelizable work MUST run in parallel.
15. Remote CI reruns MUST only happen after local pre-push is green; when remote CI fails, maintainers MUST reproduce and fix locally before the next remote run.

## 0. Project Purpose, Stack, and Navigation

### 0.1 Project Purpose

This repository turns video content (YouTube, Bilibili, and similar sources) into structured, searchable, subscribable, and distributable information flows.

Core goals:

- ingest and analyze content (`metadata / subtitles / comments / frames / LLM digest`),
- expose the results through `API / MCP / Web`,
- remain local-first, reproducible, and gate-verified.

### 0.2 Current Stack

- Backend/API: Python + FastAPI + SQLAlchemy
- Worker: Python + Temporal + pipeline steps
- MCP: FastMCP tool layer
- Frontend: Next.js (`apps/web`)
- Data: PostgreSQL + SQLite
- Tooling: uv, pytest, Playwright, npm lint/test, ruff

### 0.3 Navigation Entry Order

1. `docs/start-here.md` - the only 1-minute entrypoint
2. `README.md` - repository front door
3. `docs/runbook-local.md` - local operator authority
4. `docs/state-machine.md` - 3-stage + 9-step contract
5. `docs/testing.md` - CI / hook / smoke policy

### 0.4 AI Navigation Index (Lazy-Load)

Load root first, then only the module you actually touch:

1. Root governance
   - `AGENTS.md`
   - `CLAUDE.md`
2. Start here
   - `docs/start-here.md`
3. API module
   - `apps/api/AGENTS.md`
   - `apps/api/CLAUDE.md`
4. Worker module
   - `apps/worker/AGENTS.md`
   - `apps/worker/CLAUDE.md`
5. MCP module
   - `apps/mcp/AGENTS.md`
   - `apps/mcp/CLAUDE.md`
6. Web module
   - `apps/web/AGENTS.md`
   - `apps/web/CLAUDE.md`

## 1. Documentation Sources of Truth

Priority order:

1. `docs/start-here.md`
2. `docs/runbook-local.md`
3. `docs/state-machine.md`
4. `ENVIRONMENT.md` + `infra/config/env.contract.json`
5. `docs/testing.md`
6. module docs: `apps/*/(AGENTS.md|CLAUDE.md)`
7. `README.md`

Conflict rule:

- lower-priority docs MUST be updated to match higher-priority docs,
- module execution details follow module docs,
- cross-module and global policy follow root docs.

## 2. Startup Modes

### Mode A: Manual 6-Step Path

1. install dependencies
2. start base services
3. initialize environment
4. run migrations
5. start API / Worker / MCP
6. run minimum verification

### Mode B: One-Command Full-Stack Path

- `./bin/bootstrap-full-stack`
  - `./bin/full-stack up`
  - `./bin/smoke-full-stack`
  - `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`

### Mode C: Standard Environment (Required For AI Execution)

- DevContainer: `.devcontainer/devcontainer.json`
- Infrastructure Compose:
  - `infra/compose/core-services.compose.yml`
  - `infra/compose/miniflux-nextflux.compose.yml`

Always enter the standard environment before running Mode A or B when you need CI-equivalent evidence.

Useful commands:

- status: `./bin/full-stack status`
- logs: `./bin/full-stack logs`
- shutdown: `./bin/full-stack down`

## 3. Golden Commands

### 3.1 Install Dependencies

```bash
uv sync --frozen --extra dev --extra e2e
npm --prefix apps/web ci
```

### 3.2 Initialize Environment

```bash
cp .env.example .env
python3 scripts/governance/check_env_contract.py --strict
set -a; source .env; set +a
```

Environment policy:

- use `core + profile overlay`,
- inject secrets only through `.env` or process environment,
- never depend on shell login config as runtime secret storage.

### 3.3 Start Base Services

```bash
brew services start postgresql@16
temporal server start-dev --ip 127.0.0.1 --port 7233
```

### 3.4 Run Migrations

```bash
createdb video_analysis 2>/dev/null || true
for migration in $(ls infra/migrations/*.sql | sort); do
  psql "postgresql://localhost:5432/video_analysis" -v ON_ERROR_STOP=1 -f "$migration"
done
sqlite3 "$SQLITE_PATH" < infra/sql/sqlite_state_init.sql
```

### 3.5 Start Services

```bash
./bin/dev-api
./bin/dev-worker
./bin/dev-mcp
```

### 3.6 Minimum Verification

```bash
curl -sS http://127.0.0.1:9000/healthz
curl -sS -X POST http://127.0.0.1:9000/api/v1/ingest/poll \
  -H 'Content-Type: application/json' \
  -d '{"max_new_videos": 20}'
```

### 3.7 Full-Stack Smoke

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack --offline-fallback 0
```

### 3.8 Install Git Hooks

```bash
./bin/install-git-hooks
```

## 4. Safety Boundaries

### 4.1 Git And Filesystem Red Lines

- Never use `git push --force`, `git reset --hard`, or `git clean -fd`.
- Never perform destructive deletes without explicit confirmation.
- Never commit, amend, or push unless the user explicitly asked for it.

### 4.2 Production / High-Risk Red Lines

- Never connect to or modify production resources without explicit authorization.
- Confirm before handling secrets, tokens, passwords, or credentials.
- Confirm before destructive database actions such as drop, truncate, or irreversible migrations.

## 5. Doc Drift Triggers

When these code surfaces change, the paired docs MUST be updated:

- `infra/migrations/*.sql` -> `README.md`, `docs/runbook-local.md`
- `apps/worker/worker/pipeline/types.py` `PIPELINE_STEPS` -> `docs/state-machine.md`
- environment variables -> `.env.example`, `ENVIRONMENT.md`, `infra/config/env.contract.json`
- `apps/api/app/routers/*.py` -> `docs/reference/mcp-tool-routing.md`, `README.md`
- `apps/api/app/schemas/*.py` -> `docs/state-machine.md`, `README.md`
- local startup scripts / defaults -> `docs/start-here.md`, `docs/runbook-local.md`, `README.md`
- `infra/compose/*.compose.yml` or `.devcontainer/**` -> `README.md`, `docs/start-here.md`, `docs/runbook-local.md`
- logging policy -> `docs/reference/logging.md`
- cache policy -> `docs/reference/cache.md`
- dependency policy -> `docs/reference/dependency-governance.md`

### 5.1 Git Hooks Alignment

- `.githooks/commit-msg`
  - `npx --yes --package @commitlint/cli commitlint --config <tmp-config> --edit <commit-msg-file>`
  - Conventional Commits are mandatory even when no root `package.json` dependency exists.
- `.githooks/pre-commit`
  - `./bin/quality-gate --mode pre-commit --profile local`
  - includes `scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged`
  - includes docs governance, fake-assertion guard, web lint, ruff critical, secrets scan, gitleaks fast scan, structured-log guard, env budget guard, and IaC entrypoint guard
- `.githooks/pre-push`
  - `./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0`
  - includes `scripts/governance/ci_or_local_gate_doc_drift.sh --scope push`
  - includes coverage, core coverage, web unit tests, Python tests without silent skip, API CORS preflight smoke, and local contract-diff checks
  - pre-push is intentionally stricter than pre-commit, with change-aware mutation behavior

### 5.2 Remote CI Cost Governance

- Before triggering or rerunning remote CI, local pre-push MUST already be green:
  - `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
- Remote CI is only a double-check; it never replaces local acceptance.
- When remote CI fails, reproduce and fix locally before the next remote run.
- Cancel superseded in-progress remote runs on the same branch.
- During budget or billing anomalies, freeze non-essential reruns.
- Self-hosted CI only accepts **trusted internal PRs**.
- `config/docs/*.json` is the docs control-plane source of truth; high-drift references render into `docs/generated/*.md`.

## 6. Minimum DoD

A task is done only when all applicable checks pass:

1. Doc linkage is complete.
2. The change is verified from the standard environment and leaves command evidence.
3. Environment contract check passes:
   - `python3 scripts/governance/check_env_contract.py --strict`
4. Backend tests pass:
   - `PYTHONPATH="$PWD:$PWD/apps/worker" DATABASE_URL='sqlite+pysqlite:///:memory:' uv run pytest apps/worker/tests apps/api/tests apps/mcp/tests -q`
5. Frontend lint passes:
   - `npm --prefix apps/web run lint`
6. Fake-assertion guard passes:
   - `python3 scripts/governance/check_test_assertions.py`
7. Startup or workflow logic changes must pass the strict entrypoint:
   - `./bin/strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0`
8. Coverage and mutation thresholds pass:
   - total coverage `>=95%`
   - core coverage `>=95%`
   - `DATABASE_URL='sqlite+pysqlite:///:memory:' uv run --extra dev --with mutmut mutmut run`
   - `score>=0.64`
   - `effective_ratio>=0.27`
   - `no_tests_ratio<=0.72`

## 7. Delivery Format

Every delivery update must include these four sections:

1. Changed files
2. Executed commands
3. Results
4. Risks and follow-up

Maintenance rule:

- whenever this file changes, commands MUST remain executable from the repo root,
- and the content MUST stay aligned with `docs/start-here.md` and `docs/runbook-local.md`.
