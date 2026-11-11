# host-ops -> PhenoRegistry (private)

**Source:** [KooshaPari/host-ops](https://github.com/KooshaPari/host-ops)
**Disposition:** `DATA_ONLY`
**Wave:** twelve-repo consolidation, 2026-11-11
**Worklog ref:** MRG-10

## Where the content went

| Destination | Files | Visibility |
|---|---|---|
| public copy | 0 | withheld entirely |
| `repos/host-ops/` in `PhenoRegistry` | 107 | private |

## Withheld material

107 files were withheld from the public repo because they contain private
infrastructure detail: host runbooks, tailnet addressing, systemd units and launchd labels, operational reports.

The exact path list is deliberately not reproduced here, because naming the
files would itself describe the private estate. It lives in the private
`PhenoRegistry` record for this repo.

## Why there is no public copy

This repo is private infrastructure in its entirety. Splitting it per file
would still publish host tooling, service and unit names and runbook
cadence, so nothing from it belongs in a public repository.

## Provenance

Per-file provenance: `repos/host-ops/PROVENANCE.md` in `PhenoRegistry`.

The source repo has not been archived or deleted; that remains a separate
operator decision after this record landed.

