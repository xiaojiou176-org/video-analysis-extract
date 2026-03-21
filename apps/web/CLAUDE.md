# Web Module Governance

## 0. Canonical Scope

- This file is the English-first canonical governance surface for the web module.
- `apps/web/AGENTS.md` and `apps/web/CLAUDE.md` MUST stay content-identical.

## 1. Module Mission

- This module provides the web console and operator-facing UI for the video analysis system.
- It MUST cover subscription management, job status, artifact viewing, settings, and interaction feedback.

## 2. Tech Stack

- Next.js
- TypeScript
- Playwright + Vitest

## 3. Lazy-Load Navigation

1. `apps/web/app/` for App Router pages and server actions
2. `apps/web/components/` for reusable components
3. `apps/web/lib/` for API clients and utilities
4. `apps/web/tests/e2e/` and `apps/web/__tests__/` for tests
5. `apps/web/app/page.tsx` for the home entrypoint

## 4. Required Commands

```bash
./bin/prepare-web-runtime
npm --prefix apps/web run lint
npm --prefix apps/web run test
uv run --with pytest --with playwright pytest apps/web/tests/e2e -q
```

## 5. Verification Requirements (MUST)

1. Any page, interaction, or state-flow change MUST pass `lint + test`.
2. Any E2E scope change MUST sync `docs/testing.md`.
3. Any cross-module change MUST also satisfy the root gates: env contract, backend pytest, web lint, and the fake assertion gate.
4. Any startup-path or integration-flow change MUST run `./bin/smoke-full-stack`, or the delivery report MUST explicitly explain why it was not run.

## 6. Module Document Truth Order

1. `apps/web/AGENTS.md`
2. `apps/web/CLAUDE.md`
3. `docs/testing.md`
4. `docs/start-here.md`
5. `docs/runbook-local.md`
6. Root `AGENTS.md` / `CLAUDE.md`

Conflict handling:
Frontend testing scope and execution details defer to this module document and `docs/testing.md` first. Cross-module and global rules defer to the root governance documents.

## 7. Doc Drift Triggers

- If page routes, key interaction flows, or testing scope changes, sync `docs/testing.md` and `README.md`.
- If local startup procedures or script defaults change, sync `docs/start-here.md` and `docs/runbook-local.md`.
- If environment variables change, sync `.env.example`, `ENVIRONMENT.md`, and `infra/config/env.contract.json`.

## 8. Hook Alignment

- `pre-commit`: `./bin/quality-gate --mode pre-commit` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope staged`
- `pre-push`: `./bin/strict-ci --mode pre-push --heartbeat-seconds 20 --ci-dedupe 0` including `scripts/governance/ci_or_local_gate_doc_drift.sh --scope push`
