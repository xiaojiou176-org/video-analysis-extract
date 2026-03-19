# Root Governance

The repository root only serves two roles:

- **Public repository assets**: tracked by Git and allowed to exist as public governance entrypoints.
- **Local-private tolerated items**: allowed to exist at the root, but they must stay untracked.

## Sources Of Truth For Public Root Assets

- `tracked_root_allowlist` in `config/governance/root-allowlist.json`
- `config/governance/root-denylist.json`
- `config/governance/root-layout-budget.json`
- `config/governance/public-entrypoints.json`

## Final Entry-Point Constraints

- `.agents/Plans/`: the in-repo execution board and construction log; this is a governed public control surface.
- `bin/`: the stable public command surface. Humans, hooks, CI, and docs must reference `bin/*` instead of exposing `scripts/*` as long-term public entrypoints.
- `THIRD_PARTY_NOTICES.md`: the third-party rights ledger used for public distribution. It must stay machine-generated instead of hand-maintained.
- Root-level `.venv` / `venv` are not legal root assets; governed Python environments must live under `.runtime-cache/tmp/` or a controlled path outside the repository.

## Local-Private Tolerations

The following paths may exist at the root, but they must stay untracked:

- `.env`
- `.vscode/`
- `.codex/`
- `.claude/`
- `.cursor/`

## Gates

```bash
python3 scripts/governance/check_root_allowlist.py --strict-local-private
python3 scripts/governance/check_root_layout_budget.py
python3 scripts/governance/check_root_zero_unknowns.py
python3 scripts/governance/check_root_dirtiness_after_tasks.py --compare-snapshot <snapshot>
python3 scripts/governance/check_public_entrypoint_references.py
python3 scripts/governance/check_root_policy_alignment.py
```

Additional Reading Rule:

- `check_root_dirtiness_after_tasks.py` now checks more than the root hallway. It also checks whether `.runtime-cache/`, the repository-wide runtime-output root, has grown undeclared direct children.
- In plain English: the final root cleanliness verdict now means “the hallway is clean and the main runtime storage room entrance has not silently drifted.”

## Hard Rules

- Do not add undeclared top-level entries.
- Do not reintroduce denylisted catch-all directories at the root.
- Do not commit local-private tolerated items.
- Do not spread local helpers, experiments, or one-off outputs across the root hallway.
- Do not bypass `bin/*` and expose `scripts/*` directly to docs, hooks, or workflows as public entrypoints.
