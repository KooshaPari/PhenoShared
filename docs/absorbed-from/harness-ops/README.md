# harness-ops -> PhenoRegistry (private)

**Source:** [KooshaPari/harness-ops](https://github.com/KooshaPari/harness-ops)
**Disposition:** `DATA_ONLY`
**Wave:** twelve-repo consolidation, 2026-11-11
**Worklog ref:** MRG-11

## Where the content went

| Destination | Files | Visibility |
|---|---|---|
| public copy | 0 | withheld entirely |
| `repos/harness-ops/` in `PhenoRegistry` | 65 | private |

## Withheld material

65 files were withheld from the public repo because they contain private
infrastructure detail: agent-comms deploy scripts and worker config carrying a Cloudflare zone identifier.

The exact path list is deliberately not reproduced here, because naming the
files would itself describe the private estate. It lives in the private
`PhenoRegistry` record for this repo.

## Why there is no public copy

This repo is private infrastructure in its entirety. Splitting it per file
would still publish host tooling, service and unit names and runbook
cadence, so nothing from it belongs in a public repository.

## Provenance

Per-file provenance: `repos/harness-ops/PROVENANCE.md` in `PhenoRegistry`.

The source repo has not been archived or deleted; that remains a separate
operator decision after this record landed.
