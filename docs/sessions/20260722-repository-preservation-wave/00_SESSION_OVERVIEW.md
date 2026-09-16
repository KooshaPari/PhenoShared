# Repository Preservation Wave

## Goal

Preserve and verify the first 20 recovery/archive repositories in their canonical parents without
deleting, renaming, archiving, force-pushing, or merging source content into active branches.

## Success criteria

- `preservation-manifest.json` names all 20 sources, owners, dispositions, and gates.
- W1 imports use isolated `refs/archive/` or `refs/recovery/` namespaces only.
- W2 proves every imported SHA through GitHub before any later archive proposal.

## Links

- Boundary SSOT: `BOUNDARY_OWNERS.md`
- Rationalization plan: `docs/rationalization/ZERO_LOOP_ECOSYSTEM_PLAN.md`
- Execution DAG: `docs/rationalization/ECOSYSTEM_DAG.md`

## Outcome

W0 ledger authored. W1 and W2 remain pending.

## 2026-08-11 cockpit source-boundary preservation evidence

An additive evidence packet records the non-Git cockpit source chain without moving, replacing,
or initializing any source directory. It preserves two time-stamped observations: the supplied
render snapshot at `2026-08-11T06:53:33Z`, and a later rehash that detected source churn.

That 2026-08-11 observation must be read as historical preservation evidence, not a current
operating-owner decision.  The later custody review found no durable, tracked live ledger or
publication boundary.  `BOUNDARY_OWNERS.md` now records `pheno-harness` as the provisional
renderer/generator custodian, `phenotype-registry` as immutable provenance custodian, and the
live ledger plus cockpit publication as **UNASSIGNED** until their explicit owner gates pass.
No claim is made that AgilePlus or Tracera currently operates this surface.
