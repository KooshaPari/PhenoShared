---
repo: "heliosApp"
role: unknown
status: active
last_boundary_review: 2026-07-17
review_cadence: 30d
classification: TOO_LARGE_RETIRE
---

# Boundary — heliosApp

## Verdict

**TOO_LARGE_RETIRE** — do not absorb. Repo can stay LIVE on GitHub but is **not** an
absorption candidate per the user boundary directive (2026-07-17):

> "apps are too large in scope, too incomplete, or too bound by upstream state
> (it's a fork) to absorb"

## Ground-truth audit (2026-07-17)

| Field | Reality | Registry claim (pre-correction) | Status |
|---|---|---|---|
| Language | TypeScript (Bun monorepo) | "Swift" | ❌ → ✅ corrected |
| Layout | `apps/runtime`, `apps/desktop`, `apps/colab-renderer`, `packages/errors`, `packages/ids`, `packages/logger`, `packages/runtime-core`, `packages/types` | n/a | ✅ |
| Remote size | ~1 MB | n/a | — |
| Remote branches | 146 | n/a | sprawling fork surface |
| License | TBD (likely upstream project — not a Phenotype-ecosystem repo) | n/a | — |
| Purpose | Helios-derived app (upstream tracking) | n/a | — |
| State at audit | repo NOT cloned locally; registry referenced phantom path | n/a | — |

## In Scope

Nothing — this repo is **out of scope** for absorption.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Phenotype contracts / schemas | `phenotype-contracts` (live spine member) | heliosApp is not a phenotype repo |
| Provider/LLM proxy logic | `forgecode` (fork of tailcallhq/forgecode) | different upstream |
| Application chrome | candidate for phenotype-apps directory | would require thinning first |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| (none active) | — | — | — |

## Notes from registry note (verbatim, corrected)

> TypeScript Bun monorepo (apps/runtime + apps/desktop + apps/colab-renderer +
> packages/errors/ids/logger/runtime-core/types). 146 branches, ~1MB. Sprawling
> scope; no single owner; not a candidate for absorption in current state.
> Previous registry row recorded this as Swift (wrong). Corrected to TypeScript.
> Repo can stay LIVE but not absorb.

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** forge subagent (boundary-corrections pass)
**Decisions:**
- Language corrected: Swift → TypeScript
- Disposition: TOO_LARGE_RETIRE
- Do not absorb; keep remote live as-is
- Repo doesn't need a boundary doc if it's not absorbed, but flagged here as
  record of the misclaim correction

**Next review:** 2026-08-17
