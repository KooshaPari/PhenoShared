# Current Estate Scorecard

Date: 2026-08-02

Evidence window: `2026-08-01 08:32:46Z-08:35:27Z`

Evidence source: [PR #450](https://github.com/KooshaPari/phenotype-registry/pull/450), head
`b31203dd4b72afd81fb608e7c1b91b5438931a7c`

Live promotion source: GitHub API snapshots of [PR #453](https://github.com/KooshaPari/phenotype-registry/pull/453),
[PR #454](https://github.com/KooshaPari/phenotype-registry/pull/454),
[PR #455](https://github.com/KooshaPari/phenotype-registry/pull/455),
[PR #456](https://github.com/KooshaPari/phenotype-registry/pull/456),
[PR #448](https://github.com/KooshaPari/phenotype-registry/pull/448), `main`, and branch protection at
2026-08-02 08:01:40Z.

Baseline: `phenotype-registry/main` at `834c721f409b00294c6117a6b7e84f0c1be51e66`

## Live promotion update

The protected integration lane has advanced since the contradiction snapshot:

| Change | Evidence | State |
|---|---|---|
| Workflow/docs integration | PR #453, merge `73220f4853886f26b6195f1fb2d209246befb3ed` | MERGED 2026-08-01 23:33:56Z |
| Dependency maintenance | PR #454, merge `7ca1252fa95de09c9f256c5f3196d00ae80617e5` | MERGED 2026-08-02 01:00:48Z |
| Scorecard promotion | PR #455, merge `6d5aece8319b83400c8a79bb05ea777d8efc5fd0` | MERGED 2026-08-02 02:01:45Z |
| Post-455 provenance scorecard | PR #456, source `3311d6d76629466d4bff53d4fd587e85171b5b25`, merge `427506fa8a25ac1fb1d400e5c4c7205e11b0b9f4` | MERGED 2026-08-02 05:57:11Z |
| Runtime-config docs repair | PR #448, source `bfa56a316ef3ec5174a6312f491cd41847d91ce6`, merge `834c721f409b00294c6117a6b7e84f0c1be51e66` | MERGED 2026-08-02 07:21:21Z |
| Current default branch | `main` at `834c721f409b00294c6117a6b7e84f0c1be51e66` | authoritative snapshot 2026-08-02 08:01:40Z |

Branch protection now requires **zero approving reviews** for this single-identity repository,
while retaining strict `ci / lint` and `ci / test` contexts, conversation resolution, linear
history, and no force-push or deletion allowance. The required contexts are green on the current
`main` head. Non-required baseline failures (SonarCloud, build, Scorecard, and SBOM generation)
remain visible on the head and are not a release-readiness claim.

Preserved source refs: `ci/integration-gates-20260801` at
`380f5b563a220a26da914bc549843977cf70dbf2`, the Dependabot source at
`d3f47bc8ceba5234942561e443f6930016d9533e`, and
`docs/scorecard-current-main-20260802` at
`2f4664eeb894c16a005b4db43b859a271e6d0e7f`. The #448 source ref
`fix/docs-pheno-runtime-config-markup-20260801` at
`bfa56a316ef3ec5174a6312f491cd41847d91ce6` and the #456 source ref
`docs/scorecard-post455-20260802` at `3311d6d76629466d4bff53d4fd587e85171b5b25` are also retained. Airlock refs retain the integration,
security correction, and scorecard heads; the local repair payload is separately retained at
`wip/20260802T0408-18c7e17e73387238`.

## Executive state

The current GitHub metadata snapshot resolves all twenty intake names into four observable
classes. It contradicts the older consolidation packet's statement that only docket #1 was
archived and the other nineteen remained HOLD or VERIFY-ONLY. The snapshot is authoritative for
current repository metadata, but it does not identify the actor, transition event, or sponsor
authorization. This scorecard therefore records a contradiction, not an unauthorized-action
finding.

```text
11 archive-named target/archived  +  2 archived in place  +  3 owner API path unavailable  +  4 active  = 20 intake names
```

## Gate scorecard

| Gate | Result | Evidence / exit condition |
|---|---|---|
| Intake coverage | PASS | PR #450 records 20/20 intake names and full default-branch metadata |
| Current cloud classification | PASS | 11 archive-named target/archived, 2 in-place archived, 3 owner API paths unavailable under current credentials, 4 active |
| Ref/evidence preservation | HOLD | Preserve every current head and locally retained source artifact; 404 rows need durable bundles, redirects, or audit evidence |
| Transition provenance | BLOCKED | Obtain GitHub actor/time receipts for each rename/archive transition |
| Sponsor authorization | BLOCKED | Obtain an explicit sponsor receipt or prior approved execution packet; current metadata is not authorization |
| Registry reconciliation | BLOCKED | Do not edit `registry/disposition-index.json` until provenance and authorization gates pass |
| Protected CI promotion | DEFERRED | Resume after contradiction gates and independent registry/CI review are resolved |

## Protected-review checkpoint

PR #443's workflow recovery and the #444/#447 integration content were promoted through PR #453;
PR #454 then landed on top of that merge, PR #455 published this scorecard, PR #456 recorded the
post-455 provenance state, and PR #448 landed the runtime-config markup repair on the resulting
default branch. The source PRs remain
historical/provenance records and
are not treated as additional merge candidates. The zero-approval policy removes the impossible
single-identity review gate, but it does not close the independent provenance, authorization, or
registry-reconciliation gates below.

## Current-state classes

| Class | Count | Safe conclusion | Next proof |
|---|---:|---|---|
| Archive-named target/archived | 11 | Current `zz-archive-*` path and default head are observable | GitHub audit actor/time plus sponsor receipt |
| Archived in place | 2 | `router-docs` and `template-commons` remain addressable and archived | Archive event and boundary receipt |
| Owner API path unavailable | 3 | `AgilePlus-recovery-evidence-20260714`, `agileplus-spec-harmonizer-tool-archive-2026-07-14`, and `4sgm-archive` returned 404 under the current credentials | Search/redirect/audit evidence or a durable preservation bundle; do not infer deletion intent |
| Active | 4 | `PriceyApp` is an untouched fork; `Quillr`, `Stashly`, and `phenotype-teamcomm` are active non-forks | Preserve current refs and re-check disposition before any proposal |

## Reconciliation policy

Until both blocked gates close:

1. Freeze destructive follow-up: no restore, archive, unarchive, rename, delete, force-push, or
   history rewrite.
2. Preserve current remote refs and any local/source evidence already retained.
3. Reconcile the session packet and registry only through a separately reviewed,
   sponsor-approved change.
4. Keep `PriceyApp` untouched as a fork and keep the three 404 rows unresolved rather than
   recreating or deleting anything.

The older packet remains useful historical evidence, but its prior disposition totals must not be
treated as current cloud truth until this reconciliation completes. PR #450 is the current
metadata evidence window for this scorecard; it does not authorize remote or registry mutation.

## Next exit criteria

```text
PR #450 evidence
      |
      +--> immutable per-row refs / bundles
      +--> actor + transition timestamps
      +--> sponsor authorization receipt
                    |
                    v
         approved session + registry reconciliation
                    |
                    v
          resume protected CI-gated promotion
```
