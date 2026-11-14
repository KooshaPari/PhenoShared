# host-ops -> PhenoRegistry (private)

**Source:** [KooshaPari/host-ops](https://github.com/KooshaPari/host-ops)
**Disposition:** `DATA_ONLY`
**Wave:** twelve-repo consolidation, 2026-11-11; whole-tree refresh, 2026-11-14
**Worklog ref:** MRG-10

## Where the content went

| Destination                                   | Files   | Visibility        |
| --------------------------------------------- | ------- | ----------------- |
| public copy                                   | 0       | withheld entirely |
| `repos/host-ops/tree/` in `PhenoRegistry`     | 683     | private           |
| `refs/preserved/host-ops/` in `PhenoRegistry` | 85 refs | private           |

The whole repository is stored privately, not a per-file selection: the default
branch as `tree/`, and every branch and pull-request ref under
`refs/preserved/host-ops/`.

## Why there is no public copy

This repo is private infrastructure in its entirety. Splitting it per file would
still publish host tooling, service and unit names and runbook cadence, so
nothing from it belongs in a public repository.

For the same reason the path list is not reproduced here: naming the files would
itself describe the private estate. It lives in the private `PhenoRegistry`
record for this repo.

## Verification

The snapshot is the default branch at `f8b39eb8` (tree `6879bb6f95`), pushed to
the private registry as `781f9a75`.

The 2026-11-11 pass copied 107 files flat. That was a partial selection, and it
went stale while the source kept moving, so on 2026-11-14 the whole default
branch was grafted instead and the flat copy removed as a superseded duplicate.

```console
$ python scripts/verify_absorption.py host-ops
  OK    host-ops                         683/683  (683 withheld to registry)

$ python scripts/verify_preserved.py host-ops
host-ops                 tree 6879bb6f95 == branch main
```

`verify_absorption.py` reads the source tree from GitHub and resolves every path
against the private registry, so 683 of 683 means no source file is
unaccounted for. `verify_preserved.py` compares the grafted subtree id with the
tree id of every preserved branch and names the branch it matches, so the copy is
the default branch rather than a lookalike. Byte identity was proved separately
by comparing git blob ids per path: 683 of 683 matched.

## Provenance

Per-file provenance, layout and the history of this record:
`repos/host-ops/PROVENANCE.md` in `PhenoRegistry`.

The source repo is still live. Deleting it is a separate operator decision that
has not been taken, and the content above is what would survive it.
