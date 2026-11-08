# Block-C Consolidation Plan — <REDACTED>/phenokits-commons

**Date:** 2026-06-17  
**Status:** Approved for execution  
**Audit source:** `docs/audit/BLOCK-C-AUDIT.md`  
**Disposition:** `docs/boundary/DISPOSITION.md`  
**DAG lane:** C (merge #3 + governance bootstrap doc), N (fleet defaults spec)

---

## Goal

Consolidate phenokits-commons as the **fleet governance commons** boundary —
templates, configs, and test harness patterns — with PhenoKits/PhenoProc absorption
complete and domain libraries relocated to SDK repos.

---

## Current baseline (verified)

| Check | Result |
|-------|--------|
| PR #3 merged to `main` | PASS (913131a) |
| `governance/phenoproc-templates/` | PASS |
| `governance/phenoproc-configs/` | PASS |
| PhenoKits path parity | PASS (100%) |
| `docs/boundary/DISPOSITION.md` | This PR |
| README reflects commons scope | FAIL (pre-split SDK text remains) |

---

## Phase 1 — Boundary documentation (P0)

| ID | Task | Acceptance |
|----|------|------------|
| C1.1 | Publish `docs/boundary/DISPOSITION.md` | Every top-level module has disposition + target |
| C1.2 | Publish `docs/audit/BLOCK-C-AUDIT.md` | Baseline signals recorded |
| C1.3 | Publish `governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md` | Fleet bootstrap paths documented |
| C1.4 | Link disposition from `governance/README.md` | Cross-reference present |

**Risk:** Low — docs only.

---

## Phase 2 — README + boundary lock (P1)

| ID | Task | Acceptance |
|----|------|------------|
| C2.1 | Rewrite root `README.md` for commons scope | Remove python-sdk / go-sdk monorepo sections |
| C2.2 | Add root `BOUNDARY.md` lock | Declares scaffold-only role per disposition §1 |
| C2.3 | Update `STATUS.md` with Block-C completion date | Dated entry |

---

## Phase 3 — Library relocation (P1)

| ID | Task | Acceptance |
|----|------|------------|
| C3.1 | Move `libs/go/*` (except `phenotype-id`) → `phenotype-go-sdk` | Redirect README in commons |
| C3.2 | Move `libs/typescript/*` (except `phenotype-id`) → TS SDK repo | Redirect README in commons |
| C3.3 | Keep polyglot `phenotype-id` in all three langs | Reference impl documented |

---

## Phase 4 — Submodule hygiene (P2)

| ID | Task | Acceptance |
|----|------|------------|
| C4.1 | Remove `HexaKit/` git submodule | `.gitmodules` clean; docs point to HexaKit repo |
| C4.2 | Relocate `templates/clean-rust/` etc. to HexaKit if still needed | Or mark deprecated with HexaKit path |

---

## Phase 5 — Cross-repo Block-C alignment (P2)

Sibling Block-C dispositions (same wave, separate PRs):

| Repo | State | Next action |
|------|-------|-------------|
| `<REDACTED>/HexaKit` | DISPOSITION merged (#233) | Execute crate eviction (Lane P) |
| `<REDACTED>/services` | `audit/block-c` branch | Merge audit docs |
| `<REDACTED>/Tokn` | Plan on `main` | Execute source-tree consolidation |
| `<REDACTED>/phenotype-registry` | Lane A (#76) | BOUNDARY_OWNERS SSOT |

---

## Execution order (DAG)

```
C1.1 → C1.2 → C1.3 → C1.4
C2.* (after C1 merged)
C3.* ∥ C4.* (parallel after C2)
Phase 5 (ongoing fleet wave)
```

---

## Out of scope

- Deleting archived `PhenoKits` (requires Lane F manifest scan)
- OTel-bootstrap consolidation (cross-project audit #4 — NB)
- Rewriting historical `worklogs/` or `kitty-specs/`

---

## Success criteria

1. Disposition + audit + fleet defaults on `main`
2. phenokits-commons role = governance commons, not SDK warehouse
3. Lane C + Lane N acceptance in `ECOSYSTEM_DAG.md` satisfied
