# Cockpit deprecation ladder (v0.13 Phase 5)

**Status:** DRAFT — v0.13 Phase 5, tasks 66-75 combined design doc.
**Owner:** forge (pheno-harness) <forge@phenotype.local>
**Audience:** on-call engineers migrating from cockpit to AgilePlus + Tracera.

## Why deprecate cockpit

The cockpit HTML at `repos/cockpit/bead-cockpit-20260809-191131-f5ca38f7.html`
was created as a temporary portfolio SSOT while AgilePlus (work tracking)
and Tracera (trace repository) were not yet functional. Both are now
functional as of v0.12 Phase 2 + Phase 1:

- **AgilePlus** (v0.12 Phase 2, 15 tasks) — `beads/agileplus_adapter/`
  provides `AgilePlusBeadStore.append/query/dedup_check/stats/health/
  bulk_append` over the AgilePlus REST API. 50-bead migration verified.
- **Tracera** (v0.12 Phase 1, 15 tasks) — `pheno/trace_store/tracera.py`
  + `traces/tracera_bridge.py` provide persistent trace storage with
  dual-write bridge to JSONL. v0.13 Phase 1 added sample-rate cohort
  rollout (production-ready).

The cockpit HTML is regenerated from `phenotype-dag/beads.jsonl` by an
autocommit daemon. It contains 16 PM-lens kanban columns, FR-COCKPIT
entries, CP+Paste prompts, intent + synthesis, and session mapping.
Maintaining the daemon + HTML is redundant now that AgilePlus + Tracera
can serve the same data.

## Deprecation ladder

| Step | Action | Status |
|------|--------|--------|
| 1 | Add cockpit-migrator script (JSONL → AgilePlus + Tracera) | task 68 (DONE in v0.13 Phase 5) |
| 2 | Add cockpit-migrator tests | task 69 (DONE) |
| 3 | Mark cockpit HTML with deprecation banner | task 73 (DONE) |
| 4 | Disable cockpit autocommit daemon | task 74 (DONE) |
| 5 | Document migration procedure | task 70 (DONE — this doc) |
| 6 | Migrate remaining beads.jsonl entries to AgilePlus | task 74 (DONE) |
| 7 | Switch the dashboard from cockpit HTML to AgilePlus UI | external (post-v0.13) |
| 8 | Delete cockpit HTML and autocommit daemon | external (post-v0.13) |

## Migration procedure

```sh
# 1. Dry-run (read-only, prints what would migrate)
.venv/bin/python scripts/cockpit_migrator.py --dry-run

# 2. Migrate to AgilePlus (50 beads at a time, idempotent)
.venv/bin/python scripts/cockpit_migrator.py --backend=agileplus --batch=50

# 3. Verify migration count matches beads.jsonl line count
.venv/bin/python scripts/cockpit_migrator.py --verify

# 4. Optional: archive beads.jsonl to .archive/ before deletion
mv /Users/<REDACTED>/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl \
   /Users/<REDACTED>/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl.archive.$(date +%Y%m%d)
```

## Mapping: cockpit event → AgilePlus + Tracera

| Cockpit field | AgilePlus destination | Tracera destination |
|---------------|----------------------|---------------------|
| `id` | `bead.id` | `event.metadata.bead_id` |
| `ts` | `bead.ts` | `event.ts` |
| `agent` | `bead.agent` | `event.actor` |
| `kind` | `bead.kind` | `event.kind` |
| `target` | `bead.target` | `event.target` |
| `text` | `bead.text` | `event.payload.text` |
| `hash` | `bead.hash` | `event.metadata.bead_hash` |
| `host` | `bead.metadata.host` | `event.metadata.host` |
| `session` | `bead.metadata.session` | `event.session_id` |
| `frId` | `bead.metadata.frId` | `event.metadata.frId` |
| `outcome` | `bead.metadata.outcome` | `event.payload.outcome` |

## Cockpit HTML sections inventory (task 66)

| Section | h2 id | Source | Migration |
|---------|-------|--------|-----------|
| Summary | `summary` | beads count by kind | Compute via `AgilePlusBeadStore.stats()` |
| Kanban | `kanban` | 16 PM-lens columns | Render via AgilePlus query API |
| ARCHIVED → RETROSPECTED | (h3) | lane buckets | Each lane = query by `metadata.lane` |
| PM-Style Outcomes | `pm` | FR/user-facing outcomes | `metadata.outcome` field |
| Product Management | `reconciliation-heading` | FR verification status | `metadata.verified=true` filter |
| Functional Outcomes | (h3) | FR-COCKPIT-* entries | `metadata.frId` filter |
| Sessions | (h3) | session_id mapping | `metadata.session` filter |

## Rollback procedure

If migration causes data loss:

1. Restore `beads.jsonl` from `.archive/<date>`.
2. Re-enable the cockpit autocommit daemon.
3. Remove the deprecation banner from the HTML.
4. Open an incident in #phenotype-ops.

## Acceptance

- `scripts/cockpit_migrator.py` exists and is idempotent.
- `tests/test_cockpit_migrator.py` covers dry-run, single-bead, batch,
  verify, error cases.
- Cockpit HTML carries a deprecation banner.
- `~/.pheno-harness/env.sh` can set `COCKPIT_DEPRECATED=1` to silence
  the autocommit daemon.

---

*Cockpit deprecation ladder — design + procedure + mapping + rollback.*
