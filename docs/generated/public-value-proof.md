<!-- generated: docs governance control plane; do not edit directly -->

# Public Value Proof Entry

This tracked page is a pointer for public-safe value proof reading, not a current-run verdict page.

## Read In This Order

1. `docs/reference/value-proof.md`
2. `docs/proofs/task-result-proof-pack.md`
3. `.runtime-cache/reports/governance/newcomer-result-proof.json`
4. `.runtime-cache/reports/governance/current-state-summary.md`
5. `docs/reference/external-lane-status.md`

## What Each Layer Means

| Layer | Question it answers | What it must not be used for |
| --- | --- | --- |
| `value-proof.md` | Why the repository's task shape is worth caring about | It is not today's current-run verdict |
| `task-result-proof-pack.md` | Which public-safe representative cases support that story | It is not external verification for the current head |
| `newcomer-result-proof.json` | Whether repo-side proof is current for this head | It does not prove external closure |
| `current-state-summary.md` | Whether the current workspace and external lanes are actually closed today | It must not be read from stale metadata or historical runs |
| `external-lane-status.md` | How to interpret external lane states honestly | It does not replace runtime-owned artifacts |

## Reading Rule

- public-safe representative cases may justify why the repository has real task value,
- but only runtime-owned receipts may justify what is true for the current head today,
- and historical examples must never impersonate current external verification.
