# CHANGELOG — `config-schema`

All notable changes to this crate are documented here. Format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Versioning
follows [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-06-20

### Changed
- Workspace version bump 0.1.0 → 0.4.0 per T16 substrate audit
  (Configra tier-2 enforcement).
- Added `README.md`, `CHANGELOG.md`, and `AGENTS.md` to satisfy the
  ADR-023 / ADR-040 quality bar for tier-2 library substrates.
- The package version stays at `0.1.0` because it is explicitly pinned
  in `Cargo.toml` (not derived from `[workspace.package]`); the bump to
  `0.4.0` is tracked here for ecosystem alignment only.

### Notes
- Source: `Conft/crates/config-schema/` (drained in PR
  `<REDACTED>/Configra#47`, 2026-06-18).

## [0.1.0] — 2026-06-18

### Added
- Initial release drained from `Conft` (PR `#47`).
- `SchemaField::new(name, required, type_hint)`.
- `ConfigSchema::new()`, `ConfigSchema::field(...)`.
- `ConfigSchema::validate(&serde_json::Value) -> Result<(), SchemaError>`.
- `SchemaError` enum: `MissingField(String)`,
  `WrongType { field, expected, got }`.
- Zero MSRV-impact dependencies (`serde_json = "1.0"`, `thiserror = "1.0"`).
