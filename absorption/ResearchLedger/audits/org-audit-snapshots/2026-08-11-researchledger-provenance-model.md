# Snapshot: ResearchLedger Provenance Model — 2026-08-11

## Summary

Anchors the ResearchLedger provenance model inside the audit trail.
The model is the canonical reference for how notes, citations,
and machine-readable evidence flow into and out of the local-first
knowledge base.

## Provenance kinds

| Kind | Source | Atomicity | Audit-trail guarantee |
|---|---|---|---|
| `link` | HTTP URL (web page, paper, post) | per-fetch | `[[wikilink]]` + fetched timestamp |
| `paper` | arXiv / DOI / journal | per-paper | bibliographic block + DOI |
| `quote` | Pulled from a source | per-quote | source + cursor position |
| `note` | Free-form | per-note | `prompt` bead (if user-initiated) |
| `agent-trace` | Internal agent conversation | per-step | `complete` bead per step |
| `tick` | Time-stamped observation | per-tick | `prompt` bead (timestamp) |

## Cross-references

- `ResearchLedger/README.md` (user-facing)
- `BACKLOG-CROSSREPO-001-cluster-5` (ResearchLedger audits scaffold)
- `pheno` cli (companion tool that pushes events into
  ResearchLedger)
- `phenotype-shared` (shared utilities for citation parsing)

## Supersedes

None.
