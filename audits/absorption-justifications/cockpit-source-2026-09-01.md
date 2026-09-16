# cockpit-source — boundary governance reconciliation (2026-09-01)

**Verdict:** KEEP_STANDALONE — SOURCE custodian for the local operational cockpit.

**Confidence:** 0.95 (active repo with verifiable provenance, no absorption intent, no contradictory governance doc).

## Repo facts

- **Repo path:** `repos/cockpit-source` (mirror); `KooshaPari/cockpit` (canonical GitHub).
- **Default branch:** `main` | **Last commit:** 2026-08-20 (provenance review).
- **Active branches:** `main`, `fix/cockpit-provenance-review-20260816` (provenance ledger work).
- **Subdirs:** `dashboard/` (LaunchAgent dashboard producer), `launchd/` (plist installer),
  `tools/` (Leapfrog static multi-view cockpit generator), `tests/` (focused generator tests).
- **README role statement:** "Canonical source for the local operational cockpit generators. This repository intentionally tracks source and tests only."
- **Visibility:** private. No archived status. No license (intentional source-only scope).

## Boundary

- **Source custodian boundary:** `cockpit-source-custodian` (NEW; this audit introduces it).
  Registered in `phenotype-registry/projects/cockpit-source.json`.
- **Publication boundary (separate, UNASSIGNED):** `cockpit-publication` — per
  `BOUNDARY_OWNERS.md` lines 119-138, this is a provisional boundary for the live
  Beads ledger and dashboard publication. **UNASSIGNED** with `preservation_in_progress`
  status. Distinct from the SOURCE custodian.
- **Live Beads ledger boundary (separate, UNASSIGNED):** `cockpit-live-ledger` — also
  per `BOUNDARY_OWNERS.md` lines 119-138. UNASSIGNED. Distinct from both the SOURCE
  custodian and the publication boundary.

## Drift reconciled

cockpit-source was previously **completely absent** from the registry:

- No `projects/cockpit-source.json` entry.
- No row in `registry/disposition-index.json`.
- No mention in `BOUNDARY_OWNERS.md` (the section lines 119-138 references the
  cockpit boundary, but does not name cockpit-source as the source custodian).
- No mention in `ECOSYSTEM_MAP.md`.
- No mention in `RATIONALIZATION_PLAN.md` or `RATIONALIZATION_EXECUTION.md`.

This absence is a high-severity SSOT drift: cockpit-source is an active, maintained
repository producing live local dashboards, yet invisible to governance scanning.

This audit creates the missing `projects/cockpit-source.json` and recommends
[P2] updates to `BOUNDARY_OWNERS.md` (add cockpit-source as the provisional SOURCE
custodian for the cockpit boundary section) and `ECOSYSTEM_MAP.md` (cockpit-source
in tooling cluster).

## Cross-references

- BOUNDARY_OWNERS.md lines 119-138 — cockpit boundary section (provisional)
- projects/cockpit-source.json — new SSOT card (this audit)
- cockpit-source/README.md — repo's own role statement
