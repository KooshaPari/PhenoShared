# ADR — go-hex

## ADR-001: Generics Baseline
**Status:** Accepted
**Context:** Go generics (1.18+) enable type-safe ports and repositories without interface{}.
**Decision:** Minimum Go version is 1.21 (for `slices`, `maps` stdlib and stable generics).
**Rationale:** Phenotype platform targets current Go toolchain; 1.21 is widely available.

## ADR-002: Marker Interfaces for Ports
**Status:** Accepted
**Context:** Go does not have annotation/attribute systems; ports need a documentation contract.
**Decision:** `InboundPort` and `OutboundPort` are empty interfaces used as type constraints for documentation and lint rules (via custom `depguard` config).
**Rationale:** Enforces semantic intent at code level; compatible with interface composition.

## ADR-003: Context-First APIs
**Status:** Accepted
**Context:** Go convention for cancellation and deadline propagation.
**Decision:** All use case and repository interfaces accept `context.Context` as first argument.
**Rationale:** Standard Go idiom; required for correct timeout and tracing propagation.

## ADR-004: Error Handling
**Status:** Accepted
**Context:** Go has multi-return errors; a Result type is optional but explicit.
**Decision:** Provide `Result[T]` as an opt-in wrapper. Core interfaces use idiomatic `(T, error)` returns. `Result[T]` is available for consumers who prefer functional-style chaining.
**Rationale:** Does not force non-idiomatic Go on consumers; opt-in ergonomic layer.

## ADR-005: Wire Compatibility
**Status:** Accepted
**Context:** Many Go services use Google Wire for compile-time DI.
**Decision:** `Container` is a runtime convenience only. Adapters are plain structs/interfaces compatible with Wire provider functions.
**Rationale:** go-hex does not own the DI strategy; Wire or manual wiring both work.
