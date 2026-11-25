# Changelog

All notable changes to pheno-context are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-06-17

### Added

- Initial standalone release (recovered from stranded `chore/l4-68-pheno-context-2026-06-11` worktree, original commit `d8960dfd80`).
- `Context` struct with `request_id`, `span_id`, `trace_id`, `user_id`, `org_id`, `metadata` fields.
- `ContextBuilder` for fluent programmatic construction.
- `Context::from_headers(&HeaderMap)` for header-based extraction.
- `ContextError::MissingHeader(String)` as the canonical error.
- 9 unit tests covering builder, header extraction, display, and clone/eq.
- Workspace `Cargo.toml` with shared `thiserror` + `http` deps.

[0.1.0]: https://github.com/KooshaPari/pheno-context/releases/tag/v0.1.0
