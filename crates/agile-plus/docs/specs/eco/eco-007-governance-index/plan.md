# Plan: Governance Index

## Objective
Make kitty-spec coverage live and provably current by generating
`AgilePlus/kitty-specs/INDEX.md` from `meta.json` on every push, closing
FR1 from `worklogs/eco-006-compliance-20260605.md`.

## Scope
- Governance index generation and CI wiring only.
- No product-code or runtime changes.
- No migrations of historical `meta.json` files beyond filling
  `reactivated` / `superseded_by` where obviously missing.

## Implementation Steps
1. **Indexer script** — Add `AgilePlus/tooling/governance_index.py`
   (Python 3.10+, stdlib only). It walks
   `AgilePlus/kitty-specs/*/meta.json`, sorts by `spec_id`, and emits
   `AgilePlus/kitty-specs/INDEX.md` as a Markdown table with columns
   `spec_id | slug | status | created | reactivated | superseded_by |
   link`. Stable sort and deterministic output.
2. **Emitted `INDEX.md`** — Generated artifact committed to the repo,
   listing every kitty-spec with clickable relative links to each
   spec directory and a clear `status` cell (`active`, `pending`,
   `retired`). Retired rows surface `superseded_by` where populated.
3. **CI workflow** — Add `.github/workflows/governance-index.yml` that
   runs on `push` to `main` (and `workflow_dispatch`). It checks out
   the repo, runs the indexer, and uses `peter-evans/create-pull-request`
   or a direct `git commit` + `git push` step to commit any diff to
   `AgilePlus/kitty-specs/INDEX.md`. Runs on `ubuntu-latest` (standard
   Linux runner, no billing impact).
4. **Local verification hook** — Add a `task` Make target or
   `scripts/regen-index.sh` wrapper so a developer can reproduce
   `INDEX.md` locally with one command. Same script is invoked by CI.
5. **Backfill hint** — Note in the indexer README that
   `reactivated` / `superseded_by` are optional and may be `null` /
   missing; the indexer must render `—` in that case.

## Verification
- `python3 AgilePlus/tooling/governance_index.py` produces
  `AgilePlus/kitty-specs/INDEX.md` that is byte-identical to the
  committed copy (`git diff --exit-code` is clean).
- `agileplus validate-encoding --all` reports no BOM on `INDEX.md`.
- Workflow file passes YAML lint and references `ubuntu-latest`.
- Manual push to a test branch triggers the workflow and updates
  `INDEX.md` automatically.
- After merge, `eco-006-compliance-*.md` re-audit shows FR1
  checkbox resolved.
