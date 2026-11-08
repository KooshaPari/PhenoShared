# ADR: Shared-Crate Distribution Strategy

**Date:** 2026-04-25
**Status:** Proposed
**Decision owner:** koosha (org)
**Related:**
- `docs/governance/actual-shared-crates-audit-2026-04-25.md` (consumer audit)
- `docs/governance/phase1-crates-post-archive-audit-2026-04-25.md` (post-archive state)
- branch `adr/canonical-home-verification-2026-04-25` (canonical-home work)

---

## 1. Background

The 2026-04-25 actual-consumer audit produced sobering findings. Of 12 candidate "shared" `phenotype-*` crates in `phenoShared`, only **1** (`phenotype-errors`) has more than one real cross-repo consumer, and even that crate is consumed via `path = "../phenotype-shared/crates/..."` references that assume a sibling checkout. Every other cross-repo dependency is either:

- a `git = "...phenoShared.git", branch = "main"` reference (ResilienceKit, TestingKit) — pinned to a moving target with no version, no semver, no rollback;
- a relative-path reference to a sibling working copy (Sidekick, Eidolon, PhenoObservability) — only reproducible on workstations where directories happen to be laid out correctly;
- a vendored snapshot (`vendor/phenotype-event-sourcing` in hwLedger; AuthKit/DataKit/ResilienceKit local copies) — divergent from the canonical source.

**No crate is published to crates.io. No consumer pins a version.** Any forced-adoption migration done in this session is therefore built on an unstable foundation: the moment `phenoShared@main` lands a breaking change, every git-ref consumer rebuilds against it without warning.

This ADR selects a distribution strategy that turns "shared crate" into a real engineering primitive instead of a slogan.

---

## 2. Options

### Option A — Publish to crates.io

Each shared crate is published to the public crates.io registry. Consumers depend by version: `phenotype-errors = "0.2"`.

**Pros:** Real semver. `cargo update -p` works. Yanking is supported. docs.rs auto-generates documentation. No auth required for consumers. Standard ecosystem practice.
**Cons:** Public — every consumer of `phenotype-*` becomes visible on crates.io. Requires LICENSE on every crate (most carry none). Names may collide with squatters. Yanking is sticky; mistakes cost reputation. Requires coordinated release process across the workspace.

### Option B — Versioned git tags

Crates remain unpublished; consumers pin to git tags rather than `branch = "main"`: `phenotype-errors = { git = "...", tag = "phenotype-errors-v0.2.0" }`.

**Pros:** No public exposure. Works today with no infrastructure. Per-crate tags allow independent versioning inside a single workspace. Consumers can pin and upgrade deliberately. Trivial rollback (re-pin previous tag).
**Cons:** No transitive resolution — every consumer has to declare every transitive dep explicitly. No `cargo update -p`. No docs.rs. Tag discipline must be enforced by release tooling. Slow `cargo` resolves on cold caches because each git fetch is full-history.

### Option C — Workspace `path =` siblings

Continue today's pattern: each consumer references `path = "../phenoShared/crates/..."` and assumes the working copy layout.

**Pros:** Zero infrastructure. Edits in `phenoShared` are seen instantly by consumers. Best DX inside a single mega-checkout.
**Cons:** Only works inside one repo or a curated multi-repo working copy. CI cannot reproduce without checking out every repo into the right relative location. Production releases break the moment a consumer is built outside that layout. **This is the de-facto current state for `phenotype-errors`, and the audit flagged it as fragile.**

### Option D — GitHub Packages cargo registry (private)

Publish to a private GitHub Packages cargo registry scoped to the `<REDACTED>` org. Consumers configure `~/.cargo/config.toml` with the registry and an auth token.

**Pros:** Private (no public exposure). Real versioning. Works with `cargo publish`. Org-scoped access control via GitHub.
**Cons:** GitHub Packages cargo support is **alpha / community-driven** (`cargo-quickinstall`, `cargo-registry-github`); no first-party Cargo support as of 2026-04. Requires every developer and CI runner to provision auth tokens. Cold builds are slow until cached. If GitHub Packages billing/quotas hit, all builds fail.

### Option E — Status quo `branch = "main"`

Leave consumers pointing at `git = "...", branch = "main"`. Forced-adoption migrations continue without versioning.

**Pros:** No work required.
**Cons:** Every breaking change in `phenoShared` propagates instantly to every consumer's next `cargo build`. No reproducible builds. No rollback. **Audit explicitly named this as the failure mode that motivated this ADR.**

---

## 3. Decision

**Adopt Option B (versioned git tags) immediately, then Option A (crates.io) when the crates stabilize.**

Rationale:
- Option B is achievable today with no new infrastructure and no public exposure. It immediately replaces the fragile `branch = "main"` pattern and the sibling-`path =` pattern.
- Option A delivers the better long-term ecosystem story (docs.rs, semver enforcement, third-party discoverability) but is premature: most candidate crates are unstable, lack LICENSE, and have <2 consumers — publishing them today fixes the names and pollutes crates.io with low-value packages.
- Option C is rejected as the dominant form because it does not survive CI; Option D is rejected because the tooling is alpha; Option E is rejected because the audit named it as the problem.
- Once a crate clears the promotion bar (≥2 external consumers, LICENSE present, public API frozen for ≥1 release cycle), it is promoted from B to A.

---

## 4. Migration plan (per-crate publishing checklist)

Each crate transitioning from `branch = "main"` to a tagged release (Option B) must complete:

1. **Add LICENSE** (default: dual MIT/Apache-2.0; record in `Cargo.toml` `license` field).
2. **Set `version` in `Cargo.toml`** starting at `0.1.0` (or current effective state if commits exist).
3. **Add README.md** with: purpose, consumer list, installation snippet (using `tag = "..."`).
4. **Add docs.rs metadata** in `Cargo.toml`: `[package.metadata.docs.rs]` with feature flags. (Used when promoted to Option A.)
5. **Tag release:** `git tag <crate>-v<version>` on `phenoShared` `main`; push tag.
6. **CHANGELOG.md** entry under the new version.
7. **Update consumers** (in a follow-up PR per consumer repo): replace `branch = "main"` with `tag = "<crate>-v<version>"`.
8. **CI guard:** add a workspace lint that rejects new `branch = "main"` git deps for `phenotype-*` crates.

Promotion from Option B to Option A requires, additionally:

- ≥2 external real consumers (per the audit's definition);
- Public API frozen for ≥1 minor-release cycle without breaking change;
- `cargo publish --dry-run` clean;
- `cargo publish` performed by the release agent, not interactively.

---

## 5. Open decisions surfaced for user

These choices are not made by this ADR and require explicit user direction:

1. **Publish publicly (Option A) vs keep private (Option D / Option B-only)?** Public publishing exposes the `phenotype-*` brand and source code on crates.io; private keeps the org boundary. Default in this ADR: public, on the assumption that the ecosystem is intended to be open.
2. **Which crates are publish candidates first?** Recommend: `phenotype-errors` (only consumed crate) and `phenotype-error-core` (one external consumer). All others are SHIPPED+UNUSED or SOURCE+VENDORED — defer.
3. **Single workspace version or independent per-crate?** Recommend independent per-crate (each crate tagged separately); the workspace-wide-version pattern collapses unrelated breaking changes into shared bumps.
4. **Vendored copies in Kit repos (AuthKit, DataKit, ResilienceKit, ObservabilityKit, TestingKit) — keep, dedupe, or delete?** Out of scope for this ADR but blocks promotion to Option A: the same crate name cannot be published from multiple sources.
5. **Drift mirrors (`pheno`, `PhenoLang`, `HexaKit`, `PhenoProc`) — delete duplicate `phenotype-*` crate copies?** Same blocker; Option A requires a single source repo per crate name.
6. **Tag-naming convention:** `<crate>-v<semver>` (recommended, scoped) vs `v<semver>` (workspace-wide). Decision affects step 5 of the migration checklist.

---

**Next step:** user picks a tag-naming convention and confirms public-vs-private, then a follow-up implementer ADR/spec executes the per-crate checklist starting with `phenotype-errors`.
