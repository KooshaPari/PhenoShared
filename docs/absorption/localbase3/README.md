# localbase3 affirmation (recorded 2026-07-17)

## Status

| Field | Value |
| ----- | ----- |
| Source | `KooshaPari/localbase3` |
| Disposition | AFFIRM (canonical, NOT absorbed) |
| Registry row | `repo-localbase3` |
| Registry version | 1.6.30 |
| size_kb | 256 |
| branches | 32 |
| last_push | 2026-06-08 |

## Rationale

localbase3 is an ~87000 LOC multi-subsystem full-stack project
(localbase, localbase-api, localbase-chain, localbase-docs,
localbase-frontend, localbase-provider, localbase-tests, amp/) with
**its own product identity**. It is recorded in the registry as
AFFIRMED — the canonical artifact lives where it lives, and absorbing
it into any monorepo would lose its identity and break deployment
topology.

## Verification evidence (2026-07-17)

1. `git ls-remote` returns 32 refs at HEAD `3011bdee` (empty main;
   content lives on `airlock-recovery/main`).
2. Repo metadata in registry `projects/localbase3.json` shows size_kb=256,
   remote_branch_count=32, last_push 2026-06-08.
3. The 32 branches include 8 `chore/*` branches (CI/housekeeping) and
   a single `KooshaPari-patch-1` branch (likely external PR).
4. `main` HEAD is empty (deletion-equivalent commit at 3011bde).

## Cross-references

- boundary: `docs/boundary/localbase3.md`
- registry row: `repo-localbase3` (fsm=verified in v1.6.30)
- related: `localbase-api` (Express/Node) overlaps with phenodocs/dev
  patterns — no shared code currently.

## Forward-looking note

If localbase3 ever needs to become a Phenotype-org product, propose
ADR-122: "localbase3 productization" before flipping this row from
AFFIRM to ABSORB.
