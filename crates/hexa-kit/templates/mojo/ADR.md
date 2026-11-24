# ADR — template-lang-mojo

## ADR-001: Mojo Version
**Status:** Accepted
**Context:** Mojo is rapidly evolving; version selection matters.
**Decision:** Target latest stable Mojo version. Update as new versions release.
**Rationale:** Mojo is evolving quickly; use latest stable for best features.

## ADR-002: Package Management
**Status:** Accepted
**Context:** Mojo package ecosystem is developing.
**Decision:** Use Modal for cloud deployment. Local packages via MODULAR_PATHS.
**Rationale:** Modal provides seamless cloud execution; MODULAR for local packages.

## ADR-003: ML/AI Integration
**Status:** Accepted
**Context:** Mojo is designed for AI/ML workloads.
**Decision:** Leverage MAX (Modular Accelerator) for ML operations. Use Mojo stdlib for everything else.
**Rationale:** MAX provides optimized ML kernels; stdlib provides foundations.

## ADR-004: Python Interop
**Status:** Accepted
**Context:** Mojo has Python interop capabilities.
**Decision:** Call Python libraries from Mojo. Avoid Mojo-in-Python patterns.
**Rationale:** Mojo performance benefits require Mojo-native code.

## ADR-005: Error Handling
**Status:** Accepted
**Context:** Mojo has raise/try/catch like Python.
**Decision:** Use raises for fallible functions. Custom error types for domain errors.
**Rationale:** Explicit error handling matches Mojo design philosophy.

## ADR-006: Structs over Classes
**Status:** Accepted
**Context:** Mojo has both structs and classes.
**Decision:** Prefer structs for performance. Use classes only when identity matters.
**Rationale:** Structs are more efficient (no heap allocation by default).
