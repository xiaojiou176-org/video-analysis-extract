# Repo Governance Final Form Execution Plan

## Header

- Plan Title: Repo Governance Final Form Execution Plan
- Created At: 2026-03-15 06:07:57 America/Los_Angeles
- Last Updated: 2026-03-15 15:03:28 America/Los_Angeles
- Repo Name: 视频分析提取
- Repo Path: /Users/yuyifeng/Documents/VS Code/1_Personal_Project/[其他项目]Useful_Tools/📺视频分析提取
- Repo Archetype: hybrid-repo
- Final Goal: Push the repository to final-form governance for architecture, cache, logging, root cleanliness, and upstream integration.
- Current Status: In Progress
- Current Phase: Phase K - Post-Revalidation Forward Work
- Current Workstream: WS-07 Integration Boundary Refactor

## Objective

This file is the single execution truth source for the current governance refactor. It is not an archive note. It records the target state, current state, migration workstreams, decisions, validations, blockers, changed files, and the next irreversible actions.

## Score Targets

| Dimension | Target |
| :- | :- |
| Architecture Governance | 30 / 30 |
| Cache Governance | 20 / 20 |
| Logging Governance | 20 / 20 |
| Root Cleanliness Governance | 10 / 10 |
| Upstream Integration Governance | 20 / 20 |

## Current Status

| Dimension | Target | Current Audit Baseline | Execution Target | Status |
| :- | :- | :- | :- | :- |
| Architecture Governance | 30 / 30 | 25 / 30 | Hard-cut public entrypoint split, contracts purity, explicit integration layer | In Progress |
| Cache Governance | 20 / 20 | 17 / 20 | Single runtime output root with write-time metadata discipline | In Progress |
| Logging Governance | 20 / 20 | 16 / 20 | Unified run manifest, correlation, upstream failure classification | In Progress |
| Root Cleanliness Governance | 10 / 10 | 8 / 10 | Root allowlist + budget + dirtiness fail-closed with new `.agents` and `bin` | In Progress |
| Upstream Integration Governance | 20 / 20 | 17 / 20 | Inventory + compatibility + explicit integration boundary | In Progress |

## Workstream Table

| Workstream | Status | Priority | Current Owner | Recent Action | Next Step | Validation Status |
| :- | :- | :- | :- | :- | :- | :- |
| WS-00 Plan Control Board | Completed | P0 | Codex | Landed and continuously updated the in-repo execution ledger | Keep it current in later sessions | Verified |
| WS-01 Public Entrypoint Migration | Completed | P0 | Codex | Added stable `bin/*` entrypoints and repointed active docs/hooks/workflows/tests | Extend cutover to deeper historical surfaces only if they become active again | Verified |
| WS-02 Root Governance Alignment | Completed | P0 | Codex | Legalized `.agents` and `bin` in allowlist, semantic cleanliness, and budget | Preserve root budget headroom in later phases | Verified |
| WS-03 Bridge Registry And Expiry Gate | Completed | P1 | Codex | Added bridge registry, bridge expiry gate, and wired it into governance audit | Use the registry to close future bridges instead of adding ad-hoc shims | Verified |
| WS-04 Runtime Output And Metadata Hardening | In Progress | P1 | Codex | Added managed artifact writer coverage gate after migrating more high-value report writers | Continue covering deeper release/runtime writers and then hard-cut `temp -> tmp` | Partially Verified |
| WS-05 Logging And Correlation Hardening | In Progress | P1 | Codex | Added run-manifest bootstrap and now a passing manifest completeness gate | Add an upstream-specific log channel and richer provider failure attribution | Verified |
| WS-06 Contracts And Generated Surface Split | Completed | P1 | Codex | Hard-cut source and generated contract surfaces out of `packages/shared-contracts` into `contracts/` and rewired active references | Keep watching for stale bridge references, but active migration is finished | Verified |
| WS-07 Integration Boundary Refactor | In Progress | P1 | Codex | Introduced `integrations/`, completed the media-binary slice, and extracted the Resend provider slice into `integrations/providers` | Continue with the next upstream family after validating the provider slice and choosing the next narrow extraction target | Partially Verified |
| WS-08 Docs And Governance Surface Repoint | Partially Completed | P2 | Codex | Repointed active top-level and module docs to `bin/*`; historical/generated surfaces intentionally left untouched in this batch | Finish render-driven and historical-surface cleanup when the contract and integration moves start | Partially Verified |
| WS-09 Validation And Closure | Completed | P0 | Codex | Repointed the last stale release/docs defaults away from root `reports/`, revalidated targeted governance surfaces, and re-proved `strict-ci` end-to-end on the current dirty workspace | Carry the fresh strict-ci pass forward as the new validation baseline while resuming deeper WS-07/WS-04 structural work | Verified |

## Task Checklist

### WS-00 Plan Control Board

- [x] Create `.agents/Plans/`
  - Goal: Land the execution plan inside the repo.
  - Validation: plan file exists under `.agents/Plans/`.
  - Evidence: `.agents/Plans/2026-03-15_06-07-57__repo-governance-final-form-execution-plan.md`
- [-] Keep this plan file synchronized with every structural action
  - Goal: Prevent chat-only state drift.
  - Validation: `Last Updated`, `Current Phase`, `Current Workstream`, `Decision Log`, `Validation Log`, `Files Changed Log` stay current.

### WS-01 Public Entrypoint Migration

- [x] Add stable `bin/*` public entrypoints
  - Goal: Introduce stable public wrappers without rewriting internal shell implementations yet.
  - Validation: wrapper files exist under `bin/`.
  - Evidence: `bin/bootstrap-full-stack`, `bin/full-stack`, `bin/dev-api`, `bin/dev-worker`, `bin/dev-mcp`, `bin/quality-gate`, `bin/strict-ci`, `bin/governance-audit`, `bin/upstream-verify`
- [x] Repoint hooks to `bin/*`
  - Validation: `.githooks/pre-commit`, `.githooks/pre-push`
  - Evidence: hooks now call `bin/quality-gate` and `bin/strict-ci`
- [x] Repoint governance and CI workflows to `bin/*`
  - Validation: `.github/workflows/ci.yml`, `monthly-governance-audit.yml`, `vendor-governance.yml`
  - Evidence: strict CI and governance audit jobs now call `bin/*`
- [x] Repoint top-level docs to `bin/*`
  - Validation: `README.md`, `docs/start-here.md`, `docs/testing.md`, `docs/runbook-local.md`, `docs/governance/final-form.md`, module `AGENTS.md` / `CLAUDE.md`
  - Evidence: active doc surfaces now expose `bin/*` as the public path
- [x] Repoint workflow strictness checks and tests to `bin/*`
  - Validation: `scripts/governance/check_ci_workflow_strictness.py`, `scripts/governance/check_ci_smoke_drift.sh`, targeted pytest
  - Evidence: 43 governance/workflow tests passed

### WS-02 Root Governance Alignment

- [x] Add `.agents` to tracked root allowlist
- [x] Add `bin` to tracked root allowlist
- [x] Increase root directory budget to match the new final-form structure
- [x] Update root governance docs to explain `.agents` and `bin`

### WS-03 Bridge Registry And Expiry Gate

- [x] Create governance bridge registry
  - Goal: Record every temporary compatibility bridge with owner and removal deadline.
  - Validation: `config/governance/bridges.json` exists and is schema-valid.
- [x] Add bridge expiry validation script
  - Goal: Fail when bridges age out without closure.
  - Validation: `scripts/governance/check_bridge_expiry.py` executes successfully after wiring.
- [x] Wire bridge expiry script into governance gate
  - Validation: `./bin/governance-audit --mode audit`
  - Evidence: bridge expiry check passed inside governance audit

### WS-04 Runtime Output And Metadata Hardening

- [x] Legalize `.runtime-cache/tmp` as a governed bridge target
  - Goal: Prevent the bridge registry from declaring a runtime child that governance still treats as illegal.
  - Validation: `python3 scripts/governance/check_runtime_outputs.py`
  - Evidence: runtime outputs pass with both `tmp` and `temp` declared
- [x] Fix validation commands to avoid root `.venv` pollution
  - Goal: Keep root clean during targeted pytest runs.
  - Validation: rerun targeted pytest with `PYTHONDONTWRITEBYTECODE=1` and `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env`
  - Evidence: root allowlist and governance audit pass after test runs
- [ ] Identify every freshness-required artifact write path
- [-] Force write-time sidecar metadata instead of maintenance-only backfill
- [x] Add managed artifact writer helpers for repo-side runtime outputs
  - Goal: Stop duplicating ad-hoc metadata logic in individual scripts.
  - Validation: helper-backed scripts import and execute.
  - Evidence: `scripts/governance/common.py` now exposes `maybe_write_runtime_metadata`, `write_text_artifact`, `write_json_artifact`
- [x] Move key Python report writers to managed artifact helpers
  - Goal: Push high-frequency `.runtime-cache/reports/**` producers to write metadata at write time.
  - Validation: modified scripts parse and run `--help` / direct check commands successfully.
  - Evidence: `scripts/governance/check_runtime_cache_freshness.py`, `scripts/governance/build_nightly_flaky_report.py`, `scripts/governance/report_env_governance.py`, `scripts/ci/autofix.py`, `scripts/ci/gemini_ui_ux_audit.py`
- [x] Move key smoke diagnostics JSON writers to managed artifact helpers
  - Goal: Reduce maintenance-only metadata dependence for `.runtime-cache/reports/tests/*.json`.
  - Validation: shell syntax passes for modified smoke scripts.
  - Evidence: `scripts/ci/smoke_llm_real_local.sh`, `scripts/ci/external_playwright_smoke.sh`
- [x] Add runtime artifact writer coverage gate
  - Goal: Stop relying on memory to find unmanaged `.runtime-cache/reports/**` and `.runtime-cache/evidence/**` writers.
  - Validation: `python3 scripts/governance/check_runtime_artifact_writer_coverage.py`
  - Evidence: gate is wired in `scripts/governance/gate.sh`, documented in `docs/reference/evidence-model.md`, and passes
- [ ] Add validation that fresh artifacts are metadata-complete immediately after generation

### WS-05 Logging And Correlation Hardening

- [x] Define run-manifest-first policy
  - Goal: Stable public entrypoints should register an explicit run manifest before they hand off to internal scripts.
  - Validation: `scripts/runtime/write_run_manifest.py`, `scripts/runtime/entrypoint.sh`, `docs/reference/evidence-model.md`
  - Evidence: `.runtime-cache/run/manifests/*.json` now appear after public entrypoint execution
- [ ] Add upstream-specific log channel plan
- [x] Ensure public entrypoints allocate run correlation before invoking internal scripts
  - Goal: `bin/*` entrypoints should not rely on downstream scripts to invent their run correlation context.
  - Validation: `python3 scripts/governance/check_public_entrypoint_manifests.py`
  - Evidence: all governed `bin/*` entrypoints now source `scripts/runtime/entrypoint.sh` and call `vd_entrypoint_bootstrap`
- [x] Add manifest completeness gate
  - Goal: Confirm the run manifest is not just a cover page, but that it actually points to current runtime evidence.
  - Validation: `python3 scripts/governance/check_run_manifest_completeness.py`
  - Evidence: governance audit and standalone manifest completeness checks now pass after fresh manifest regeneration

### WS-06 Contracts And Generated Surface Split

- [x] Design `contracts/source` and `contracts/generated` move
  - Goal: Split handwritten source contracts from generated contract surfaces.
  - Validation: `contracts/source/openapi.yaml` and `contracts/generated/jsonschema/*` exist.
- [x] Freeze new writes into `packages/shared-contracts`
  - Goal: Stop using the legacy shared-contracts path as the active contract root.
  - Validation: active refs in workflows/docs/gates/tests repointed to `contracts/*`.
- [x] Add migration bridge and cutover checkpoints
  - Goal: Record the move in `bridges.json` and make the bridge state explicit.
  - Validation: bridge updated to completed and governance audit remains green.
- [x] Move contract files into final-form contracts root
  - Goal: Make `contracts/` the real contract room, not just a future sketch.
  - Validation: contract files now live under `contracts/`, and `packages/` no longer exists.
  - Evidence: `contracts/README.md`, `contracts/AGENTS.md`, `contracts/CLAUDE.md`, `contracts/source/openapi.yaml`, `contracts/generated/jsonschema/*`
- [x] Repoint active references from shared-contracts to contracts
  - Goal: Remove active-path drift after the move.
  - Validation: targeted residual-path scan; governance gates and tests pass.
  - Evidence: workflows, docs, gates, and tests now reference `contracts/*`

### WS-07 Integration Boundary Refactor

- [x] Inventory direct upstream coupling points
  - Goal: Identify which upstream family is safest for the first explicit extraction slice.
  - Validation: targeted grep over active non-test coupling points.
- [x] Define explicit `integrations/` target tree
  - Goal: Establish a real root-level integration boundary rather than leaving the layer as a plan-only concept.
  - Validation: `integrations/README.md` exists and root governance accepts the new directory.
- [-] Prepare hard-cut migration rules for direct upstream calls
  - Goal: Move direct upstream command construction out of worker business steps and into the integration layer in narrow slices.
  - Validation: first slice tests and governance audit pass.
- [x] Extract media binary command construction into integration layer
  - Goal: Move `yt-dlp` / `ffmpeg` / `bbdown` command building out of worker step modules.
  - Validation: targeted worker tests pass and governance audit remains green.
  - Evidence: `integrations/binaries/media_commands.py`, worker step modules updated to consume it
- [x] Extract Resend provider implementation into integration layer
  - Goal: Move outbound Resend request construction and sanitization logic out of service/activity implementation layers.
  - Validation: targeted API + worker notification tests pass and governance audit remains green.
  - Evidence: `integrations/providers/resend.py`, API notifications and worker email activities now act as thin wrappers

### WS-08 Docs And Governance Surface Repoint

- [ ] Repoint README/start-here/runbook/testing to stable public entrypoints
- [ ] Keep high-drift facts in SSOT/render sources, not manual mirrors
- [ ] Record every public command migration in docs

### WS-09 Validation And Closure

- [ ] Run root allowlist checks
- [ ] Run root dirtiness checks
- [ ] Run bridge expiry gate
- [ ] Run governance gate
- [ ] Run targeted tests for changed governance contracts

## Decision Log

| Time | Decision | Why | Rejected Alternative | Impact |
| :- | :- | :- | :- | :- |
| 2026-03-15 06:07:57 | Use `.agents/Plans/` as the in-repo execution control plane | User explicitly required in-repo plan as single source of truth | Keep state only in chat | Introduces a new tracked top-level governance directory |
| 2026-03-15 06:07:57 | Start with public entrypoint hardening before deeper contracts/integrations refactors | Public entrypoints are the highest-leverage hard cut and the least invasive way to make governance real immediately | Jump directly into `contracts/` or `integrations/` moves while public docs and CI still call old paths | Forces hooks, CI, and docs onto stable `bin/*` wrappers first |
| 2026-03-15 06:10:40 | Add a bridge registry before finishing the first hard cut | The repo already has multiple migration fronts; bridges must be tracked from day one so temporary aliases do not become permanent infrastructure | Delay bridge tracking until after the first public entrypoint migration | Gives every bridge a deadline and an owner before more cutovers begin |
| 2026-03-15 06:16:00 | Treat `.runtime-cache/tmp` as a governed bridge subdir now, not a future-only idea | The bridge registry must not point at a runtime path that the control plane still rejects | Remove the tmp bridge entry and pretend the migration will happen later | Lets the runtime output control plane recognize the final-form target while `temp` still exists |
| 2026-03-15 06:18:00 | Use `PYTHONDONTWRITEBYTECODE=1` plus `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env` for governance pytest validation | A plain `uv run pytest` created a root `.venv`, which violates root cleanliness | Tolerate `.venv` in root allowlist | Keeps validation clean without weakening root governance |
| 2026-03-15 06:23:00 | Stop this session after the public-entrypoint/root/runtime bridge batch instead of forcing the `contracts/` and `integrations/` hard cuts on the current dirty worktree | The remaining moves are broad shared-file migrations with high conflict risk against existing in-flight governance edits | Attempt repo-wide moves blindly in the current dirty state | Converts the remaining scope into explicit blocked workstreams rather than unsafe half-migrations |
| 2026-03-15 06:39:00 | Add a shared managed-artifact helper before touching more report writers | Repeating per-script metadata glue would create another form of drift | Patch each report writer ad-hoc | Centralizes write-time metadata discipline in one reusable helper surface |
| 2026-03-15 06:41:00 | Cover the highest-value Python report writers first, then the highest-value smoke diagnostics JSON writers | These files land in freshness-required runtime report paths most often and are cheap to validate | Try to patch every report/evidence writer in one batch | Produces measurable metadata hardening progress without turning the batch into an unsafe repo-wide sweep |
| 2026-03-15 06:47:00 | Make `bin/doctor` set `PYTHONDONTWRITEBYTECODE=1` unconditionally | The official doctor entrypoint must not be allowed to create its own `__pycache__` residue under source directories | Accept `doctor` as a special-case dirty command | Keeps the diagnosis entrypoint aligned with root cleanliness rules |
| 2026-03-15 06:54:00 | Add a runtime artifact writer coverage gate after migrating the first high-value writers | Without a gate, WS-04 would regress back into manual spot-checking | Keep inventory only in the execution plan | Turns the remaining runtime metadata hardening work into a machine-audited backlog instead of a memory task |
| 2026-03-15 07:01:00 | Start WS-05 with static public-entrypoint manifest enforcement instead of historical run-data enforcement | Historical `.runtime-cache` contents are noisy and would make a first manifest gate brittle | Fail builds on missing manifests for old run data before the new entrypoints have had time to populate clean manifests | Gives the repo a reliable run-manifest foundation without being blocked by historical artifacts |
| 2026-03-15 07:14:00 | Re-open WS-06 once the worktree is clean and the active contract move is small enough to finish end-to-end in one batch | The earlier blocker was about doing a broad shared-file migration on a dirty baseline, not about the move being impossible | Keep deferring `contracts/` even after the repository reached a clean baseline | Allowed the contract hard cut to be finished safely instead of lingering as a permanent bridge |
| 2026-03-15 07:27:00 | Start WS-07 with a narrow media-binary slice instead of trying to relocate every upstream family at once | `yt-dlp / ffmpeg / bbdown` command construction is a clean, high-signal extraction target with direct tests and low API-surface ambiguity | Attempt a repo-wide `integrations/` move in one batch | Converts WS-07 from “blocked giant project” into “running migration with a proven first slice” |
| 2026-03-15 07:29:00 | Migrate root `reports/` into `artifacts/` before raising root cleanliness claims further | The root directory cannot reach final-form cleanliness while long-lived artifacts still occupy the hallway | Leave `reports/` in place until every other workstream is finished | Frees the root from a permanent semantic conflict and makes the remaining R4 gap much smaller |
| 2026-03-15 07:43:00 | Scope manifest completeness to fresh current-run manifests and exclude evidence-index self-reference | The first completeness pass was catching stale/current mixed manifests and the index file trying to reference itself | Force historical manifests to satisfy a current-run gate | Makes WS-05 validate the thing it is actually supposed to validate: that new public entrypoints produce a coherent current-run case file |
| 2026-03-15 07:52:00 | Extract Resend as the second integration slice by moving the real provider logic into `integrations/providers/resend.py` while keeping service/activity wrappers stable | Resend is a narrow, test-rich provider family with clear boundaries and low migration ambiguity | Jump directly to a larger provider family like Gemini or a multi-service reader slice | Expands WS-07 from binary-only to provider API extraction without breaking existing API or worker call sites |
| 2026-03-15 09:08:00 | Make upstream compatibility freshness enforce only rows that currently claim `verification_status=verified`, and downgrade blocker chains without fresh runtime receipts to `pending` | The matrix must be honest: a row cannot claim “freshly verified” when the required runtime artifacts are absent from the live workspace | Leave the gate requiring artifacts for every row, or keep missing-artifact blocker rows marked `verified` | Restores contract truth between matrix status and artifact evidence instead of letting the gate or the data lie |
| 2026-03-15 09:30:40 | Treat the old Docker timeout as resolved and carry forward the new strict-ci first failure instead of leaving closure blocked on stale infrastructure evidence | Fresh probes now show `docker version`, `docker info`, and `docker ps` all respond; the real blocker moved forward to mutation sandbox drift after the `integrations/` move | Keep calling Docker the blocker after new evidence exists | Keeps the closure log honest and turns the next step into a repo-side fix instead of an infrastructure shrug |
| 2026-03-15 09:39:30 | Remove the empty legacy root `reports/` subtree immediately instead of tolerating it until a later cleanup pass | Once `artifacts/` is the long-lived home, leaving an empty `reports/` hallway behind only creates fake root-governance failures and blocks strict-ci for the wrong reason | Leave the empty legacy directory until a final sweep | Keeps closure focused on the next real failure instead of a stale migration shell |
| 2026-03-15 09:47:20 | Fix the mutmut sandbox at its true wiring point instead of only patching pyproject metadata | The strict-ci failure came from `scripts/ci/run_mutmut.sh` not linking the new `integrations/` top-level directory into the mutation workspace; `also_copy` alone was not enough | Re-run strict-ci repeatedly without fixing the shell-level sandbox bootstrap | Aligns the mutation sandbox with the new root architecture so mutmut sees the same module tree as normal execution |
| 2026-03-15 09:54:40 | Record the live strict-ci rerun as the current closure checkpoint instead of waiting to update the control board until the rerun ends | The source of truth should show that fresh standard-env validation is actively in progress, not pretend the repo is still waiting to rerun | Leave the control board on the old “pending rerun” wording until the process finishes | Keeps the repo-side state machine synchronized with the actual active validation run |

## Validation Log

| Validation Item | Status | Validation Method | Result | Notes |
| :- | :- | :- | :- | :- |
| Plan file exists in repo | Completed | File presence | Created | Initial landing step complete |
| `.agents` legal under root governance | Completed | `check_root_allowlist` + `check_root_layout_budget` + `check_root_zero_unknowns` + semantic cleanliness via governance audit | PASS | `.agents` is now a governed public control-plane directory |
| `bin/*` wrappers exist | Completed | File presence + executable bit + `--help` smoke | PASS | Stable public entrypoints now exist and advertise the new paths |
| Bridge registry exists | Completed | File presence + `check_bridge_expiry.py` + governance audit | PASS | Bridge control plane is live |
| Root governance batch | Completed | `python3 scripts/governance/check_root_allowlist.py --strict-local-private && python3 scripts/governance/check_root_layout_budget.py && python3 scripts/governance/check_root_zero_unknowns.py && python3 scripts/governance/check_bridge_expiry.py && python3 scripts/governance/check_runtime_outputs.py` | PASS | Confirms `.agents`, `bin`, bridge registry, and runtime output bridge are legal |
| Governance control plane batch | Completed | `./bin/governance-audit --mode audit` | PASS | Full governance gate passed after all batch-1 fixes |
| Workflow/governance tests | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env uv run pytest apps/worker/tests/test_governance_controls.py apps/worker/tests/test_ci_workflow_strictness.py -q` | PASS (43 passed, 2 warnings) | Warnings are existing pytest config warnings about `reruns` / `reruns_delay` on Python 3.14, not failures |
| Stable public doctor entrypoint | Completed | `./bin/doctor` | PASS | Quick governance health entrypoint is available and no longer leaves bytecode residue under `apps/` or `scripts/` |
| Managed artifact helper batch | Completed | `python3 scripts/governance/check_runtime_cache_freshness.py` + helper-based script `--help` smoke + shell syntax checks | PASS | Confirms helper-backed report writers and smoke scripts still parse and the freshness report itself now writes through the helper |
| Runtime artifact writer coverage gate | Completed | `python3 scripts/governance/check_runtime_artifact_writer_coverage.py` + targeted pytest | PASS | The new gate is wired, documented, and currently passes on the active script surface |
| Public entrypoint manifest gate | Completed | `bash -n bin/* scripts/runtime/entrypoint.sh && python3 scripts/governance/check_public_entrypoint_manifests.py` | PASS | Static gate confirms all governed `bin/*` entrypoints write manifests before handoff |
| Run manifest foundation | Completed | `./bin/doctor && ./bin/governance-audit --help >/dev/null && ./bin/strict-ci --help >/dev/null` plus manifest directory inspection | PASS | Public entrypoints now create `.runtime-cache/run/manifests/<run_id>.json` artifacts |
| Run manifest completeness gate | Completed | clean manifest regeneration + `./bin/governance-audit --mode audit` + standalone `python3 scripts/governance/check_run_manifest_completeness.py` | PASS | Current-run manifests now prove they point to real runtime logs and indexed runtime artifacts |
| Contracts hard-cut batch | Completed | `python3 scripts/governance/check_contract_locality.py && python3 scripts/governance/check_contract_surfaces.py && python3 scripts/governance/check_generated_vs_handwritten_contract_surfaces.py` + targeted pytest + governance audit | PASS | Contract root is now `contracts/`, and active gate/test/workflow/docs references were updated successfully |
| Root artifact migration batch | Completed | residual `reports/*` scan + root/governance checks + targeted release governance tests | PASS | Root long-lived report surfaces moved to `artifacts/`, and the root allowlist now accepts `artifacts` instead of `reports` |
| Integration first slice batch | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env uv run pytest apps/worker/tests/test_metadata_and_prompts.py apps/worker/tests/test_runner_fallbacks.py apps/worker/tests/test_worker_step_branches.py apps/worker/tests/test_governance_controls.py -q` + governance audit | PASS (27 passed) | Media binary command construction now lives in the integration layer without breaking worker flow tests |
| Resend provider slice batch | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env uv run pytest apps/api/tests/test_notifications_service.py apps/api/tests/test_notifications_service_extra_coverage.py apps/worker/tests/test_temporal_helpers_coverage.py apps/worker/tests/test_governance_controls.py -q` + governance audit | PASS (39 passed) | Resend outbound provider logic now lives in `integrations/providers/resend.py` while API/worker layers keep thin compatibility wrappers |
| Honest upstream compat freshness semantics | Completed | `PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env uv run pytest apps/worker/tests/test_governance_controls.py -q` + `python3 scripts/governance/check_upstream_compat_freshness.py` + `./bin/governance-audit --mode audit` | PASS | The matrix now only claims `verified` when fresh runtime artifacts exist; non-fresh blocker chains are explicitly `pending` instead of lying |
| Git closure snapshot | Completed | `git status --short --branch` + `git branch -vv` + `git worktree list` + `git ls-remote --heads origin` + `gh pr list --state open --limit 50` + `git rev-parse HEAD && git rev-parse origin/main` | PASS | Live workspace re-check shows one local branch (`main`), one worktree, no open PRs, and local `main` aligned with `origin/main` before the new closure commit |
| Docker responsiveness probe | Completed | `docker version --format '{{json .}}'` + `docker info --format '{{json .}}'` + `docker ps --format '{{json .}}'` | PASS | Docker is responsive again; the old infrastructure blocker is no longer current |
| Strict-ci first-failure refresh | Completed | `./bin/strict-ci --debug-build --mode pre-push --strict-full-run 1 --ci-dedupe 0` | FAIL in mutation gate | The first current repo-side failure is now concrete: mutmut sandbox missing `integrations` after the integration-layer move |
| Mutation sandbox follow-up fix | Completed | `python3 scripts/governance/check_mutation_scope.py && python3 scripts/governance/check_mutation_test_selection.py` + targeted governance pytest | PASS | `pyproject.toml` now copies `integrations/` into mutmut sandboxes, and governance checks accept the change |
| Root reports residue cleanup | Completed | inspect `reports/` + remove empty legacy subtree + rerun `python3 scripts/governance/check_root_allowlist.py --strict-local-private && ./bin/governance-audit --mode pre-push` | PASS | The old root-level `reports/` shell no longer blocks governance closure |
| Mutation sandbox root-link fix | Completed | `bash -n scripts/ci/run_mutmut.sh` + manual sandbox bootstrap smoke + targeted governance pytest | PASS | The mutation workspace now really links `integrations/` at the top level instead of only declaring it in config |
| Legacy release/docs path cleanup | Completed | targeted pytest + `python3 scripts/governance/render_docs_governance.py --check` + isolated `verify_db_rollback_readiness.py` smoke | PASS | `verify_db_rollback_readiness.py` now writes release drill state under `artifacts/releases/`, and docs governance reads `artifacts/release-readiness/ci-kpi-summary.json` instead of reviving root `reports/` |
| Strict-ci rerun after mutation/root fixes | Completed | `./bin/strict-ci --debug-build --mode pre-push --strict-full-run 1 --ci-dedupe 0` | PASS | Fresh standard-env debug-build evidence now passes through short checks, long tests, mutation, api-real-smoke-local, and final root dirtiness on the current workspace |

## Risk / Blocker Log

| Time | Type | Description | Impact | What Can Continue | Resolution Condition |
| :- | :- | :- | :- | :- | :- |
| 2026-03-15 06:07:57 | Risk | Current worktree already contains extensive governance refactor changes not authored in this step | Any overwrite or revert could destroy in-flight governance work | Additive hardening around existing direction | Only apply targeted patches with local context reads |
| 2026-03-15 06:07:57 | Resolved | Adding `.agents` and `bin` would violate current root allowlist and budget unless control plane changed in the same batch | Would have broken root gates | Resolved in batch 1 | Root allowlist, budget, and semantic cleanliness now all pass |
| 2026-03-15 06:10:40 | Resolved | `bin/*` wrappers initially lacked executable bits and wiring | Public entrypoint hard cut would have remained cosmetic | Resolved in batch 1 | `chmod +x` applied, hooks/workflows/docs/tests updated, help paths updated |
| 2026-03-15 06:16:00 | Resolved | Bridge registry pointed to `.runtime-cache/tmp` before runtime outputs control plane allowed it | Governance audit failed on an undeclared runtime child | Resolved in batch 1 | `tmp` is now a declared governed bridge subdir |
| 2026-03-15 06:18:00 | Resolved | A plain `uv run pytest` created a root `.venv` during validation | Root cleanliness was violated by the validation path itself | Resolved for current validation batch | Clean validation now uses `PYTHONDONTWRITEBYTECODE=1` and `UV_PROJECT_ENVIRONMENT=.runtime-cache/temp/pytest-governance-env` |
| 2026-03-15 06:23:00 | Blocker | `contracts/` hard cut and `integrations/` extraction remain broad shared-file moves on top of a heavily dirty worktree with many pre-existing governance edits | High risk of clobbering in-flight local refactors and leaving the repo in a half-migrated state | Further additive hardening and validation can continue in later sessions | Re-enter on a stabilized shared-file baseline or with explicit scope to carry the large-scale moves end-to-end |
| 2026-03-15 06:44:20 | Risk | Write-time metadata hardening is still partial; many runtime report/evidence writers remain outside the new helper path | Runtime maintenance is still doing some cleanup work that should eventually be unnecessary | Additional high-value writers can keep moving to the helper incrementally | Finish inventory of freshness-required writers and wire remaining hot paths |
| 2026-03-15 06:49:40 | Resolved | `bin/doctor` created `__pycache__` under `scripts/governance`, violating root/runtime cleanliness by using plain `python3` semantics | Would have made the official diagnosis entrypoint self-contradictory | Resolved in batch 2 | `bin/doctor` now exports `PYTHONDONTWRITEBYTECODE=1` and passes clean rerun validation |
| 2026-03-15 06:56:30 | Risk | The new coverage gate only audits script-side runtime report/evidence writers with recognizable direct write patterns; it does not yet prove every possible runtime artifact path across the whole repo is helper-backed | WS-04 is stronger but still not complete | Continue migrating deeper release/runtime writers and expand the gate if new patterns emerge | Finish writer inventory and add post-generation metadata completeness validation |
| 2026-03-15 07:05:10 | Risk | WS-05 currently guarantees that stable public entrypoints create run manifests, but it does not yet guarantee that every downstream log/report/evidence path is linked back to a manifest in a completeness gate | Correlation is better, but not yet final-form complete | Continue with manifest completeness validation and upstream channel planning | Add a manifest completeness gate that checks current-run artifacts against generated manifests |
| 2026-03-15 07:47:40 | Resolved | WS-05 previously had only a static manifest coverage gate, not a current-run completeness gate | Manifest foundations were good, but not yet sufficient for stronger correlation claims | Resolved in batch 6 | `check_run_manifest_completeness.py` now passes as part of governance audit after fresh manifest generation |
| 2026-03-15 07:19:20 | Resolved | `contracts/` hard cut was previously blocked because the worktree was too dirty for a safe shared-file migration | Would have made the contract move too risky earlier | Resolved in batch 4 | The repository baseline is clean enough and the contract move has now been completed with gate/test closure |
| 2026-03-15 07:19:20 | Mitigated | `integrations/` extraction was still a broad multi-surface migration across app logic, runtime scripts, CI scripts, and upstream governance surfaces | High risk of partial glue-layer duplication if forced too quickly | Mitigated by narrowing the first slice to media-binary command construction | Continue slicing the remaining upstream families incrementally instead of forcing a repo-wide glue rewrite in one jump |
| 2026-03-15 07:34:30 | Risk | WS-07 is now real, but only the media-binary family has moved; provider APIs, reader services, and runtime images are still distributed across worker/app/runtime/CI surfaces | The integration layer is no longer hypothetical, but it is not yet complete enough for a U4 verdict | Further slices can continue safely now that the pattern is proven | Extract the next upstream family with the same narrow-slice discipline |
| 2026-03-15 07:55:40 | Risk | WS-07 now has both a binary slice and a provider API slice, but reader services, provider health probes, and runtime image glue are still distributed across the old layers | The integration layer direction is now proven, but the remaining surfaces are still large enough to create duplication if rushed | Continue with narrow provider/reader slices | Choose the next family based on boundary clarity and test coverage, not on raw dependency count |
| 2026-03-15 09:12:00 | Resolved | `./bin/strict-ci --debug-build --mode pre-push --strict-full-run 1 --ci-dedupe 0` was previously blocked by Docker timing out even on `docker version` | Release-qualifying standard-env evidence could not be regenerated | Resolved with fresh Docker probes and a live strict-ci rerun reaching the mutation gate | Docker is responsive again; closure is no longer blocked by stale infrastructure timeout evidence |
| 2026-03-15 09:30:40 | Risk | The latest strict-ci rerun had not yet been repeated after the actual mutmut shell-wiring fix, so the mutation-gate repair was not proven end-to-end in standard-env strict-ci | Closure was closer, but not yet fully re-proved | Repo-side governance work and mutation config checks could continue | A fresh rerun has now started on the updated mutation sandbox wiring; keep watching for its real outcome |
| 2026-03-15 09:39:30 | Resolved | A stale empty `reports/` subtree at root was still tripping terminal governance even though long-lived artifacts had already moved to `artifacts/` | strict-ci and governance pre-push were blocked by a migration shell, not a live governance defect | Resolved in closure follow-up | Root hallway no longer contains the legacy `reports/` shell |
| 2026-03-15 09:39:30 | Resolved | The fresh strict-ci rerun was still in progress, so closure could not yet claim final standard-env pass or name the next true first failure after long-tests | Final closure evidence was still being minted | Other read-only inspection or control-board maintenance could continue | Resolved once the rerun completed end-to-end on the updated workspace |
| 2026-03-15 15:03:28 | Resolved | Two stale release/docs defaults still pointed at root `reports/`, which could silently re-create a now-illegal top-level hallway even after the empty shell was removed | Root cleanliness could regress from future release-readiness or docs-governance execution paths | Targeted governance tests and root/governance checks could continue while the defaults were corrected | `verify_db_rollback_readiness.py` and `render_docs_governance.py` now point at `artifacts/`, root `reports/` is gone again, and fresh strict-ci passes end-to-end |

## Files Changed Log

| Time | Files / Paths Changed Since Last Update |
| :- | :- |
| 2026-03-15 06:07:57 | `.agents/Plans/2026-03-15_06-07-57__repo-governance-final-form-execution-plan.md` created |
| 2026-03-15 06:10:40 | `bin/*` wrappers created; `config/governance/bridges.json` created; `scripts/governance/check_bridge_expiry.py` created |
| 2026-03-15 06:14:00 | Root governance control plane updated for `.agents` / `bin`; hooks and key workflows moved to `bin/*`; active top-level and module docs repointed; workflow strictness checks and targeted tests updated |
| 2026-03-15 06:18:00 | `scripts/governance/common.py` hardened for out-of-repo temp artifacts; governance tests updated for versioned config evolution; `.runtime-cache/tmp` legalized as a governed bridge subdir |
| 2026-03-15 06:22:00 | Added `bin/clean-runtime`, `bin/prune-runtime`, `bin/doctor`; updated public help/usage strings to advertise `bin/*` instead of leaking internal `scripts/*` paths |
| 2026-03-15 06:44:20 | Added managed runtime artifact helpers in `scripts/governance/common.py`; migrated key report writers and smoke diagnostics JSON writers to write-time metadata-backed paths |
| 2026-03-15 06:49:40 | `bin/doctor` hardened to suppress repo-side bytecode residue; validation rerun confirmed no lingering `__pycache__` under `apps/` or `scripts/` |
| 2026-03-15 06:56:30 | `scripts/ci/collect_kpi.py` and `scripts/release/build_readiness_report.py` migrated to managed artifact helpers; added `scripts/governance/check_runtime_artifact_writer_coverage.py`; wired the new gate into governance control plane and evidence docs |
| 2026-03-15 07:05:10 | Added `scripts/runtime/entrypoint.sh`, `scripts/runtime/write_run_manifest.py`, and `scripts/governance/check_public_entrypoint_manifests.py`; wired stable `bin/*` entrypoints to emit run manifests before handoff |
| 2026-03-15 07:19:20 | Moved active contract source and generated schema surfaces from `packages/shared-contracts` into `contracts/`; removed the old packages tree; rewired workflows, docs, gates, tests, module ownership, and dependency-boundary policy to the new contract root |
| 2026-03-15 07:34:30 | Migrated root `reports/` contents into `artifacts/`; added `artifacts/README.md`; rewired release/readiness/performance paths; introduced `integrations/` and extracted media binary command construction into `integrations/binaries/media_commands.py` |
| 2026-03-15 07:47:40 | Added `scripts/governance/check_run_manifest_completeness.py`; wired it into governance audit, docs, and governance tests; adjusted entrypoint bootstrap to emit a first log event so fresh manifests point at real log files |
| 2026-03-15 07:55:40 | Added `integrations/providers/resend.py`; rewired API notification service and worker email activity helpers into thin wrappers over the integration module; updated dependency policy to allow API access to `integrations.` |
| 2026-03-15 09:16:00 | Updated `scripts/governance/check_upstream_compat_freshness.py`, `config/governance/upstream-compat-matrix.json`, and `docs/reference/upstream-compatibility-policy.md` so only rows that really have fresh runtime receipts claim `verified`; revalidated governance audit and captured the external Docker timeout blocker |
| 2026-03-15 09:30:40 | Captured fresh Docker responsiveness evidence; reproduced strict-ci far enough to replace the stale Docker blocker with a concrete mutation-sandbox failure; updated mutmut `also_copy` to include `integrations/` and documented the change in dependency governance and governance tests |
| 2026-03-15 09:39:30 | Removed the stale root `reports/` migration shell after confirming `artifacts/` already holds long-lived files; reran governance pre-push successfully; started a fresh strict-ci rerun that is now beyond short-checks |
| 2026-03-15 09:54:40 | Patched `scripts/ci/run_mutmut.sh` so the mutation workspace symlinks `integrations/`; lightly verified the wiring with sandbox inspection and governance pytest; launched a fresh strict-ci rerun on the updated shell wiring |
| 2026-03-15 09:47:20 | Patched `scripts/ci/run_mutmut.sh` so the mutation workspace symlinks `integrations/`; lightly verified the fix with sandbox inspection, mutation governance guards, and targeted governance pytest |
| 2026-03-15 15:03:28 | Repointed stale release/docs defaults from root `reports/` to `artifacts/` in `verify_db_rollback_readiness.py` and `render_docs_governance.py`; added regression assertions; removed the empty legacy `reports/` shell again; revalidated targeted governance tests, docs governance, root/governance gates, and fresh end-to-end strict-ci |

## Next Actions

1. Continue WS-07 with the next narrow extraction slice, prioritizing one reader/provider-health family rather than a repo-wide glue rewrite.
2. Finish the remaining WS-04 helper coverage on deeper release/runtime writers.
3. Add an explicit `upstreams` log channel usage plan once the next integration slice lands.
4. Keep this file current before any later structural batch starts.

## Final Completion Summary

Batch 1 completed and verified:

- Landed the in-repo execution control board under `.agents/Plans/`.
- Added stable public `bin/*` entrypoints and moved active hooks, workflows, docs, and workflow-governance tests to them.
- Legalized `.agents` and `bin` in root allowlist, budget, and semantic cleanliness rules.
- Added bridge registry + bridge expiry gate and wired the gate into governance audit.
- Added `bin/doctor`, `bin/prune-runtime`, and `bin/clean-runtime` to start turning final-form operational commands into stable public entrypoints.
- Closed the two real validation regressions discovered during execution:
  - root `.venv` pollution from plain `uv run pytest`
  - undeclared `.runtime-cache/tmp` bridge target
- Verified the batch with root/runtime checks, governance audit, doctor, wrapper help, and targeted pytest.

Remaining workstreams are not marked complete. `WS-06` and `WS-07` are explicitly blocked because the required repo-wide `contracts/` and `integrations/` hard cuts would be unsafe to force on top of the current heavily dirty shared-file worktree without a cleaner migration baseline.

Batch 2 progress completed and verified:

- Added reusable managed artifact helpers in `scripts/governance/common.py`.
- Moved several high-value Python runtime report writers to write-time metadata helpers.
- Moved two key smoke diagnostics JSON writers to the same helper discipline.
- Fixed `bin/doctor` so the official diagnosis entrypoint no longer leaves bytecode residue in source directories.
- Added a runtime artifact writer coverage gate so the remaining WS-04 surface is machine-audited rather than memory-driven.
- Verified shell syntax, helper-backed script importability, runtime cache freshness report execution, clean `bin/doctor` execution, the new coverage gate, and the targeted governance/workflow pytest suite.

Batch 3 progress completed and verified:

- Added a run-manifest bootstrap layer for stable public `bin/*` entrypoints.
- Added a static public-entrypoint manifest coverage gate and wired it into governance control plane and evidence docs.
- Verified that public entrypoints now emit `.runtime-cache/run/manifests/<run_id>.json` without leaving bytecode residue.

WS-05 is no longer “not started”; it now has a concrete run-manifest-first foundation. It remains incomplete because there is not yet a stronger manifest completeness gate for current-run logs/reports/evidence, and there is not yet an upstream-specific logging channel plan.

Batch 4 progress completed and verified:

- Hard-cut the active contract root from `packages/shared-contracts` to `contracts/`.
- Split handwritten contract source and generated schema surfaces into `contracts/source` and `contracts/generated/jsonschema`.
- Rewired active workflows, docs, gates, tests, module ownership, and dependency-boundary policy to the new contract paths.
- Removed the legacy `packages/shared-contracts` tree after validation.

WS-06 is now effectively complete for the active contract root migration.

Batch 5 progress completed and verified:

- Migrated the root long-lived `reports/` tree into `artifacts/`, reducing the root hallway’s semantic conflict.
- Added `artifacts/README.md` so the new long-lived artifact room is explicit and documented.
- Introduced the root-level `integrations/` layer and completed the first narrow extraction slice for media binaries.
- Rewired worker media steps to consume `integrations/binaries/media_commands.py` instead of building upstream binary commands inline.

WS-07 is no longer “blocked and untouched”; it is now in progress with one proven narrow slice. The remaining structural blocker is not “whether” to build the integration layer, but how many additional upstream families can be safely extracted per batch without duplicating glue across old and new surfaces.

Batch 6 progress completed and verified:

- Added a current-run manifest completeness gate on top of the earlier public-entrypoint manifest coverage gate.
- Adjusted the entrypoint bootstrap so fresh manifests always point at a real log file, not an empty path.
- Verified that fresh public-entrypoint manifests now resolve to real logs and indexed runtime artifacts.

WS-05 is now materially stronger: it has both entrypoint coverage and current-run completeness. The remaining logging-correlation gap is the lack of an explicit upstream-specific log channel and richer provider failure attribution.

Batch 7 progress completed and verified:

- Added a second explicit integration slice for the Resend provider.
- Moved provider request construction, sanitization, HTML rendering, and idempotency-header handling into `integrations/providers/resend.py`.
- Kept API and worker call surfaces stable by turning them into thin wrappers over the integration module.
- Verified the slice with targeted API + worker tests and a full governance audit pass.

WS-07 is now more than a proof of concept: it has one binary slice and one provider API slice. The remaining work is to keep extending this pattern to reader services, provider health probes, and runtime image glue until the distributed integration logic is gone.

WS-04 remains in progress because the repository still contains additional freshness-required report/evidence writers that have not yet been migrated to the helper path.

Batch 8 closure-integrity progress completed and verified:

- Re-audited the live `main` workspace instead of relying on older chat-only closure claims.
- Repaired the mismatch between the upstream compatibility matrix and the freshness gate: only rows that truly have fresh runtime receipts now remain `verified`.
- Downgraded blocker-chain rows without fresh local runtime receipts to `pending` instead of letting the repo claim evidence it does not currently possess.
- Re-validated governance audit, env contract, and governance pytest from the live clean baseline.
- Reconfirmed git closure before the new closure commit: one branch, one worktree, no open PRs, and `main` aligned with `origin/main`.

Batch 9 validation closure completed and verified:

- Repointed the last stale release/docs defaults that could recreate root `reports/` back to the governed `artifacts/` tree.
- Added regression assertions so release rollback readiness and docs-governance rendering both fail closed if they drift back to root `reports/`.
- Removed the reappeared empty `reports/` shell and revalidated root/governance gates immediately after cleanup.
- Re-proved the current dirty workspace with a fresh `./bin/strict-ci --debug-build --mode pre-push --strict-full-run 1 --ci-dedupe 0` pass, including mutation, api-real-smoke-local, and final root dirtiness.

This batch still does **not** declare the entire Final Form program finished. WS-04 still has deeper runtime writer coverage work, WS-07 still has more upstream families to extract into `integrations/`, and WS-08 still has historical/generated doc surfaces to finish cleaning up. What is now closed is the current validation frontier: the present workspace once again has a fresh end-to-end strict-ci pass instead of a lingering closure question mark.
