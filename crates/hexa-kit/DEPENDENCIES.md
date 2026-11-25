# Workspace Dependency Hierarchy

**Document**: DEPENDENCIES.md  
**Date**: 2026-04-02  
**Status**: Documented

## Overview

The Phenotype repository shelf has a multi-layered dependency structure with core infrastructure crates, shared templates, and application projects.

## Layer 1: Core Infrastructure Crates

### Location: `crates/`
**Count**: 65+ individual crates
**Structure**: Flat directory (not a Cargo workspace)

#### Core Categories

| Category | Crates | Purpose |
|----------|--------|---------|
| **Error Handling** | `phenotype-error-core`, `phenotype-error-macros`, `phenotype-errors` | Domain and application error types |
| **Configuration** | `phenotype-config-core`, `phenotype-config-loader`, `phenotype-shared-config` | Configuration management |
| **Logging/Telemetry** | `phenotype-logging`, `phenotype-telemetry` | Structured logging and observability |
| **Health** | `phenotype-health` | Health check patterns |
| **Async** | `phenotype-async-traits` | Async trait definitions |
| **Security** | `phenotype-crypto`, `phenotype-security-aggregator`, `phenotype-casbin-wrapper` | Cryptography and authorization |
| **Testing** | `phenotype-test-fixtures`, `phenotype-test-infra` | Test infrastructure |
| **Utilities** | `phenotype-string`, `phenotype-time`, `phenotype-iter`, `phenotype-retry`, `phenotype-rate-limit` | Shared utilities |
| **Contracts** | `phenotype-contract`, `phenotype-contracts` | Interface contracts |
| **Git** | `phenotype-git-core` | Git operations |
| **Events** | `phenotype-event-sourcing` | Event sourcing patterns |
| **Policy** | `phenotype-policy-engine` | Policy evaluation |
| **State** | `phenotype-state-machine` | State machine patterns |
| **Process** | `phenotype-process` | Process management |
| **MCP** | `phenotype-mcp` | Model Context Protocol |

### AgilePlus Crates (in `crates/`)
- `agileplus-api`, `agileplus-api-types`
- `agileplus-domain`, `agileplus-events`
- `agileplus-sqlite`, `agileplus-git`, `agileplus-github`
- `agileplus-sync`, `agileplus-graph`, `agileplus-triage`
- `agileplus-telemetry`, `agileplus-nats`, `agileplus-p2p`
- `agileplus-plane`, `agileplus-cli`, `agileplus-dashboard`
- And more...

## Layer 2: Infrastructure Workspace

### Location: `phenotype-infrakit/`
**Structure**: Proper Cargo workspace

```
phenotype-infrakit/
├── Cargo.toml          # Workspace manifest
├── crates/
│   ├── phenotype-bdd/
│   ├── phenotype-rate-limiter/
│   ├── phenotype-validation/
│   └── phenotype-http-client/
└── target/             # Shared build artifacts
```

**Workspace Members**: 4 crates
**Excluded**: `phenotype-config-core`, `phenotype-testing`, `phenotype-config-loader`

### Workspace Dependencies
- **Serialization**: serde, serde_json, serde_yaml, toml
- **Async**: tokio, futures, async-trait
- **Error Handling**: thiserror, anyhow
- **Tracing**: tracing, tracing-subscriber, tracing-appender
- **HTTP**: reqwest, hyper, axum, http
- **Validation**: jsonschema, schemars, validator
- **Crypto**: sha2, hex, ed25519-dalek, argon2, bcrypt
- **Time**: chrono

## Layer 3: Shared Templates

### Location: `template-commons/`
**Contents**:
- `phenotype-py-kit/` - Python kit templates
- `phenotype-ts-kit/` - TypeScript kit templates  
- `phenotype-rs-kit/` - Rust kit templates

## Layer 4: Individual Projects

Projects depend on crates from Layer 1 and 2:

| Project | Key Dependencies |
|---------|------------------|
| `thegent/` | phenotype-error-core, phenotype-logging |
| `AgentMCP/` | phenotype-mcp, phenotype-async-traits |
| `AgilePlus/` | agileplus-* crates |
| `helios-cli/` | (standalone) |
| `Tokn/` | (standalone) |

## Dependency Rules

1. **Layer 4** → depends on **Layer 1, 2, 3**
2. **Layer 3** → depends on **Layer 1, 2**
3. **Layer 2** → internal workspace deps + external crates
4. **Layer 1** → external crates only

## Recommendations

1. **Unify crates structure**: Consider making `crates/` a proper workspace
2. **Merge phenotype-infrakit**: Integrate into unified workspace
3. **DEPENDENCIES.md**: Each project should declare its dependencies
4. **Version alignment**: Use workspace.dependencies for shared versions

## See Also

- `plans/20260402-repo-graph-optimization-v1.md`
- `template-commons/README.md`
