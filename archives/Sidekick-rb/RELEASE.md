# Sidekick Release Process

## Versioning Scheme

Sidekick uses **Semantic Versioning (SemVer)**:
- Major: Breaking changes to public APIs
- Minor: New features, backwards compatible
- Patch: Bug fixes, internal improvements

Current version: `0.0.1` (pre-release)

## Publish Targets

All crates in Sidekick target **crates.io** as the primary registry:

| Crate | Status | Target |
|-------|--------|--------|
| sidekick-dispatch | alpha | crates.io |
| sidekick-messaging | alpha | crates.io |

## Release Registry

The authoritative registry of all packages and their publish metadata is maintained in:
- **Location**: `./release-registry.toml` (this directory)
- **Format**: TOML with collection metadata and per-crate publish targets
- **Schema**: Conforms to `docs/governance/release_registry_schema.md`

## Publish Process

1. **Verify tests pass**: `cargo test --workspace`
2. **Update version** in each crate's `Cargo.toml` and root `release-registry.toml`
3. **Update CHANGELOG.md** with release notes
4. **Create git tag**: `git tag v<version>`
5. **Publish**: `cargo publish --manifest-path crates/<crate>/Cargo.toml`
6. **Push tags**: `git push origin <tag>`

## Release Registry Location

- **File**: `release-registry.toml` (repository root)
- **Format**: TOML
- **Contents**: Collection metadata, all workspace member crates with publish targets
- **Update**: When adding new crates or changing publish targets

## Additional Resources

- **Cargo Book**: https://doc.rust-lang.org/cargo/
- **Crates.io**: https://crates.io/
- **SemVer**: https://semver.org/
