# L9 — Build & release pipeline

## Scope
Cross-compilation matrix, reproducible builds, SBOM emission, container image, publish flow, SLSA Build L2/L3, provenance, locked deps across the 4-repo Phenotype bloc (AgilePlus + thegent + Tracely + Tracera).

## SOTA 2026
- `cargo dist` or `release-plz` for Rust workspace versioning + multi-crate release.
- `maturin` (PyO3) for Rust+Python hybrid crates with `abi3` for many-version wheels.
- `cibuildwheel` for cross-platform wheel builds (manylinux, musllinux).
- SBOM: CycloneDX 1.5 (OWASP standard) emitted as CI artifact per release; SPDX 2.3 as secondary.
- Container: distroless (`gcr.io/distroless/cc-debian12`) or `alpine` with multi-stage builds; `FROM scratch` for pure-Rust.
- SLSA Build L2 minimum for public packages; L3 for regulated/enterprise.
- `SOURCE_DATE_EPOCH` for reproducible builds; locked lockfiles (`Cargo.lock`, `uv.lock`, `package-lock.json`/`bun.lock`/`pnpm-lock.yaml`, `go.sum`).
- `actions/attest-build-provenance` (official GitHub) or `slsa-framework/slsa-github-generator` for L2.
- npm `--provenance`, `cargo --config-deny` (audit), `gh attestation verify`.

## Phenotype state

### AgilePlus (45+ Rust crates, library + CLI + API server)

- `AgilePlus/.github/workflows/release.yml:1-90` — `release-plz/action` for automated release PRs + `cargo publish` on merge of `release-plz-*` branch — **status ✓**
- `AgilePlus/release-plz.toml:1-40` — workspace config: `changelog_update`, `git_release_enable`, `git_tag_enable`, `pr_labels = ["release"]` — **status ✓**
- `AgilePlus/.github/workflows/release-attestation.yml:1-100` — `slsa-framework/slsa-github-generator/attest-build-provenance@v1` after `cargo build --release --locked --workspace --all-targets` — **status ✓** (SLSA Build L2)
- `AgilePlus/.github/workflows/release-attestation.yml:60-79` — stages source tarball + binaries + `BUILD_MANIFEST.txt` with sha/runner/rustc/cargo/built_at — **status ✓**
- `AgilePlus/.github/workflows/release-attestation.yml:74` — `actions/upload-artifact@043fb...` 90-day retention — **status ✓**
- `AgilePlus/.github/workflows/ci.yml:1-100` — `RUSTFLAGS: "-D warnings"`, ubuntu-24.04 + macos-latest matrix, protolock, `buf` lint — **status ✓**
- `AgilePlus/.github/workflows/deny.yml:1-50` — `cargo-deny` weekly, `--locked` — **status ✓**
- `AgilePlus/deny.toml:1-50` — `[advisories]`, `[licenses]` (Apache/BSD/MIT/MPL-2.0/etc), `[bans]`, `[sources]` (unknown-registry = warn, unknown-git = deny) — **status ✓**
- `AgilePlus/Cargo.lock` — present, committed — **status ✓**
- `AgilePlus/clippy.toml:1-10` — `msrv = "1.88.0"`, `avoid-breaking-exported-api = true` — **status ✓**
- `AgilePlus/.github/workflows/ci.yml` — uses SHA-pinned actions (`actions/checkout@df4cb1c...`) — **status ✓**
- **No `cargo dist` workflow** — uses `release-plz` (functionally equivalent) — **status ✓**
- **No `cross` / cross-compilation matrix** — `ci.yml` builds on native `ubuntu-latest` and `macos-latest` only; no `aarch64-unknown-linux-musl` target — **status △**
- **No SBOM emission** — no `cyclonedx-bom`/`cargo-cyclonedx` step in any workflow — **status ✗**
- **No Dockerfile** — AgilePlus is a CLI + library crate collection; no published container image — **status △** (acceptable for lib)
- **No `SOURCE_DATE_EPOCH`** in any release workflow — **status ✗**
- **No SLSA Build L3** (only L2 via slsa-github-generator) — **status △**

### thegent (25+ Python+hybrid crates, Rust pyo3 + pure Python)

- `thegent/crates/thegent-{fs,subprocess,router,policy,resources,cache,git}/Cargo.toml` — `pyo3 = { version = "0.29", features = ["abi3-py312", "extension-module"] }` — **status ✓**
- `thegent/crates/thegent-router/pyproject.toml:2-3` — `requires = ["maturin>=0.14,<0.15"]`, `build-backend = "maturin"` — **status △** (split version constraints across crates — drift risk)
- `thegent/crates/thegent-policy/pyproject.toml:2-3` — `requires = ["maturin>=1.0,<2.0"]` — **status ✓**
- `thegent/crates/thegent-git/pyproject.toml:2-3` — `requires = ["maturin>=1.5,<2.0"]` — **status ✓**
- `thegent/crates/*/pyproject.toml` — `[tool.maturin]` sections — **status ✓**
- `thegent/pyproject.toml:1-15` — `build-system = hatchling`, project name `thegent`, deps on `httpx`, `typer`, `pydantic`, `psutil>=7.0.0` — **status ✓**
- `thegent/uv.lock` (664KB) — committed, locked — **status ✓**
- `thegent/.cargo/config.toml:1-5` — `git-fetch-with-cli = true` — **status ✓**
- `thegent/.github/workflows/release-attestation.yml:1-100` — `slsa-framework/slsa-github-generator/attest-build-provenance@v1`, `cargo build --release --locked --workspace --all-targets` — **status ✓**
- `thegent/.github/workflows/release-plz.yml:1-50` — release-plz with `CARGO_REGISTRY_TOKEN` — **status ✓** (but only for Rust crates, no PyPI)
- `thegent/.github/workflows/python-ci.yml:1-30` — pyright strict, `actions/setup-python@v5`, Python 3.13 — **status ✓**
- `thegent/.github/workflows/cargo-deny.yml:1-50` — weekly `cargo-deny` — **status ✓**
- `thegent/templates/operational/docker/Dockerfile.python` — Docker template exists — **status ✓**
- `thegent/templates/operational/docker/Dockerfile.typescript` — Docker template exists — **status ✓**
- `thegent/templates/operational/docker/docker-compose.yml` — exists — **status ✓**
- `thegent/.github/workflows/scorecard.yml:1-50` — OSSF Scorecard weekly — **status ✓**
- **No cibuildwheel** for maturin wheels — no `manylinux`/`musllinux` matrix — **status ✗**
- **No `cargo cyclonedx-bom` / `cargo-cyclonedx` step** — **status ✗**
- **No PyPI publish workflow** — `thegent-router`, `thegent-policy`, `thegent-git`, etc. are not actually published; only local install — **status ✗**
- **No `actions/attest-build-provenance` for Python** — no Python wheel provenance (would need `twine upload --attestations` or `pypa/gh-action-pypi-publish`) — **status ✗**
- **No `SOURCE_DATE_EPOCH`** in build/release — **status ✗**
- **No distroless/alpine/multi-stage Dockerfile** — only templates; runtime uses the templates — **status △**
- **Maturin version drift** — thegent-router `>=0.14,<0.15` vs thegent-policy `>=1.0,<2.0` vs thegent-git `>=1.5,<2.0` — risk of incompat — **status ✗**

### Tracely (5 Rust crates: `tracely-core`, `helix-tracing`, `tracely-sentinel`, `zerokit`, `pheno-logging-zig`)

- `Tracely/.github/workflows/ci.yml:1-50` — uses `<REDACTED>/template-commons/.github/workflows/reusable-rust-ci.yml@main` — **status △** (refs `main` branch of an external repo — SHA not pinned — supply-chain risk ✗)
- `Tracely/.github/workflows/ci.yml:46-50` — `check-cliff-template` calls `scripts/check-cliff-template.sh` — **status ✓**
- `Tracely/.github/workflows/audit.yml:1-50` — CodeQL Rust weekly + on push/PR — **status ✓**
- `Tracely/.github/workflows/deny.yml:1-50` — `cargo deny --manifest-path Cargo.toml --locked check` weekly + on PR — **status ✓**
- `Tracely/cliff.toml` — present (release notes config) — **status ✓**
- `Tracely/CODEOWNERS` — present — **status ✓**
- `Tracely/Cargo.lock` — present, committed — **status ✓**
- **No release workflow** — no `release.yml`, no `release-plz` config, no `release-attestation.yml` — **status ✗**
- **No SLSA attestation** — **status ✗**
- **No SBOM emission** — **status ✗**
- **No Dockerfile** — **status N/A** (lib)
- **No `cross` matrix** — **status △**
- **No `pheno-logging-zig` build** — directory exists but empty — **status ✗** (orphan crate)
- **External workflow @ main** (template-commons, phenotypeActions) — unpinned ref — supply-chain risk — **status ✗**

### Tracera (1 Rust crate `tracera-core` + Go + TS polyglot)

- `Tracera/Cargo.toml:1-50` — workspace root, `tracera-core` only member, `phenotype-error-core` etc. extracted to `phenoShared` — **status ✓**
- `Tracera/justfile:1-200` — comprehensive recipes: `dev`, `build`, `test`, `coverage` (cargo llvm-cov), `audit` (cargo-audit + npm audit + pip-audit + govulncheck), `deny` (cargo-deny), `grade`, `ci`, `lint`, `fmt`, `clean` — **status ✓✓**
- `Tracera/justfile:90-110` — `ci: lint test build audit deny` aggregates the full sweep — **status ✓**
- `Tracera/.github/workflows/cargo-deny.yml:1-50` — weekly `cargo deny --locked check` — **status ✓**
- `Tracera/.github/workflows/release-attestation.yml:1-100` — `slsa-framework/slsa-github-generator/attest-build-provenance@v1`, `cargo build --release --locked --workspace --all-targets` — **status ✓** (SLSA Build L2)
- `Tracera/.github/workflows/release-plz.yml:1-50` — release-plz `release-pr` — **status ✓**
- `Tracera/.github/workflows/rust-tests.yml:1-50` — `cargo hack test --workspace --each-feature --no-dev-deps` per-crate feature matrix — **status ✓**
- `Tracera/.github/workflows/governance-gates.yml:1-50` — `qa-artifact-gate`, `qa-assurance-gate`, `antipattern-detect` — **status ✓**
- `Tracera/.github/workflows/python-ci.yml:1-30` — pyright strict — **status ✓**
- `Tracera/.github/workflows/scorecard.yml:1-50` — OSSF Scorecard weekly — **status ✓**
- `Tracera/release-plz.toml` — workspace config — **status ✓**
- `Tracera/deny.toml:1-50` — `[graph]`, `[advisories]`, `[licenses]`, `[bans]`, `[sources]` all configured — **status ✓**
- `Tracera/go.mod:1-3` — `module github.com/KooshaPari/tracera`, `go 1.23` — **status ✓**
- `Tracera/Cargo.lock` — present — **status ✓**
- `Tracera/frontend/apps`, `Tracera/frontend/packages` — has `docs/package-lock.json` — **status ✓**
- **No `go test` workflow** — `go.mod` exists but no `go build` / `go test` step in any workflow — **status ✗**
- **No `npm publish` / `bun publish` workflow** — frontend packages not published — **status ✗**
- **No SBOM emission** for any language — **status ✗**
- **No Dockerfile** (lib-only) — **status N/A**
- **No `SOURCE_DATE_EPOCH`** — **status ✗**
- **No cibuildwheel** (no Python+rust hybrid in Tracera) — **status N/A**
- **No cross-compile matrix for go** — **status △**

### Cross-cutting
- All four repos: **zero SBOM emission** — `phenotype-dep-guard` has `sbom.rs:131` (CycloneDX 1.5 emitter) but it's not run in any release pipeline
- All four repos: **zero `SOURCE_DATE_EPOCH`** in any build/release
- Three of four repos (AgilePlus, thegent, Tracera) have SLSA Build L2 via `slsa-github-generator`. Tracely has **none**.
- All four repos: **no SLSA Build L3** (would need isolated builds / hermetic)
- All four repos: **no `cargo-cyclonedx` or equivalent** integrated
- AgilePlus + thegent: use `release-plz` (no `cargo dist`). Tracera: also `release-plz`. Tracely: **no release automation at all**
- Lockfiles: AgilePlus `Cargo.lock` ✓, thegent `uv.lock` ✓, Tracely `Cargo.lock` ✓, Tracera `Cargo.lock` ✓ + `docs/package-lock.json` ✓
- thegent Maturin version drift: thegent-router `>=0.14,<0.15` vs thegent-policy `>=1.0,<2.0` vs thegent-git `>=1.5,<2.0` — risk of maturin API drift across the workspace
- Tracely uses `<REDACTED>/template-commons/.github/workflows/...@main` (branch ref) and `<REDACTED>/phenotypeActions/...@main` (branch ref) — not SHA-pinned, supply-chain risk

## Gaps

1. **All four repos** — no SBOM emission in any release pipeline despite `phenotype-dep-guard` having a `sbom.rs:131` CycloneDX 1.5 emitter — wire it into `release-attestation.yml` as a post-build step — **effort: S per repo**
2. **All four repos** — no `SOURCE_DATE_EPOCH` — add `env: SOURCE_DATE_EPOCH: $(git log -1 --pretty=%ct)` to release workflows — **effort: S**
3. **Tracely** — no release workflow at all (no `release.yml`, no `release-plz`, no `release-attestation.yml`) — adopt release-plz like AgilePlus/thegent/Tracera — **effort: M**
4. **Tracely** — `pheno-logging-zig` directory exists but is empty — either implement `build.zig` + FFI logging or remove the directory — **effort: S**
5. **Tracely** — external reusable workflows pinned to `@main` not SHA — change `@main` to commit SHA in `.github/workflows/ci.yml:18,21,30` — **effort: S** (supply-chain hardening)
6. **thegent** — maturin version drift across crates (thegent-router 0.14 vs thegent-policy 1.0 vs thegent-git 1.5) — unify to `>=1.5,<2.0` in a workspace `[tool.maturin]` table — **effort: S**
7. **thegent** — no cibuildwheel for `manylinux`/`musllinux` wheel matrix — add `.github/workflows/wheels.yml` with `cibuildwheel` — **effort: M**
8. **thegent** — no PyPI publish — `pypa/gh-action-pypi-publish` for the 6+ maturin crates — **effort: M**
9. **thegent** — no Python wheel provenance (would need `twine upload --attestations` or `pypa/gh-action-pypi-publish@release`) — **effort: S**
10. **Tracera** — Go code has no CI build/test (only `cargo`) — add `go build` and `go test` job to `ci.yml` (or new `go-tests.yml`) — **effort: S**
11. **Tracera** — frontend TS packages not published — `bun publish` or `pnpm publish` workflow — **effort: M**
12. **All four repos** — no SLSA Build L3 — would require isolated workers (e.g. `slsa-github-generator` v2 with `builder-id: https://github.com/actions/runner-images` + `source.verifiable: true`) — **effort: L**
13. **All four repos** — no `cargo cyclonedx-bom` or `cyclonedx-python-lib` step — **effort: S per repo**
14. **AgilePlus** — no `aarch64-unknown-linux-musl` cross-compile target — add `cross` or `cargo-zigbuild` matrix step — **effort: M**
15. **thegent** — Docker templates only in `templates/operational/docker/`; no `Dockerfile` at root or per-service — promote to actual deployable images — **effort: M**

## Recommendations

1. **Stand up `phenotype-sbom` as a shared GitHub Action** that runs `phenotype-dep-guard` SBOM emitter and uploads CycloneDX 1.5 + SPDX 2.3 as release artifacts. One action, used by all four repos.
2. **Add `SOURCE_DATE_EPOCH` environment to every release workflow** — single-line `env:` block.
3. **Promote Tracely to release-plz parity** with the other three repos. Single PR.
4. **Pin all external reusable workflows to commit SHA** in Tracely. Single PR.
5. **Resolve thegent maturin version drift** by adding a `[tool.maturin]` workspace table or by extracting maturin version to a `thegent-workspace/pyproject.toml` consumed by all sub-crates.
6. **Add cibuildwheel matrix** for thegent hybrid crates (`thegent-router`, `thegent-policy`, `thegent-git`, `thegent-cache`, `thegent-resources`, `thegent-fs`, `thegent-subprocess`) — produces `manylinux_2_28` + `musllinux_1_2` wheels for x86_64 + aarch64.
7. **Add PyPI publish** for thegent hybrid crates with provenance via `pypa/gh-action-pypi-publish@release`.
8. **Add `go build` + `go test` + `govulncheck` to Tracera CI** — the Go component currently has no CI.
9. **Tracely `pheno-logging-zig`**: decide and execute. Either implement (`build.zig` for a staticlib exporting a C ABI) or remove the directory and the Cargo.toml member entry.
10. **Cross-repo**: roll up SBOMs from all four repos into a single `phenotype-org/sboms` release artifact on a weekly cron.

## Status summary

| Repo | L9 covered | L9 partial | L9 missing |
|---|---|---|---|
| AgilePlus | 8 (release-plz, SLSA L2, cargo-deny, SHA-pinned actions, locked Cargo.lock, clippy MSRV, deny.toml full) | 3 (no cross-compile, no Dockerfile, no SBOM, no SOURCE_DATE_EPOCH) | 4 (SBOM, SOURCE_DATE_EPOCH, SLSA L3, cross-compile) |
| thegent | 9 (maturin per crate, release-plz, SLSA L2, uv.lock, cargo-deny, scorecard, Docker templates, pyright CI, pyo3 abi3) | 2 (maturin drift, Docker template only) | 5 (no cibuildwheel, no PyPI publish, no Python provenance, no SBOM, no SOURCE_DATE_EPOCH) |
| Tracely | 4 (cargo-deny, CodeQL, cliff.toml, locked Cargo.lock) | 1 (CI reuses template) | 8 (no release workflow, no SLSA, no SBOM, empty zig crate, no Dockerfile, @main refs, no cross-compile, no SOURCE_DATE_EPOCH) |
| Tracera | 10 (justfile recipes, SLSA L2, release-plz, cargo hack per-feature, cargo-deny, governance gates, scorecard, den.toml full, pyright, locked Cargo.lock) | 2 (no go CI, no SBOM) | 4 (no SBOM, no SOURCE_DATE_EPOCH, no go CI, no npm publish) |
| **Bloc** | **31** | **8** | **21** |
