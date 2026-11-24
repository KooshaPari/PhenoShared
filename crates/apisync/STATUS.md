# Status

Last updated: 2026-06-08

## Build

GitHub Actions billing-blocked org-wide. Workflows are configured but not running.

## Quality gates

- cargo check: local + CI
- cargo test: local + CI
- cargo clippy: local + CI
- cargo fmt: local + CI
- cargo audit: local + CI

## Current state

- Branch: `main` (default)
- Working tree: clean
- Stashes: 0
- Open PRs: 0
- License: MIT OR Apache-2.0
- Tests: benches only (no unit tests yet)

## Recent changes

- Fixed CI workflow duplicate `on:` block and replaced broken placeholder SHAs
- Enhanced Taskfile.yml with build, lint, audit, bench tasks
- Added STATUS.md

## Cross-references

See `phenotype-org-governance/SUPERSEDED.md` for canonical authority.
