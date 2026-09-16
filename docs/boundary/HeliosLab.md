---
repo: "HeliosLab"
role: unknown
status: active
last_boundary_review: 2026-07-17
review_cadence: 30d
in_scope:
  - "Experimentation and lab notebooks for the Phenotype ecosystem"
out_of_scope:
  - "Production-ready crates or libraries"
  - "Anything targeting the pheno workspace (use pheno/ for that)"
---

# Boundary — HeliosLab

## Disposition

**TOO_LARGE_RETIRE** (per fleet-absorption-eligibility-2026-07-17 policy).

`KooshaPari/HeliosLab` is a sprawling experimental/lab repo (55 remote branches, multi-language). Per the boundary correction 2026-07-17, it has been marked as **not absorption-eligible** because:

- Scope is too sprawling to consolidate into a single spine target.
- Lab/experimentation content is not a candidate for permanent absorption; it should remain a standalone playground.
- Repo is archived on GitHub (2026-07-17 boundary-corrections session); if the experimentation is needed again, fork it back locally.

## In Scope

- Lab notebooks, experimentation scripts, exploratory prototypes
- Multi-language testbenches (Rust + TypeScript + Python are common in HeliosLab)
- Throwaway integrations with emerging APIs (not promoted to spine members)

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Production-ready crates | `pheno/crates/*` | pheno workspace is the canonical Rust home |
| MCP server implementations | `PhenoMCPServers/` | implementations registry is the canonical home |
| Boundary contracts | `phenotype-contracts/` | 7th spine role (CONTRACTS) |
| Reusable journey harness | `phenotype-journeys/` | 6th spine role (JOURNEYS) |

## Boundary Crossings

None expected — HeliosLab is intentionally a leaf with no production dependencies.

## Restore Procedure (if experiments need to be revived)

```bash
gh repo unarchive KooshaPari/HeliosLab -y
```

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** registry steward (this session, batch boundary-corrections)
**Decisions:**
- Marked `TOO_LARGE_RETIRE` (55 branches, sprawling lab scope)
- GitHub-side: archived 2026-07-17

**Next review:** 2026-08-17 (if un-archived and re-entered scope)
