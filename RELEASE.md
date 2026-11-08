# PhenoObservability Release Process

## Versioning Scheme

PhenoObservability uses **Semantic Versioning (SemVer)**:
- Major: Breaking changes to observability trait contracts
- Minor: New backend integrations, instrumentation utilities
- Patch: Bug fixes, telemetry enhancements

Current version: `0.1.0` (pre-release)

## Publish Targets

Most crates target **crates.io**; internal utilities publish to workspace only:

| Crate | Status | Target |
|-------|--------|--------|
| pheno-dragonfly | alpha | crates.io |
| pheno-questdb | alpha | crates.io |
| pheno-tracing | alpha | crates.io |
| phenotype-llm | alpha | internal |
| phenotype-mcp-server | alpha | internal |
| phenotype-surrealdb | alpha | crates.io |
| tracely-core | alpha | crates.io |
| tracely-sentinel | alpha | crates.io |
| helix-logging | alpha | crates.io |
| tracingkit | alpha | crates.io |
| phenotype-observably-tracing | alpha | crates.io |
| phenotype-observably-logging | alpha | crates.io |
| phenotype-observably-sentinel | alpha | crates.io |

## Release Registry

The authoritative registry is maintained in:
- **Location**: `./release-registry.toml` (this directory)
- **Format**: TOML collection manifest with per-crate metadata and publish targets
- **Schema**: Conforms to `docs/governance/release_registry_schema.md`

## Publish Process

1. **Run full test suite**: `cargo test --workspace`
2. **Verify all backend integrations**: `cargo build --all-features`
3. **Update versions** in all `Cargo.toml` files and `release-registry.toml`
4. **Update CHANGELOG.md** with observability improvements
5. **Create release tag**: `git tag v<version>`
6. **Publish public crates**: Filter by `publish_target = "crates.io"` in registry
7. **Internal crates** remain workspace-only (no crates.io publish)

## Release Registry Location

- **File**: `release-registry.toml` (repository root)
- **Format**: TOML
- **Contents**: Observability infrastructure metadata, all 13 workspace crates with publish targets
- **Update**: When adding backends or reclassifying crates between public/internal

## Additional Resources

- **Backend Integration Guide**: See `docs/backend-integration.md`
- **Telemetry Standards**: OpenTelemetry spec at https://opentelemetry.io/
- **Cargo Publishing**: https://doc.rust-lang.org/cargo/publishing/
