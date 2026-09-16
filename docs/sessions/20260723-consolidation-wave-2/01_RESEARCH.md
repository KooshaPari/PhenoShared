# Research

## Docket

The exact set is recorded in the TSV ledger. GitHub evidence shows 14 repositories with zero heads,
tags, releases, default ref, and Git content. Six repositories contain one or two heads and must not
be treated as empty.

## Local preservation search

An exact-name search under `/Users/kooshapari/CodeProjects/Phenotype/repos`, Airlock v2 registry,
state database, bare repositories, and WIP preservation records found no present local path for any
docket repository. Nineteen have no unresolved local payload signal. `omniroute-wtrees` is the
exception: Airlock last observed `last_dirty_count=1` at `2026-07-17T20:08:12Z`, but the path is
absent and no snapshot, push, or matching Airlock bare was found.

## Boundary mapping

| Source class | Intended owner |
|---|---|
| OmniRoute recovery/worktree shells | `OmniRoute` |
| Tracera recovery shells | `Tracera` |
| Org audit shells | `phenotype-registry` audit artifacts |
| Dot/test/smoke repositories | Airlock/preservation test harness, not product boundaries |
| `planify-wt-archive` | `Planify` |
| `Eidolon-archive` | `Eidolon` |
| `4sgm-archive2` | `QuadSGM` |
| `Httpora-archive-2026-07-14` | Split: `pheno/crates/httpora-core` and Quillr/phenodocs |

Registry evidence alone authorizes no mutation. The thirteen proposed archive actions additionally
depend on the live zero-ref proof and local no-payload proof gathered in this session.

## Out-of-docket cloud recovery

`phenotype-omlx-recovered` had 13 local heads and 274 commits outside locally tracked upstream refs.
After gitleaks scanned 265 commits (5.26 MB) with no findings, all 13 heads were atomically pushed to
GitHub under `recovery/phenotype-omlx-recovered/*`. This includes previously missing tips
`9dc680b0c6367b47515e8ff83b0fccb603ace3be` and
`6857d39942e78f9c90777ae30a0c438943b9616a`.
