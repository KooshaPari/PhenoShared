# Flake Tracker

SessionLedger treats a failing test as a product signal, not a CI nuisance. A
test may be quarantined only after the failure is captured with enough evidence
to reproduce or remove the quarantine.

## Required Record

Track confirmed flakes in `docs/ops/flakes-records.json`. The JSON schema lives in
[`flakes.json`](flakes.json). Each entry includes:

- `id`: stable issue or tracker id.
- `test`: exact test target or test name.
- `status`: `open`, `quarantined`, or `resolved`.
- `owner`: person or team responsible for root cause.
- `opened`: ISO-8601 date.
- `deadline`: ISO-8601 removal deadline for quarantined tests.
- `evidence`: CI URL, proptest seed, panic output, or local reproduction note.
- `quarantine`: how the test was isolated, or `null` when it still runs.

## Quarantine Rules

Quarantine is temporary and must have an owner, linked issue, evidence, and a
deadline. Prefer reducing nondeterminism or committing a regression fixture over
adding retries. If a repeat job catches a failure, preserve the seed/output in
the tracker before rerunning locally. CI publishes rerun stats from
[`scripts/flake-rerun-stats.ps1`](../../scripts/flake-rerun-stats.ps1) as
`docs/ops/flake-rerun-stats.json` and uploads the artifact from the
`flake-tracker` job.

Resolved flakes stay in the file with `status: "resolved"` until the next
release cycle, so reviewers can see when a quarantine was removed.

[`scripts/flake-quarantine-apply.ps1`](../../scripts/flake-quarantine-apply.ps1)
reads quarantined entries and emits `cargo test --skip <name>` arguments for
the `flake-tracker` and default `build-test` property reruns.
