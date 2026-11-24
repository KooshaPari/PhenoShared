# ADR: Phenotype Kits Workspace

## ADR-001: Cargo Workspace over Individual Crates

**Status**: Accepted

**Context**: Multiple kit libraries share dev-dependencies (tokio, serde, thiserror) and need coordinated versioning. Two approaches considered: (a) individual crate repos, (b) single Cargo workspace.

**Decision**: Single Cargo workspace in this repository. All kit crates are workspace members.

**Rationale**: Workspace allows shared dependency resolution, single `cargo test --workspace`, and coordinated version bumps. Cross-crate integration tests are easier in a workspace context.

**Consequences**: All kits must be compatible Rust editions. Individual crate publishing still works via `cargo publish -p <crate>`.

---

## ADR-002: Trait-Based Port Definitions

**Status**: Accepted

**Context**: Kit libraries are used by many downstream crates. Concrete implementations must not leak into the public API surface.

**Decision**: Each kit exposes only trait-based ports in its top-level `lib.rs`. Concrete adapters are in `adapters/` subdirectories and are feature-gated.

**Rationale**: Consumers can depend on the trait without pulling concrete adapter dependencies (e.g., Redis client for cachekit).

**Consequences**: Feature flags increase compilation surface area. Default features must be minimal.

---

## ADR-003: tokio as Async Runtime

**Status**: Accepted

**Context**: Several kits (agentkit, taskkit) require async primitives. Choices: tokio, async-std, smol.

**Decision**: tokio as the single async runtime dependency across all kits.

**Rationale**: tokio is the de-facto standard in the Rust ecosystem with the widest compatibility. Using two runtimes in one binary causes deadlocks.

**Consequences**: All kit consumers must use tokio. This is documented in each kit's README.

---

## ADR-004: thiserror for Error Types

**Status**: Accepted

**Context**: Error propagation across kit boundaries requires consistent error types.

**Decision**: All kit crates use `thiserror` for deriving `Error` implementations. No `anyhow` in library code (only in binary/example code).

**Rationale**: `thiserror` produces typed errors that consumers can match on. `anyhow` is opaque and unsuitable for library boundaries.

**Consequences**: Error types are more verbose to define but provide better ergonomics at call sites.

