# ARCHIVED

**Authvault has been absorbed into [AuthKit](https://github.com/KooshaPari/AuthKit).**

All authentication and authorization code (Rust, Go, Python, TypeScript) has been moved to the AuthKit repository, which is now the canonical auth repository for the Phenotype ecosystem.

## What happened

- Authvault's Rust auth crates were moved into `AuthKit/crates/`
- All multi-language SDKs (Go, Python, TypeScript) were consolidated into AuthKit
- AuthKit now serves as the single source of truth for all auth-related code

## Migration

- **Existing code**: Update your `Cargo.toml` dependency from `authvault` to `authkit-core` (package name: `authkit_core` in code)
- **New development**: Clone [github.com/KooshaPari/AuthKit](https://github.com/KooshaPari/AuthKit) instead of Authvault
- **Issues/PRs**: File all new issues and PRs against [AuthKit](https://github.com/KooshaPari/AuthKit/issues)

## History

This repository remains available for historical reference. No further development will occur here.

*Archived: 2026-06-20*
