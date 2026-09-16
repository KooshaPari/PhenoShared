# Beads Boundary Assignment - Provisional Custody

**Date:** 2026-08-21
**Status:** Preservation in progress; no live data or publication owner is affirmed.

## Decision

The Beads cockpit is split into three boundaries so that recovery evidence is not mistaken for
a runnable product:

| Boundary | Custody | Present assertion | Explicit non-assertion |
|----------|---------|-------------------|------------------------|
| Renderer and generator | `pheno-harness` (provisional) | A preserved, tested implementation exists on a hosted branch | This is not an adoption of ledger data or a production publication service |
| Evidence and provenance | `phenotype-registry` | Registry may index dated manifests, hashes, and recovery decisions | Registry is not the writer and does not make a loose file a live SSOT |
| Ledger and cockpit publication | **UNASSIGNED** | The historical loose paths are volatile evidence | No replay, regeneration, or release may be claimed from those paths |

## Required acceptance gates

1. Specify and review a durable ledger location, schema, retention policy, writer identity, and
   read-only recovery interface.
2. Move the generator's configured input/output paths to that approved boundary; absolute loose
   paths and deletion-oriented helpers are prohibited.
3. Publish content-addressed outputs with non-destructive retention, failure alerts, and a
   reader contract that identifies snapshot versus live state.
4. Preserve the approved source and artifact set in Git plus an independent second cloud.
5. Restore onto an independent host and run a read-only ledger/render smoke with recorded hashes.

## Safety constraints

- Preserve all historical loose copies, branches, manifests, and recovery artifacts when present.
- Do not create a replacement ledger merely because a loose path has disappeared.
- A custody capture requires the source to be present for the same-run hash, byte-count, and
  JSONL-parse preflight. If it disappears before that preflight, stop and record a no-capture
  event; a prior observation or hash is not a substitute for current source bytes.
- Do not re-enable a periodic writer or dashboard publisher before Gates 1-3 have a reviewed
  implementation and Gates 4-5 have evidence.
- A future adoption or retirement decision is a separate reviewed change; this document grants
  neither.
