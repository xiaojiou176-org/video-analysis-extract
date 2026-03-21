# Newcomer Clean-Room Receipt

This document is not an onboarding summary. Think of it as an **execution receipt**: for the fresh run listed below, it shows which official newcomer steps really ran and which ones did not.

The wording here must stay honest:

- This repository is publicly presented as **public source-first + limited-maintenance**, not as a one-command commercial product.
- This receipt only proves that the **minimum try-it path** produced a fresh receipt for the run captured below. It does not prove that the full-stack or operator paths were freshly rerun.
- Heavier repo-side strict and external-lane acceptance still require their own independent receipts. This page must not be used as a substitute.

## What This Receipt Proves

- **Freshly proved**: the newcomer shortest path documented in `docs/start-here.md`, `./bin/validate-profile --profile local`, ran successfully on the source commit listed below and produced a receipt.
- **Not freshly proved**: `./bin/full-stack up`, `./bin/smoke-full-stack`, `./bin/api-real-smoke-local`, `./bin/repo-side-strict-ci ...`, and `./bin/strict-ci ...`.

Put more plainly: this is like confirming that the key matches the front door. It does **not** prove that the full kitchen, plumbing, and ventilation have all been turned on and checked.

## Sources Of Truth

- Official newcomer entrypoint: `docs/start-here.md`
- Operator runbook: `docs/runbook-local.md`
- Public/source-first boundary: `docs/reference/public-repo-readiness.md`
- Shortest-path entry script: `bin/validate-profile`
- Actual executed script: `scripts/env/validate_profile.sh`
- Machine-readable status page: `docs/reference/newcomer-result-proof.md`

## Fresh Run Stamp

This section records the **receipt source**, not a forever-current status for every future commit. For the live reading, still defer to the runtime report pointed to by `docs/reference/newcomer-result-proof.md`.

| Field | Value |
| --- | --- |
| Date | 2026-03-16 America/Los_Angeles |
| Approximate time | 22:59 PDT |
| Commit | `c7ddaed526671b927396063f2812978b9a739a15` |
| Command | `./bin/validate-profile --profile local` |
| Exit code | `0` |
| Duration | `0.42s` |

## Environment Preconditions

This newcomer shortest path has a lower bar than full-stack startup. The observed prerequisites were:

- the repository-shipped `env/core.env.example`
- `env/profiles/local.env`
- `python3` plus the ability to run repository scripts
- **`.env` was missing during this run**, but the command still passed; the script reported that as a `risk hint` instead of pretending the machine already had a full runnable setup
- this path does **not** require Docker, PostgreSQL, or Temporal to be started first, and it does not prove those dependencies are available

## Exact Commands

```bash
./bin/validate-profile --profile local
python3 scripts/governance/render_newcomer_result_proof.py
```

The second command is not the official newcomer entrypoint itself. It only renders the fresh result into a machine-readable proof bundle for later integrator use.

## Actual Artifacts

### 1. Resolved env snapshot

Path:

- `.runtime-cache/tmp/.env.local.resolved`

Observed content summary for this run:

```dotenv
ENV_PROFILE=local
```

Interpretation:

- This proves that the profile composition at least produced a resolved env file.
- But only **one key** was resolved, so this is better read as proof that profile composition still works, not proof that the application runtime configuration is fully populated.

### 2. Run manifest

Path:

- `.runtime-cache/run/manifests/20d2fb35724d4aa89de9f46b04012bff.json`

Key field summary:

- `entrypoint=validate-profile`
- `channel=governance`
- `run_id=20d2fb35724d4aa89de9f46b04012bff`
- `argv=["--profile","local"]`
- `repo_commit=c7ddaed526671b927396063f2812978b9a739a15`
- `log_path=.runtime-cache/logs/governance/20d2fb35724d4aa89de9f46b04012bff.jsonl`

### 3. Newcomer result proof JSON

Path:

- `.runtime-cache/reports/governance/newcomer-result-proof.json`

Fresh reading summary for this run:

- `newcomer_preflight=status=pass`
- `repo_side_strict_receipt=status=missing_current_receipt`
- `governance_audit_receipt=status=missing`

Together, those three states mean:

- the **minimum try-it path** is freshly proved
- the heavier **repo-side strict receipt** is still missing a fresh PASS receipt for this commit
- the **governance audit receipt** was not freshly captured in the same run

## Observed Limits And Failure Points

### Limits that were actually observed

- `validate-profile` printed `risk hint: .env is missing; validation passed with available files only.`
- In other words, this path does not prove that `.env` is already prepared, and it definitely does not prove that API, Worker, Web, or Reader can start

### Script-level fail-fast points for this path

Based on the real logic in `scripts/env/validate_profile.sh`, this newcomer path will fail immediately if:

- `env/profiles/<profile>.env` is missing
- `compose_env.sh` fails while composing env files
- the resolved env file is empty
- no usable env file can be found at all

## How It Differs From The Full Full-Stack Path

This is the part most likely to be misunderstood, so it is written out separately.

### Minimum try-it path

Command:

```bash
./bin/validate-profile --profile local
```

What it proves:

- the newcomer entrypoint is not stale documentation
- the local profile can still be composed by the scripts
- the current HEAD still has at least one low-bar fresh entrypoint

What it does **not** prove:

- `.env` already exists and is complete
- Docker or DevContainer are available
- PostgreSQL or Temporal are available
- API, Worker, and Web can start
- smoke, real smoke, or strict-ci have freshly passed

### Full operator / full-stack path

Reference commands:

```bash
./bin/bootstrap-full-stack
./bin/full-stack up
./bin/smoke-full-stack
./bin/api-real-smoke-local
./bin/repo-side-strict-ci --mode pre-push --strict-full-run 1 --ci-dedupe 0
```

Those are the commands that move toward the real "cook the meal and serve it" path. They require a higher operator bar and depend more heavily on the standard environment, infrastructure, and external conditions.

## Operator-Bar Reminder

If this is your first time touching the repository, the safest reading is:

- this is not a lightweight toy project, so do not treat it like a clone-and-open app
- the newcomer shortest path is a **configuration and entrypoint truth check**
- the full-stack/operator path is the actual **runtime and acceptance chain**
- strict acceptance is still split into `repo-side` and `external lane`, and this receipt does not currently prove either one end to end

## Reviewer Checklist

If a reviewer wants to tell whether this page is grounded in a real run instead of copied boilerplate, they should be able to find:

- the **current commit**
- the **fresh command**
- the **exit code and duration**
- the **real runtime artifact paths**
- an explicit note that **`.env` was missing but the command still passed**
- a clear separation between the **minimum try-it path** and the **full full-stack path**
- no attempt to disguise missing strict or governance receipts as a pass
