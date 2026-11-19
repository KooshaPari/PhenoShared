# Session 2026-11-19 — PhenoShared forensic audit and reshape plan

Read-only audit of `KooshaPari/PhenoShared` at `f06c3cc7f`, producing the three artifacts the task
asked for, plus the corrections found while writing them.

## Deliverables

| File | Deliverable | Note |
|---|---|---|
| `CODEBASE-ATLAS.md` | Codebase atlas | size, language mix, build topology, governed-package staleness |
| `QA-MATRIX.md` | QA matrix | CI surface, test census, coverage floors, the one real coverage artifact |
| `../../dossiers/DOSSIER.md` | Product dossier | second edition appended to the 2026-11-12 edition, which is preserved unchanged |

## Why the atlas lives in `docs/sessions/`

`docs/atlas/` is a governed package: `MANIFEST.json` lists 257 payload files with sha256,
`SHA256SUMS` pins them, and `docs/atlas/scripts/validate_package.py` walks every markdown file under
the package for broken relative links and every file for emptiness. `cvp-nightly.yml` runs it. Session
audit output does not belong inside a checksum-governed package, so these live here and cross-reference
the package instead.

## Corrections recorded because they produced wrong numbers first

1. `xargs wc -l | tail -1` returns only the final xargs batch. Over 11,466 Rust files it reported
   365,543 lines against a true 3,158,866. Always concatenate first:
   `git ls-files -z -- '*.rs' | xargs -0 cat | wc -l`.
2. A count of `[workspace] members` entries is not a count of members. **287** entries glob-expand
   to 292 packages; only `cargo metadata --no-deps` is authoritative. Two other figures were produced
   by counting quoted lines (288 on the Mac, 240 on the desk) and both were wrong.
3. A prior dossier already existed at `docs/dossiers/DOSSIER.md`. It was overwritten once during this
   session and restored byte-identically from `HEAD` before any commit; the second edition is now
   appended to it instead of replacing it.

## Host attribution

Every number in these documents was derived twice, on two hosts, and the host that served it is
named where the figure appears.

| Host | Role | What it served |
|---|---|---|
| Mac (`~/CodeProjects/phenotype/repos/PhenoShared-space/docs/wtree`, `f06c3cc7f`) | working tree, GitHub credentials, doc authoring | the audit itself, `gh` run history, the validator run |
| Desk (`ssh desk` -> WSL2 Fedora, fresh `git clone` of the same SHA, cargo 1.100.0) | independent re-derivation | language LOC, tracked file count, `go.mod`/`go.work`, workflow count, Dockerfile count, `cargo metadata`, `<REDACTED>` census, manifest parse |

The two hosts agreed on every figure except `[workspace] members`, where the disagreement was a
method fault on **both** sides and not a disagreement about the repository. The fresh clone landed
on the same commit (`f06c3cc7fdf61d75e8aa9f8d0feade068760d308`), so the comparison is like-for-like.

## What is not claimed

No build, no test run, no CI result. `cargo metadata --no-deps` resolves no dependencies and is the
only cargo command used.
