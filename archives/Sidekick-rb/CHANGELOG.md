# Changelog

All notable changes to the Sidekick workspace are documented here.

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.0.1] — 2026-04-24

### Added

- **Bootstrap**: Consolidated 4 agent micro-utilities into named collection
  - sidekick-presence (from `agent-user-status`)
  - sidekick-dispatch (from `thegent-dispatch`)
  - sidekick-cheap-llm (from `cheap-llm-mcp`)
  - Stub for sidekick-messaging (agent-imessage not yet located)
- Workspace-level Cargo.toml with shared dependencies
- Documentation: README, CHANGELOG, AGENTS.md, CLAUDE.md
- Consolidation notes mapping source repos to target crates
- Initial workspace verification passing (cargo check --workspace)

### Notes

- Original source repos retained pending user cutover approval
- Python package (sidekick-cheap-llm) integrated via separate pyproject.toml
- Messaging integration deferred to Phase 2
