# ADR — ts-hex

## ADR-001: Zero Runtime Dependencies
**Status:** Accepted
**Context:** Architecture libraries should not force dependency choices on consumers.
**Decision:** ts-hex has zero production dependencies. Framework integrations (NestJS, Express, Fastify) are separate packages (`ts-hex-nest`, etc.) with peer dependencies.
**Rationale:** Consumers can adopt ts-hex without inheriting a transitive dep tree.

## ADR-002: Result Type Over Exceptions
**Status:** Accepted
**Context:** Exceptions are untyped and break the use case contract.
**Decision:** Use cases return `Result<T, E>` (discriminated union). Exceptions are only for truly unexpected programmer errors (invariant violations).
**Rationale:** Forces callers to handle error cases at compile time; improves error flow traceability.
**Alternatives considered:** Throwing typed errors — not enforceable at compile time; `Either` from fp-ts — external dep, heavier API.

## ADR-003: No Decorator/Reflect-Metadata
**Status:** Accepted
**Context:** Decorator-based DI (like InversifyJS) requires `reflect-metadata` and experimentalDecorators.
**Decision:** HexContainer uses explicit registration (no magic), compatible with strict TypeScript and ESM.
**Rationale:** Avoids compiler flag requirements; works with all module systems.

## ADR-004: Type-Level Testing
**Status:** Accepted
**Context:** Port/adapter type contracts must be verified at compile time, not just runtime.
**Decision:** Use `expect-type` (or `tsd`) for type-level assertions in test suite.
**Rationale:** Catches regressions in generic type parameters that runtime tests cannot catch.
