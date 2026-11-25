# CHANGELOG — `phenotype-config-loader`

All notable changes to this crate are documented here. Format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Versioning
follows [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-06-20

### Changed
- Workspace version bump 0.1.0 → 0.4.0 per T16 substrate audit
  (Configra tier-2 enforcement).
- Added `README.md`, `CHANGELOG.md`, and `AGENTS.md` to satisfy the
  ADR-023 / ADR-040 quality bar for tier-2 library substrates.
- No source-code changes — `load_json`, `load_toml`, and
  `ConfigLoadError` API is unchanged.

### Notes
- Crate moved into the Configra workspace at this commit
  (PR `<REDACTED>/Configra#52` prior).
- Source: `<REDACTED>/phenotype-config/crates/phenotype-config-loader/`
  (commit `f86f8e9` on `main`, 2026-06-17).

## [0.1.0] — 2026-06-17

### Added
- Initial release absorbed from `<REDACTED>/phenotype-config`.
- `load_json<T: DeserializeOwned>(&Path) -> Result<T, ConfigLoadError>`
- `load_toml<T: DeserializeOwned>(&Path) -> Result<T, ConfigLoadError>`
- `ConfigLoadError` enum: `NotFound`, `Parse`, `Io`.
- 3 unit tests in `src/lib.rs` (JSON, TOML, not-found paths).
