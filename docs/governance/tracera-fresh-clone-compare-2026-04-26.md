# Tracera Fresh Clone Compare - 2026-04-26

## Purpose

This completes `SUNSET-011A`: compare live `<REDACTED>/Tracera.git` against
local `Tracera-recovered` before any promotion, rename, or push operation.

## Decision

Do not promote `Tracera-recovered` directly over remote `main`.

Remote `main` is newer than the local recovered branch by 26 commits, while
`Tracera-recovered/fix/main-workflow-syntax` has 6 patch-different recovery
commits that are not on live `main`. The safe path is a new branch from live
`main` with reviewed cherry-picks, not a force-push or wholesale directory
promotion.

## Compared Refs

| Source | Ref | SHA | Notes |
|---|---|---|---|
| Fresh clone | `main` / `origin/main` | `5695f3984d31cde4cbc140219eada971b5ed8a40` | Live default branch. |
| Local recovered | `fix/main-workflow-syntax` | `f91232584284a2fa971b8b9b4c3122cf1b9dba34` | Dirty local working tree. |
| Remote recovered branch | `origin/fix/main-workflow-syntax` | `19e9a9ab2f47eb61aab28f1cba2eff58693875f5` | One commit behind local recovered branch. |
| Merge base | `main...fix/main-workflow-syntax` | `ab5f80fa345a12618c27f312ba9ac407373779a2` | Local `origin/main` in recovered checkout was stale here. |

Ancestry:

```text
live main vs local fix/main-workflow-syntax: 26 behind / 6 ahead
remote fix/main-workflow-syntax vs live main: 26 behind / 5 ahead
```

## Recovery Commits Not On Live Main

Review each commit individually before cherry-picking:

```text
bcf56fea ci: repair invalid workflow syntax
d7d68840 ci: scope legacy broad workflows
048a9699 chore(ci): adopt phenotype-tooling workflows (wave-2)
8873600b feat(tracera): tracertm.cli stub with all command modules
19e9a9ab docs(worklog): bootstrap worklog scaffolding (org-wide gap closure)
f9123258 chore: add MIT LICENSE and update README
```

## File Presence Snapshot

Both live `main` and `Tracera-recovered` contain the real TracerTM product
shape:

- `backend/go.mod`
- `frontend/package.json`
- `docs/package.json`
- `package.json`
- `process-compose.yml`
- `openapi/README.md`
- `proto/README.md`
- `schemas/README.md`
- `tests/README.md`

Important deltas:

| Area | Live `main` | `Tracera-recovered` |
|---|---|---|
| Licensing | `LICENSE-MIT`, `LICENSE-APACHE` | single `LICENSE` |
| Worklogs | no root `worklogs/README.md` in key-file snapshot | `worklogs/README.md` |
| Workflow branch | current remote workflows include recent security/action pinning commits | recovered branch has older workflow repair/scope commits |
| CLI recovery | live main lacks recovered `src/tracertm/cli/*` diff from recovered branch | recovered branch adds CLI command stubs |

## Working Tree Risk

Local `Tracera-recovered` is dirty:

```text
M AGENTS.md
M CLAUDE.md
M agents.md
M claude.md
?? docs/worklogs/*
?? tests/test_smoke.py
?? worklog.md
```

Do not switch or rebase this local checkout until the dirty files are either
bundled, copied to a quarantine artifact, or intentionally discarded in a
separate decision.

## Promotion Plan

1. Preserve local dirty files from `Tracera-recovered` into a dated quarantine
   manifest or patch bundle.
2. Create a fresh branch from live `origin/main` at `5695f398`.
3. Cherry-pick only still-needed recovery commits, in order:
   - likely keep: `8873600b` CLI stub, `19e9a9ab` worklog scaffolding
   - review carefully: `bcf56fea`, `d7d68840`, `048a9699` workflow changes
   - likely replace/rework: `f9123258` license/README because live main now has
     dual-license files and README updates
4. Resolve conflicts against current workflows, README, and license files.
5. Validate at minimum:

```bash
git diff --check
gh workflow list --repo <REDACTED>/Tracera
actionlint .github/workflows/*.yml
go test ./backend/...
```

6. Push the new branch and open a PR to `main`.
7. Do not force-push `main`.
8. Do not overwrite remote `fix/main-workflow-syntax`.

## SUNSET-011A Status

Complete. Follow-up is `SUNSET-011B`: create the live-main recovery branch and
cherry-pick reviewed commits.

`SUNSET-011B` is closed in
`docs/governance/tracera-recovery-disposition-2026-04-26.md`: the two safe
workflow recovery commits were already represented on live Tracera `main`, and
the remaining recovered commits were skipped or deferred for scoped rework.
