# Observability Trio (cross-reference)

Three repos on <REDACTED> cover observability / tracing / logging:

  - <REDACTED>/PhenoObservability  (Rust, 1606KB, 2026-09-09) — KEEP
  - <REDACTED>/pheno-tracing       (Rust, 287KB,  2026-09-09) — candidate submodule
  - <REDACTED>/Logify              (Rust, 174KB,  2026-09-10) — candidate absorb or move to phenoUtils

## Dependency graph

  PhenoObservability  ⊃  (would-be-submodule) pheno-tracing
        ↓ (producers)
  Logify  →  consumers (3rd-party apps)

## Conditions for consolidation (currently false)

  - Consumer fleet converges on a single observability stack
  - Registry contract unification
  - Unified ship cadence

## Refs

- nanovms PRs numbered 196 through 201 (batch 25 scope complete)
- phenoResearchEngine PRs numbered 66 through 70 (batch 27 scope complete)
- PhenoFastMCP PR numbered 18 POLYGLOT STATUS md (batch 26 scope complete)
- phenodocs PR numbered 224 vcs router teamcomm triad (E9)
- Apisync PR numbered 417 BLOCK-A-TRIO crossref (A1)
