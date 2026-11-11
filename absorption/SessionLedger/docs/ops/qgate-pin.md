# Quality-gate reusable workflow pin

SessionLedger calls the shared Phenotype quality gate from
`KooshaPari/phenotype-tooling` via
[`.github/workflows/qgate.yml`](../../.github/workflows/qgate.yml).

## Current pin

| Field             | Value                                                                      |
| ----------------- | -------------------------------------------------------------------------- |
| Workflow          | `KooshaPari/phenotype-tooling/.github/workflows/reusable/quality-gate.yml` |
| Commit SHA        | `c43cc4af2cbcc2bb2df37f3e4ab78cc5d8c1b3ad`                                 |
| Recorded tip      | phenotype-tooling `main` as of 2026-07-13                                  |
| `qgate-ref` input | same SHA (builds the `qgate` binary from that commit)                      |

Both the `uses: …@<sha>` ref and the `qgate-ref` workflow input must be full
40-character commit SHAs. Do not use `@main`, branch names, or moving tags.

## Why

Reusable workflow and action refs that float on a branch are mutable supply-chain
inputs. Pinning the workflow file and the `qgate` source ref to the same commit
keeps the gate reproducible until a deliberate bump.

## Bump procedure

1. Choose a phenotype-tooling commit that includes the desired
   `reusable/quality-gate.yml` (and compatible `qgate` crate).
2. Update both places in `.github/workflows/qgate.yml`:
   - `jobs.quality-gate.uses` `@<full-sha>`
   - `jobs.quality-gate.with.qgate-ref: <full-sha>`
3. Refresh the table in this document and the short note in
   [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
4. Open a focused PR; keep the gate `continue-on-error` until per-module
   coverage meets the `.qgate.toml` threshold.
