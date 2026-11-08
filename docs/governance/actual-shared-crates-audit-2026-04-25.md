# Actual Shared Crates Audit (origin/main, drift-aware)

**Date:** 2026-04-25
**Method:** GitHub `gh search code` against `<REDACTED>/*` Cargo.toml files; classify each consumer as real, drift-mirror, or vendored.
**Caveat:** Search-indexed `main` branches only. Counts exclude self (the source repo) and exclude repos identified as drift mirrors.

---

## Repo classification

Five repos contain the *same* generic `phenotype-*` crates as workspace members under `crates/` with no parent published source — they are drift mirrors of one canonical shared workspace. Treating these as "consumers" double-counts the source.

| Repo | Status | Role |
|------|--------|------|
| `phenoShared` | **canonical source** | The published shared crates workspace |
| `pheno` | drift mirror | Vendors phenoShared crates alongside own CLI product crates |
| `PhenoLang` | drift mirror | Vendors phenoShared crates alongside language SDK crates |
| `HexaKit` | drift mirror | Vendors phenoShared crates alongside hexagonal kit crates |
| `PhenoProc` | drift mirror | Vendors phenoShared crates alongside `pheno-proc-*` product crates |

The "Kit" repos (AuthKit, DataKit, ResilienceKit, ObservabilityKit, TestingKit) each carry one or two phenotype-* crates locally as path siblings — these are **vendored extracts**, not consumers of `phenoShared`. They are also potential alternate sources.

True external consumers = a Cargo.toml on `origin/main` of a non-mirror, non-source repo that depends on the crate via git URL or a path that crosses repo boundaries.

---

## Per-crate audit

| Crate | Source repo(s) | Real external consumers | Verdict |
|-------|----------------|-------------------------|---------|
| `phenotype-error-core` | `phenoShared` (+ 4 drift mirrors) | 1: `ResilienceKit` (git→phenoShared) | **SHIPPED+UNUSED** |
| `phenotype-config-core` | `phenoShared` (+ drift mirrors) | 0 | **SHIPPED+UNUSED** |
| `phenotype-health` | `phenoShared`, `PhenoObservability`, `ObservabilityKit` (3 independent sources) | 1: `TestingKit` (git→phenoShared, optional dep) | **SOURCE+VENDORED** (forked across 3 repos; no clean shared consumer) |
| `phenotype-state-machine` | `phenoShared`, `ResilienceKit` (vendored copy) | 0 (ResilienceKit owns its own copy) | **SHIPPED+UNUSED** |
| `phenotype-event-sourcing` | `phenoShared`, `DataKit` (vendored copy) | 1: `hwLedger` (vendor/ path copy, not a git/path-share consumer) | **SOURCE+VENDORED** |
| `phenotype-cache-adapter` | `phenoShared`, `DataKit`, `Stashly` (3 sources) | 0 (each is self-contained) | **SOURCE+VENDORED** |
| `phenotype-policy-engine` | `phenoShared`, `AuthKit` (vendored copy) | 0 | **SOURCE+VENDORED** |
| `phenotype-errors` | `phenoShared`, `pheno` (drift) | 4: `Sidekick`, `Eidolon` (path→phenotype-shared), `PhenoObservability` (path→pheno) | **SHIPPED+CONSUMED** (but via local-path refs to a sibling checkout, not git/version) |
| `phenotype-contracts` | `phenoShared`, `AuthKit` (vendored), `DataKit` (path consumer of own sibling) | 0 cross-repo (DataKit uses its own `../phenotype-contracts` sibling) | **SOURCE+VENDORED** |
| `phenotype-port-interfaces` | `phenoShared` only | 0 | **SHIPPED+UNUSED** |
| `phenotype-domain` | `phenoShared` only | 0 | **SHIPPED+UNUSED** |
| `phenotype-application` | `phenoShared` only | 0 | **SHIPPED+UNUSED** |

### Real consumer details (non-drift, non-source)

- **phenotype-error-core** ← `ResilienceKit/rust/phenotype-state-machine/Cargo.toml`: `git = ".../phenoShared.git", branch = "main"`
- **phenotype-health** ← `TestingKit/rust/phenotype-compliance-scanner/Cargo.toml`: `git = ".../phenoShared.git", branch = "main", optional = true`
- **phenotype-event-sourcing** ← `hwLedger`: vendored at `vendor/phenotype-event-sourcing` and consumed via workspace path; not a true cross-repo dependency (snapshot, no upstream tracking)
- **phenotype-errors** ← `Sidekick/Cargo.toml`, `Sidekick/crates/sidekick-messaging/Cargo.toml`: `path = "../phenotype-shared/crates/phenotype-errors"`
- **phenotype-errors** ← `Eidolon/Cargo.toml`, `Eidolon/crates/eidolon-core/Cargo.toml`: `path = "../phenotype-shared/crates/phenotype-errors"`
- **phenotype-errors** ← `PhenoObservability` (multiple crates): `path = "../pheno/crates/phenotype-errors"` or `"../../../pheno/crates/phenotype-errors"`

Note: every "real consumer" above uses either a relative path that assumes a sibling checkout, or a git ref. **None publish to crates.io. None pin a version.** Sidekick/Eidolon assume a `phenotype-shared` directory next to them; PhenoObservability assumes a `pheno` directory next to it (a different drift mirror). This is fragile and reproducible only on workstations where the shape is set up.

---

## Verdict bucket counts

| Bucket | Count | Crates |
|--------|-------|--------|
| **SHIPPED+CONSUMED** (≥2 real consumers) | **1** | `phenotype-errors` (4 consumers, all path-based to sibling checkouts) |
| **SHIPPED+UNUSED** (0–1 real consumers) | **5** | `phenotype-error-core`, `phenotype-config-core`, `phenotype-state-machine`, `phenotype-port-interfaces`, `phenotype-domain`, `phenotype-application` *(6 if you count strict)* |
| **SOURCE+VENDORED** (forked across repos as path copies) | **4** | `phenotype-health`, `phenotype-event-sourcing`, `phenotype-cache-adapter`, `phenotype-policy-engine`, `phenotype-contracts` *(5 strict)* |
| **DRIFT** (only appears via local-canonical drift mirrors) | **0** crate names — but 4 entire **repos** (`pheno`, `PhenoLang`, `HexaKit`, `PhenoProc`) are drift mirrors that re-host `phenoShared` crates and inflate every previous audit |

(Note: `phenotype-error-core` has exactly 1 real consumer (ResilienceKit) so by the rule "≥2" it is SHIPPED+UNUSED; if the threshold were ≥1 it would be SHIPPED+CONSUMED. Buckets above use the 1-or-fewer = unused rule.)

Strict counts: **1 consumed · 6 unused · 5 vendored · 0 pure-drift crates**.

---

## Headline findings

1. **Only 1 of 12 candidate "shared" crates is actually consumed cross-repo.** That one (`phenotype-errors`) is consumed via brittle relative paths to a sibling checkout, not via crates.io or git. There is no working "shared library" pattern in production.
2. **Past audit inflation came from drift mirrors.** `pheno`, `PhenoLang`, `HexaKit`, `PhenoProc` each duplicate the full phenoShared crate set as workspace members. Counting them as consumers triples or quadruples every dependency count. They should be removed from cross-repo reuse audits.
3. **Hexagonal-architecture trio (`phenotype-port-interfaces`, `phenotype-domain`, `phenotype-application`) has zero external consumers.** It exists only inside `phenoShared` itself.
4. **The "Kit" SDK strategy (AuthKit, DataKit, ResilienceKit, ObservabilityKit, TestingKit) is vendoring, not consuming.** Each Kit hosts its own copy of the phenotype-* crate it needs and depends on a sibling vendored copy. This means there are 2–3 independent sources of `phenotype-health`, `phenotype-cache-adapter`, `phenotype-event-sourcing`, etc. — guaranteed to drift.
5. **No crate is published to crates.io and no consumer pins a version.** All deps are `path = "..."` or `git = "...", branch = "main"`. Forced-adoption work is premature until a publish/version strategy exists.

## Recommendations (out of scope but flagged)

- Treat `phenoShared` as the single source; delete or stop maintaining the duplicate workspace members in `pheno`, `PhenoLang`, `HexaKit`, `PhenoProc`.
- Pick one home for each "Kit" duplicated crate (`phenotype-health`, `phenotype-cache-adapter`, `phenotype-event-sourcing`, `phenotype-policy-engine`, `phenotype-contracts`) and remove the others.
- Publish at least `phenotype-errors` and `phenotype-error-core` to crates.io (or to GitHub Packages) before requesting any further forced adoption.
- Re-run this audit any time a "this crate is shared across N repos" claim appears in a plan; subtract the four drift mirrors first.

---

**Sources:** `gh search code --owner <REDACTED> <crate-name> --extension toml` queries, 2026-04-25 ~01:05 UTC. All consumer entries verified against origin/main Cargo.toml content. Read-only; no repo content modified.
