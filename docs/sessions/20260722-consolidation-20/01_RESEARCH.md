# Research

## Evidence Summary

- All 20 named repositories existed and were unarchived at intake.
- Live metadata confirms only `PriceyApp` is a fork. `router-docs` and `template-commons` are private
  non-forks and remain mutation-blocked by incomplete absorption evidence.
- Historical scripts assume `main`, but eight source repositories have non-`main` default branches.
- Batch A contains placement errors; its conclusions cannot authorize mutation without correction.
- Disk pressure is critical: 98% used with about 22 GiB free. Evidence collection must use partial bare
  clones rather than full working clones.
- The ecosystem validator baseline is known to fail with 18 reachable repositories, 2 unreachable
  repositories, 17 drift findings, and 47 total items.
- The docs build baseline is blocked at
  `docs/specs/pheno-specs/specs/platform/build-system/PRD.md:65:60` by a Vue missing-end-tag error.
- `AgilePlus-recovery-20260714` has a sole head, `recovery/isolated-20260714`, at exact commit
  `0aafdf9692c11abb6e426f36857aeec7bb6cd942`; canonical AgilePlus contains that exact commit and
  tree `eb82ced16353219d85aa83c925819ae48cb36c16` with the exact head. It was the sole source to
  reach READY and is now `ARCHIVED-PRESERVED / complete`.
- `AgilePlus-recovery-evidence-20260714` remains HOLD as unique preservation evidence.
- The authorized transaction completed for docket #1. The source is now
  `KooshaPari/zz-archive-AgilePlus-recovery-20260714`, with `archived=true`, `private=true`,
  `fork=false`, default branch `recovery/isolated-20260714`, one branch, zero tags, and unchanged
  `pushed_at=2026-07-16T00:20:23Z`.
- Postverification confirmed exact commit `0aafdf9692c11abb6e426f36857aeec7bb6cd942` and tree
  `eb82ced16353219d85aa83c925819ae48cb36c16`; canonical AgilePlus retains the exact recovery ref,
  commit, and tree. The old name redirects to the renamed archived repository. No deletion occurred.

## Decision Rationale

Existence and unarchived state do not prove safe absorption or archival. Default-branch drift, Batch A
misplacements, and incomplete SHA/content parity require a preservation-first, verify-before-mutate
workflow. The one proven exception, `AgilePlus-recovery-20260714`, passed immediate preflight and
was renamed to `zz-archive-AgilePlus-recovery-20260714` and archived. It is preserved, not deleted;
the other 19 docket entries remain HOLD or VERIFY-ONLY.

## Tranche 2 Evidence

| Candidate | Evidence | Disposition |
|---|---|---|
| `agileplus-spec-harmonizer-tool-archive-2026-07-14` | Source `main` and `v0.1.0` commit/tree pairs exactly match AgilePlus namespaced head and tag; zero releases | PARITY-PROVEN / POLICY-HOLD (`archive=false`) |
| `4sgm-archive` | Four source heads are absent from `QuadSGM`; canonical `main` has diverged | HOLD |
| `Parpoura-archive` | One of four heads is exact in `Parpoura`; three Dependabot heads are absent | HOLD |
| `phenoResearchEngine-archive` | Commit/tree is retained as a canonical ancestor, but exact `local/main` ref is absent | HOLD |
| `home-recovery-2026-07-archive` | Unique `local/main` has no proven canonical parent | HOLD |
| `phenotype-monorepo-state-archive` | Five heads representing four unique commits are absent from `phenotype-registry`; original parent is deleted | HOLD |

The complete tranche-2 ref, commit, tree, and parent-result ledger is
`artifacts/tranche-2-ref-evidence.tsv`.

## Tranche 3 Evidence

| Candidate | Refs | Evidence | Disposition |
|---|---:|---|---|
| `phenotype-registry-archive` | 23 | No complete namespaced ref set; nine commit/tree objects absent and 14 object-present heads still lack complete namespaced preservation | HOLD |
| `phenotype-org-audits-archive2` | 7 | Seven of seven exact namespaced heads and trees preserved in `phenotype-registry` | PARITY-PROVEN / POLICY-HOLD |
| `PhenoRuntime-archive` | 3 | Governance head exact in `PhenoRuntime`; two Dependabot objects absent and registry target evidence conflicts between `PhenoRuntime`, `pheno`, and a nonexistent legacy collection | HOLD |
| `ResilienceKit-archive` | 7 | Local head exact in `ResilienceKit`; six Dependabot objects absent and Python/Rust ownership is split across current and future SDK boundaries | HOLD |
| `phenotype-shared-archive` | 2 | Both source commit/tree objects absent from `phenotype-shared` | HOLD |
| `agent-user-status-archive` | 7 | All seven commit/tree objects absent from `phenotype-tooling`; designated crate path absent on main | HOLD |

The nine missing registry-archive commits begin `63b8817`, `82953cf`, `4dd7bfa`, `3b16f0d`,
`75c8950`, `9248110`, `62be997`, `f10ced4`, and `143a58c`. The complete seven-head
org-audit namespace is rooted at `archive/phenotype-org-audits/`.

The authoritative 49-head tranche-3 ledger is `artifacts/tranche-3-ref-evidence.tsv`.

## Tranche 4 Evidence

| Candidate | Refs | Evidence | Disposition |
|---|---:|---|---|
| `AgilePlus-recovery-evidence-20260714` | 1 | Private 112,012,704-byte DATA_ONLY forensic package with raw objects, reflogs, bundles, stashes, patches, and untracked archives; sensitive by construction and not replaced by ordinary refs | KEEP-STANDALONE / PRIVATE |
| `PriceyApp` | 1 | Live fork of `mobile-next/PriceyApp`; no Phenotype parent boundary authorizes mutation | KEEP-FORK / UNTOUCHED |
| `Quillr` | 25 | Restored live remote conflicts with prior deletion/absorption records; no complete 25-ref map to pheno and phenodocs targets | HOLD |
| `Stashly` | 17 heads + 1 tag | Registry history conflicts, but later user directive makes the unique cache product canonical standalone | KEEP-STANDALONE |
| `router-docs` | 1 | Source commit `c4d19f1e3fa6f2c4bfe671428b64aea9227efb00` and tree `e3c1e59321aefeea05e5c077666c0ed5dbf3e647` are absent from OmniRoute | HOLD / IMPORT REQUIRED |
| `template-commons` | 5 heads + 3 tags | Five unique commit/tree pairs, including the shared three-tag target, are absent from `phenokits-commons`; this is not currently a fork | HOLD / IMPORT REQUIRED |
| `phenotype-teamcomm` | 8 | Protected five-crate Rust coordination workspace; seven unique head commits absent from pheno and ShareCLI boundary unresolved | KEEP-STANDALONE |
