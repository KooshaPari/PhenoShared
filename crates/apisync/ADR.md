# Architecture Decision Records — apikit

> **Canonical ADR location:** `docs/adr/*.md` (one file per decision, rendered by VitePress).
> This root `ADR.md` is kept as a quick-reference summary. If the two diverge,
> `docs/adr/` wins — do not add new decisions here; add them to `docs/adr/` only.

## ADR-001: Hexagonal Internal Layout

**Status:** Accepted

**Context:** `apikit` is itself structured with hexagonal layers (`domain/`, `application/`, `adapters/`, `infrastructure/`). This was observed in the repo source layout.

**Decision:** Internal modules follow hexagonal naming. The `domain/` module contains transport-agnostic request/response types. `adapters/` contains hyper-specific implementations. `application/` contains the client/server use case logic.

**Rationale:** Keeps the library internally testable and consistent with ecosystem patterns, enabling future transport replacement (e.g., swapping hyper for reqwest) without API surface changes.

**Consequences:** More files than a flat structure; offset by clear separation.

---

## ADR-002: hyper 1.x as HTTP Transport

**Status:** Accepted

**Context:** Rust HTTP options include `reqwest`, `hyper`, `ureq`, and `isahc`. The library targets both client and server use cases.

**Decision:** Use `hyper` 1.x directly for full control over HTTP/1.1 and HTTP/2. Higher-level libraries (`reqwest`) may be re-exported as optional features.

**Rationale:** `hyper` is the lowest-level async HTTP library in Rust with the widest ecosystem compatibility. Direct usage avoids layered abstraction overhead.

**Alternatives Considered:**
- reqwest: higher-level but less control over connection pooling and middleware.
- ureq: blocking only; not suitable for async-first Phenotype services.

**Consequences:** More boilerplate required for common patterns; mitigated by the higher-level abstractions `apikit` provides.

---

## ADR-003: async-trait for Protocol Traits

**Status:** Accepted

**Context:** Rust async traits require `async-trait` macro or nightly RPITIT.

**Decision:** Use `async-trait` crate for all async port traits until stable async trait support is universally available.

**Consequences:** Small allocation per async call; acceptable for API toolkit use cases.
