# Project Classification System

**Document**: PROJECT_CLASSIFICATION.md  
**Date**: 2026-04-02  
**Status**: Implemented

## Classification Tiers

| Tier | Criteria | Count |
|------|----------|-------|
| **Core** | Required by 5+ projects, infrastructure crates | 15+ |
| **Platform** | Core product infrastructure | 8 |
| **Application** | End-user products and tools | 40+ |
| **Template** | Project scaffolding (12 canonical) | 20+ |
| **Archive** | Deprecated/legacy, wrong content | 5+ |

## Tier 1: Core Infrastructure

**Criteria**: Used by 5+ projects, fundamental building blocks

| Project | Type | Description |
|---------|------|-------------|
| `crates/phenotype-error-core` | Crate | Error handling foundation |
| `crates/phenotype-logging` | Crate | Structured logging |
| `crates/phenotype-health` | Crate | Health check patterns |
| `crates/phenotype-config-core` | Crate | Configuration management |
| `crates/phenotype-async-traits` | Crate | Async abstractions |
| `crates/phenotype-telemetry` | Crate | Observability |
| `crates/phenotype-crypto` | Crate | Cryptography utilities |
| `crates/phenotype-test-fixtures` | Crate | Test infrastructure |
| `crates/phenotype-contract` | Crate | Interface contracts |
| `crates/phenotype-validation` | Crate | Validation patterns |
| `crates/phenotype-rate-limit` | Crate | Rate limiting |
| `crates/phenotype-retry` | Crate | Retry logic |
| `crates/phenotype-time` | Crate | Time utilities |
| `crates/phenotype-string` | Crate | String utilities |
| `crates/phenotype-git-core` | Crate | Git operations |

## Tier 2: Platform Infrastructure

**Criteria**: Core product infrastructure, major systems

| Project | Type | Description |
|---------|------|-------------|
| `thegent/` | Platform | Agent orchestration platform |
| `AgilePlus/` | Platform | Project management system |
| `AgentMCP/` | Platform | Model Context Protocol |
| `Agentora/` | Platform | Agent framework |
| `phenotype-infrakit/` | Platform | Infrastructure toolkit |
| `BytePort/` | Platform | Data transport |
| `Datamold/` | Platform | Data transformation |
| `Eventra/` | Platform | Event processing |

## Tier 3: Applications

**Criteria**: End-user products, CLI tools, services

| Project | Type | Description |
|---------|------|-------------|
| `helios-cli/` | CLI | Command-line interface |
| `heliosApp/` | App | Web application |
| `Tokn/` | App | Token management |
| `Duple/` | App | Data duplication |
| `Profila/` | App | Profile management |
| `Settly/` | App | Configuration |
| `Stashly/` | App | Caching |
| `Tasken/` | Task | Task execution |
| `Docuverse/` | App | Documentation |
| `Evalora/` | App | Evaluation framework |
| `Queris/` | App | Query system |
| `Quillr/` | App | Document processing |
| `Logify/` | App | Log aggregation |
| `Metron/` | App | Metrics |
| `Flagward/` | Feature | Feature flags |
| `Flowra/` | App | Workflow |
| `Guardis/` | App | Security |
| `Httpora/` | App | HTTP toolkit |
| `KaskMan/` | App | Cache manager |
| `Authvault/` | App | Auth storage |
| `Cliproxy/` | CLI | CLI proxy |
| `Cmdra/` | CLI | Command runner |
| `Clikit/` | CLI | CLI kit |
| `Portage/` | CLI | Package management |
| `Tracera/` | App | Tracing |
| `Traceon/` | App | Observability |
| `Tossy/` | App | Task orchestration |
| `Planify/` | App | Planning |
| `Schemaforge/` | App | Schema management |
| `Seedloom/` | App | Seeding |
| `Apisync/` | App | API sync |
| `Authvault/` | App | Auth vault |
| `bifrost/` | App | Routing |
| `cloud/` | App | Cloud tooling |
| `Kogito/` | App | Knowledge |
| `KodeVibeGo/` | Dev | Dev tooling |
| `Portalis/` | App | Portal |
| `PolicyStack/` | App | Policies |
| `Zerokit/` | App | Zero-config |

## Tier 4: Templates (12 Canonical)

**Criteria**: Project scaffolding, language/domain templates

### Language Templates
| Project | Language | Status |
|---------|----------|--------|
| `template-lang-python` | Python | v0.1.0 |
| `template-lang-rust` | Rust | v0.1.0 |
| `template-lang-go` | Go | v0.1.0 |
| `template-lang-kotlin` | Kotlin | v0.1.0 |
| `template-lang-typescript` | TypeScript | v0.1.0 |
| `template-lang-elixir-hex` | Elixir | v0.1.0 |
| `template-lang-swift` | Swift | v0.1.0 |
| `template-lang-zig` | Zig | v0.1.0 |
| `template-lang-mojo` | Mojo | v0.1.0 |

### Domain Templates
| Project | Domain | Status |
|---------|--------|--------|
| `template-domain-webapp` | Web App | v0.1.0 |
| `template-domain-service-api` | Service API | v0.1.0 |
| `template-program-ops` | Ops/CLI | v0.1.0 |

### Template Commons
| Project | Purpose |
|---------|---------|
| `template-commons` | Shared templates, kits |

## Tier 5: Archive

**Criteria**: Deprecated, wrong content, historical

| Project | Reason | Action |
|---------|--------|--------|
| `hexagon-ts/` | Contains Go, not TypeScript | ARCHIVED |
| `hexagon-python/` | Contains Go, not Python | ARCHIVED |
| `hexagon-rs/` | Contains Go, not Rust | ARCHIVED |
| `phenotype-auth-ts/` | Deprecated | Archive |
| `phenotype-dep-guard/` | Check status | Review |

## Classification Labels

Use these labels in project metadata:

```yaml
# In PROJECT_METADATA.md or similar
tier: core | platform | application | template | archive
status: active | maintenance | deprecated | archived
visibility: public | internal | private
dependents: count or list
```

## Update Process

1. **New projects**: Classify on onboarding
2. **Quarterly review**: Reclassify based on usage
3. **Promotion**: Core candidates need 5+ dependents
4. **Deprecation**: Archive tier after 6 months stale

## See Also

- `DEPENDENCIES.md` - Dependency hierarchy
- `plans/20260402-repo-graph-optimization-v1.md`
- Individual project `AGENTS.md` files
