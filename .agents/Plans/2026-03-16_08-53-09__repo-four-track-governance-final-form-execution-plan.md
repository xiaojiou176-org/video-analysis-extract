# Repo Four-Track Governance Final-Form Execution Plan

## Header

- Created At: 2026-03-16 08:53:09 America/Los_Angeles
- Plan Role: single source of truth for this execution run
- Repo Position: high-maturity hybrid-repo, strong control plane, not yet truthfully final-form green
- Current Phase: Phase F - second-wave high-signal/value/integration hard-cuts finished and validated
- Current Workstream: plan closure / remaining external-only or larger-scope next-wave items

## Objective

Turn the repo from "strong but still carrying completion illusion" into "current-proof-verifiable and public-boundary-consistent".

This run must:

1. Remove the live public-surface policy contradiction.
2. Prevent historical green receipts from being consumed as current HEAD verdict proof.
3. Align docs, gates, and public narrative with repo-side vs external-lane truth.
4. Execute every structural action that is locally completable in this workspace.

## Score Targets / Target State

| Dimension | Current | Target For This Run |
| --- | --- | --- |
| Repo-side governance verdict | red due to public-surface contradiction | fresh green or clearly narrowed residual blocker |
| Public surface governance | contradictory policy | one coherent enforced rule |
| Current-proof semantics | stale/current can be mixed by readers | canonical gate rejects stale commit proof consumption |
| Done-model semantics | repo-side vs external split exists but needs stronger consumption discipline | docs and gates say the same thing and enforce the same thing |
| Open-source boundary | public/source-first but not high-confidence | narrower, more honest, less misreadable |
| Hiring/project signal | strong engineering, overclaim risk remains | stronger truthfulness and lower completion illusion |
| Third-party rights ledger | absent | machine-rendered public notices + tracked inventory + gate |
| AI regression thickness | 2 deterministic cases | 20 deterministic cases with broader repo-side coverage |
| Value proof | positioning-only narrative | tracked task-level baseline/value proof page |
| Gemini integration boundary | scattered direct SDK imports in runtime code | runtime code imports Gemini SDK through `integrations/providers/gemini.py` |

## Current Status

- Former live blocker resolved in source and validation: public-surface policy now uses explicit allowlisted tracked sample semantics and passes its checker.
- Former live illusion source narrowed: canonical current-proof lane is now machine-checked; stale external/current artifacts were refreshed to current HEAD.
- Confirmed existing repo worktree drift not created by this run: `apps/worker/tests/test_full_stack_env_runtime_regression.py` modified.
- Confirmed task board absence: no `.agent/TASK_BOARD-*.md` or `.agents/TASK_BOARD-*.md`.
- Third-party rights ledger is now present as tracked artifacts: `THIRD_PARTY_NOTICES.md` + `artifacts/licenses/third-party-license-inventory.json`.
- AI repo-side eval golden set now contains 20 deterministic cases and the regression gate is passing on a fresh report.
- Runtime Gemini SDK imports in `apps/` code have been pulled behind `integrations/providers/gemini.py`; direct runtime imports in app code no longer remain.
- Value-proof narrative now exists as a first-class repo doc and is linked from project positioning.

## Workstream Table

| ID | Workstream | Goal | Key Objects | Validation |
| --- | --- | --- | --- | --- |
| WS2 | Public surface hard-cut | remove policy/doc/sample contradiction | `config/governance/public-surface-policy.json`, `docs/reference/public-artifact-exposure.md`, `scripts/governance/check_public_surface_policy.py` | `python3 scripts/governance/check_public_surface_policy.py`, `./bin/governance-audit --mode audit` |
| WS4 | Current-proof hardening | block stale commit proof from current verdict | governance/release check scripts, generated docs inputs, current-proof checker | new current-proof gate + governance audit |
| WS3 | Done-model/docs alignment | align repo-side vs external-lane semantics | `docs/reference/done-model.md`, generated external/release docs, referenced status docs | docs governance check + targeted grep/readback |
| WS10 | External proof lane narrowing | make ready/in_progress semantics non-overclaiming | external lane docs and contracts | targeted docs/readback; full remote verify only if locally completable |
| WS13 | Third-party rights ledger | turn license inventory gap into generated tracked evidence | `scripts/governance/render_third_party_notices.py`, `THIRD_PARTY_NOTICES.md`, `artifacts/licenses/third-party-license-inventory.json` | generation check + governance audit |
| WS14 | AI regression thickening | expand repo-side eval from minimum existence to broader regression coverage | `evals/golden-set.sample.jsonl`, eval docs, regression output | `run_regression.py`, `check_eval_regression.py`, `check_eval_assets.py` |
| WS15 | Value proof hardening | turn value narrative into task-level evidence surface | `docs/reference/value-proof.md`, `docs/reference/project-positioning.md` | docs check + manual readback |
| WS16 | Gemini adapter convergence | move runtime SDK imports behind integration layer | `integrations/providers/gemini.py`, worker/api runtime call sites | targeted pytest + grep for residual runtime imports |

## Task Checklist

- [x] Create dynamic execution plan in `.agents/Plans/`
- [x] Fix public-surface policy contradiction in policy/doc/checker source
- [x] Re-run public-surface policy check
- [x] Design and wire current-proof gate into canonical governance path
- [x] Update done-model / external proof wording so docs cannot overclaim
- [x] Re-run canonical governance audit
- [x] Add machine-rendered third-party rights ledger and gate it
- [x] Repair tmp-runtime cleanup semantics uncovered during execution
- [x] Expand repo-side eval golden set and refresh regression proof
- [x] Add task-level value proof surface and connect it to project positioning
- [x] Converge runtime Gemini SDK imports behind the integration layer
- [x] Update plan with validation results, blockers, changed files, and next actions

## Decision Log

| Time | Decision | Why | Rejected Alternative |
| --- | --- | --- | --- |
| 2026-03-16 08:53:09 | Use a new execution plan file instead of reusing older plans | this run has a new source-of-truth synthesis and must keep its own state ledger | editing an older plan would blur prior execution states |
| 2026-03-16 08:53:09 | Start with public-surface contradiction before proof hardening | it is the current canonical blocker and changes repo-side truth immediately | starting with README/public copy would preserve the live red gate |
| 2026-03-16 08:53:09 | Resolve the TSV conflict through explicit allowlist semantics instead of deleting the sanitized sample | the sample itself is synthetic/public-safe; the bug is policy enforcement ambiguity | deleting the sample would hide the contract bug instead of fixing it |
| 2026-03-16 08:53:09 | Add a dedicated current-proof alignment gate | human-only `.meta.json` reading is too weak; the repo must reject stale current-state proof automatically | relying on documentation alone would preserve completion illusion |
| 2026-03-16 09:10:00 | Narrow the current-proof contract to true canonical current-state artifacts and exclude `quality-gate-summary` from the blocking set | `quality-gate-summary` is valuable evidence but not a canonical current-state source consumed by repo-side/docs truth; keeping it in the blocking set creates a self-refresh cycle | forcing summary freshness through the same gate would deadlock pre-commit regeneration |
| 2026-03-16 09:12:00 | Keep GHCR readiness artifact in the current-proof contract even when it blocks | a truthful blocked current artifact is better than a hanging or stale pseudo-ready artifact | dropping GHCR readiness from the contract would preserve external-lane illusion |
| 2026-03-16 09:20:00 | Implement third-party notices as generated tracked artifacts, not handwritten markdown | a handwritten notices file would recreate the same false-maturity problem we just removed elsewhere | a one-off manual NOTICE would drift immediately |
| 2026-03-16 09:27:00 | Move temporary uv environments under `.runtime-cache/tmp/` and auto-clean them after inventory generation | root governance explicitly forbids root `.venv`; the inventory generator must obey the same runtime-output law as the rest of the repo | leaving `.venv` or long-lived tmp envs behind would make the new ledger fail root/runtime governance |
| 2026-03-16 09:31:00 | Fix tmp retention semantics at the root cause instead of manually deleting oversized buckets | `tmp` retention was effectively broken because files were treated as newly created on every maintenance run | manual deletion alone would not stop the budget red from coming back |
| 2026-03-16 09:45:00 | Keep eval thickening repo-side and deterministic instead of jumping straight to provider-heavy live eval | the current user value is better served by stronger regression confidence before external cost expansion | switching to live eval first would add cost and noise before strengthening the local decision surface |
| 2026-03-16 09:47:00 | Converge Gemini runtime imports through the integration layer without breaking test monkeypatch contracts | integration convergence is valuable, but existing test seams are part of the repo contract | a pure refactor that breaks monkeypatch seams would create fake maturity by weakening verification |

## Validation Log

| Check | Status | Method | Result | Notes |
| --- | --- | --- | --- | --- |
| Task board presence | PASS | root glob probe | no task board files found | safe to proceed without board intake |
| Public-surface contradiction existence | PASS | read policy + docs + checker | contradiction confirmed | live blocker |
| Existing plan directory | PASS | filesystem probe | `.agents/Plans/` exists | used for this run |
| Structural source patch bundle | PASS | source edits landed | policy/checker/docs/gate source patched | command validation pending |
| Public-surface policy | PASS | `python3 scripts/governance/check_public_surface_policy.py` | PASS | contradiction removed from live gate path |
| Generated docs refresh | PASS | `python3 scripts/governance/render_docs_governance.py` | PASS | generated docs re-synced after render-rule change |
| Docs governance | PASS | `python3 scripts/governance/check_docs_governance.py` | PASS | docs truth stayed consistent after hard-cut |
| Current-proof alignment | PASS | `python3 scripts/governance/check_current_proof_commit_alignment.py` | PASS (5 artifacts) | stale current-state artifact consumption now machine-blocked |
| Canonical governance gate | PASS | `./bin/governance-audit --mode audit` | PASS | repo-side governance returned to fresh green |
| Quality gate | PASS | `bash scripts/governance/quality_gate.sh --mode pre-commit` | PASS | pre-commit path accepts the new hard-cuts |
| GHCR readiness artifact refresh | PASS | `./scripts/ci/check_standard_image_publish_readiness.sh` | FAIL with current blocked artifact, not stale/hanging | external lane now yields truthful current blocked proof |
| Third-party notices render | PASS | `python3 scripts/governance/render_third_party_notices.py` | rendered tracked notices + inventory | rights ledger is now machine-produced |
| Third-party notices gate | PASS | `python3 scripts/governance/render_third_party_notices.py --check` | PASS | rights ledger is now governed, not decorative |
| Runtime tmp maintenance | PASS | `bash scripts/runtime/run_runtime_cache_maintenance.sh --apply --subdir tmp` | PASS after retention fix | tmp budget restored under governance |
| Eval asset count | PASS | `python3 scripts/governance/check_eval_assets.py` | PASS (cases=20) | repo-side eval is no longer the 2-case minimum |
| Eval regression | PASS | `python3 scripts/evals/run_regression.py`; `python3 scripts/governance/check_eval_regression.py` | PASS (`pass_rate=0.95`) | thicker eval still satisfies the repo-side baseline |
| Gemini adapter convergence | PASS | `UV_PROJECT_ENVIRONMENT="$PWD/.runtime-cache/tmp/uv-project-env-tests" uv run python -m pytest ...` | PASS (54 passed) | runtime Gemini call sites now share the integration helper |
| Runtime direct-import scan | PASS | `rg` over `apps/api/app` + `apps/worker/worker` | no runtime `google.genai` direct imports remain | adapter convergence is real, not cosmetic |

## Risk / Blocker Log

| Type | Status | Detail | Impact | Next Handling |
| --- | --- | --- | --- | --- |
| blocker | closed | public-surface policy contradiction | canonical governance gate no longer red on this cause | fixed and validated |
| structural | closed | stale/current proof can be mixed by human readers | current-proof gate now blocks stale canonical artifacts | fixed and validated |
| workspace-drift | open | unrelated modified test file already exists | avoid overwriting user changes | do not touch unless required |
| external | open | GHCR standard-image readiness remains blocked by local `docker buildx inspect` timeout | external lane still not verified; current artifact is truthful but blocked | keep as honest external-lane blocker unless deeper local fix is pursued |
| next-wave | open | provider-heavy live eval, broader value proof beyond repo docs, and deeper external adapter/publish closure still remain | these are larger next-wave upgrades, not quick hard-cuts | keep as explicit follow-on workstreams, not implied closure |

## Files Changed Log

| Time | File | Change |
| --- | --- | --- |
| 2026-03-16 08:53:09 | `.agents/Plans/2026-03-16_08-53-09__repo-four-track-governance-final-form-execution-plan.md` | created dynamic execution control board |
| 2026-03-16 08:53:09 | `config/governance/public-surface-policy.json` | added explicit allowlisted tracked sample semantics |
| 2026-03-16 08:53:09 | `scripts/governance/check_public_surface_policy.py` | enforced allowlist-aware public surface checks |
| 2026-03-16 08:53:09 | `docs/reference/public-artifact-exposure.md` | aligned public artifact docs with explicit allowlist semantics |
| 2026-03-16 08:53:09 | `config/governance/current-proof-contract.json` | introduced canonical current-proof artifact ledger |
| 2026-03-16 08:53:09 | `scripts/governance/check_current_proof_commit_alignment.py` | added stale/current commit alignment gate |
| 2026-03-16 08:53:09 | `scripts/governance/gate.sh` | wired current-proof gate into governance audit |
| 2026-03-16 08:53:09 | `docs/reference/done-model.md` | tightened repo-side/external proof semantics |
| 2026-03-16 08:53:09 | `docs/reference/external-lane-status.md` | tightened current-state reading rules |
| 2026-03-16 08:53:09 | `scripts/governance/render_docs_governance.py` | tightened generated current-proof wording |
| 2026-03-16 09:10:00 | `config/governance/current-proof-contract.json` | narrowed blocking scope to true canonical current-state artifacts |
| 2026-03-16 09:10:00 | `scripts/ci/check_standard_image_publish_readiness.sh` | hardened timeout cleanup and removed unregistered env contract drift |
| 2026-03-16 09:12:00 | `docs/generated/external-lane-snapshot.md` | regenerated from updated render rules |
| 2026-03-16 09:12:00 | `docs/generated/release-evidence.md` | regenerated from updated render rules |
| 2026-03-16 09:20:00 | `scripts/governance/render_third_party_notices.py` | added generated third-party rights ledger pipeline |
| 2026-03-16 09:20:00 | `THIRD_PARTY_NOTICES.md` | generated machine-readable public rights ledger summary |
| 2026-03-16 09:20:00 | `artifacts/licenses/third-party-license-inventory.json` | generated tracked Python/Web runtime license inventory |
| 2026-03-16 09:20:00 | `config/governance/root-allowlist.json` | registered `THIRD_PARTY_NOTICES.md` as a legal root public asset |
| 2026-03-16 09:20:00 | `docs/reference/root-governance.md` | documented third-party notices as governed root legal surface |
| 2026-03-16 09:27:00 | `scripts/runtime/prune_runtime_cache.py` | fixed tmp retention age semantics so maintenance can actually prune stale tmp data |
| 2026-03-16 09:27:00 | `scripts/governance/check_root_semantic_cleanliness.py` | recognized `THIRD_PARTY_NOTICES.md` as a conventional root legal doc |
| 2026-03-16 09:45:00 | `evals/golden-set.sample.jsonl` | expanded deterministic repo-side eval set from 2 to 20 cases |
| 2026-03-16 09:45:00 | `docs/reference/ai-evaluation.md` | documented thicker repo-side eval coverage |
| 2026-03-16 09:45:00 | `docs/reference/value-proof.md` | added task-level baseline/value proof surface |
| 2026-03-16 09:45:00 | `docs/reference/project-positioning.md` | linked value proof and made value evidence explicit |
| 2026-03-16 09:47:00 | `integrations/providers/gemini.py` | turned Gemini provider helper into a reusable SDK/client integration seam |
| 2026-03-16 09:47:00 | `apps/worker/worker/pipeline/steps/llm_client.py` | moved runtime Gemini SDK loading through integration helper |
| 2026-03-16 09:47:00 | `apps/worker/worker/pipeline/steps/embedding.py` | moved runtime Gemini embedding SDK/client through integration helper |
| 2026-03-16 09:47:00 | `apps/api/app/services/retrieval.py` | converged Gemini embedding imports/client creation behind integration helper while preserving test seam |
| 2026-03-16 09:47:00 | `apps/api/app/services/ui_audit.py` | converged Gemini UI audit runtime imports/client creation behind integration helper |
| 2026-03-16 09:47:00 | `apps/api/app/services/computer_use.py` | converged Gemini computer-use runtime imports/client creation behind integration helper |

## Next Actions

1. If continuing immediately, start the next-wave structural items in this order: provider-heavy live eval -> broader user-result evidence beyond repo docs -> deeper external publish/buildx repair.
2. Keep the GHCR readiness blocker recorded as truthful blocked state unless a deeper local buildx/runtime fix path is intentionally taken on.
3. Do not claim open-source adoption-grade or final-form high-signal project closure until the next-wave items above are actually executed.

## Final Completion Summary

Locally-completable governance and second-wave high-signal/value wave completed.

Completed in this run:

1. Public-surface policy contradiction removed at source, docs, and checker layers.
2. Current-proof alignment contract and gate introduced, refreshed, and driven to PASS.
3. Repo-side canonical governance gate restored to fresh PASS.
4. Pre-commit quality gate restored to PASS with the new hard-cuts in place.
5. GHCR readiness moved from stale/hanging ambiguity to truthful current blocked evidence.
6. Third-party rights ledger added as generated tracked artifacts plus a governance gate.
7. Root governance updated so the new legal surface is recognized as legitimate.
8. Tmp retention semantics fixed so runtime-cache maintenance can actually clear oversize tmp debt.
9. Repo-side eval expanded from 2 to 20 deterministic cases and refreshed to a passing current report.
10. Value proof is now a first-class tracked doc instead of an implicit talking point.
11. Runtime Gemini SDK use in app code now converges through the integration layer and is backed by passing targeted tests.

Still open after this run:

1. Unrelated pre-existing workspace drift in `apps/worker/tests/test_full_stack_env_runtime_regression.py`.
2. External GHCR lane remains blocked, though now truthfully reported on the current commit.
3. Provider-heavy live eval, broader user-result evidence outside repo docs, and deeper external publish/buildx repair remain next-wave work, not completed in this run.
