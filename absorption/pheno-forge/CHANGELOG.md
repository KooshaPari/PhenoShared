# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Project status (2026-09-08):** scaffold only. The `0.1.0` entry below is
> **historical documentation** of a release that was claimed but never delivered
> in code. See the `0.0.0` audit-closure entry below for the truthful state of
> this checkout.

---

## [Unreleased]

### Added

- (none)

### Changed

- (none)

### Deprecated

- (none)

### Removed

- (none)

### Fixed

- (none)

### Security

- (none)

---

## [0.0.0] - 2026-09-08 — Audit closure: truthful scaffold

### Added

- `FUNCTIONAL_REQUIREMENTS.md` — `Status` and `Where` columns added to every
  requirement; new `FR-OBS` section enumerates the three observability
  requirements that are actually delivered today.
- `tests/integration.rs` — replaced vacuous `assert_eq!(2+2,4)`-style tests with
  a negative-oracle suite that locks in the truthful scaffold (banner output,
  README feature matrix integrity, no false "Stable" claims, scaffold-only
  status of `src/main.rs` and `Cargo.toml`).
- `README.md` — rewritten to describe the **actual** scaffold instead of the
  aspirational feature matrix. Every prior `Stable`/`Beta` claim has been
  removed or re-qualified as `Not implemented` / `Stub only` /
  `Scaffold only`.
- `src/main.rs` — replaced the silent "Watching for changes..." line with a
  clearer "scaffold placeholder; not a real watcher" message so that the
  no-op nature of `--watch` is self-documenting at runtime.
- `ARCHIVED.md` — clarified that the migration record is historical; this
  checkout still ships the `phenotype-forge` binary and was not renamed.

### Changed

- `Cargo.toml` — **no changes**. The dependency list (`tokio`, `clap`, `serde`,
  `notify`, `toml`, `thiserror`, `tracing`) is over-provisioned for the current
  scaffold (only `clap` is actually exercised at runtime). Removal or
  implementation is tracked as future work, not done in this closure to keep
  the blast radius small.

### Fixed

- **Documentation-vs-code gap.** Previously the README asserted eight
  `Stable` / `Beta` features that the binary does not deliver. The closure
  surfaces the gap explicitly in `README.md`, `FUNCTIONAL_REQUIREMENTS.md`,
  and the negative-oracle tests so that any future implementer can flip
  the tests from "currently passes" to "must pass with a positive
  assertion" when each feature is actually built.

### Security

- (no security-relevant changes)

---

## [0.1.0] - 2026-01-01

> **Audit note (2026-09-08):** This entry describes a release that was **claimed
> in documentation** but **not delivered in code**. The binary in this checkout
> is a 12-line `clap` placeholder that prints `Running task: <name>`. None of
> the `Added` items below are implemented in the source tree. The entry is
> retained for provenance; future readers should treat it as a documentation
> milestone rather than an implementation milestone.

### Added

- Initial project setup
- README.md documentation
- AGENTS.md guidelines
- CLI task runner core functionality (claim only; not implemented)
- Configuration parsing (TOML) (claim only; not implemented)
- Task dependency resolution (claim only; not implemented)
- File watching support (claim only; not implemented)
