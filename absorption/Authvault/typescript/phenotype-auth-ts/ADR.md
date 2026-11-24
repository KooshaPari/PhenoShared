# Architecture Decision Records — phenotype-auth-ts

## ADR-001 — jose as JWT Implementation

**Status:** Accepted  
**Date:** 2026-03-27

### Context
Several Node.js JWT libraries exist (jsonwebtoken, jose, fast-jwt). `jose` supports modern algorithms (EdDSA, ES256), JWKS, and runs in both Node.js and edge runtimes.

### Decision
Use `jose` (v5+) as the JWT implementation backend in the JwtTokenProvider and JwtTokenVerifier adapters.

### Consequences
- Supports RS256, ES256, EdDSA, and symmetric algorithms.
- Works in Cloudflare Workers and other edge environments.
- `jsonwebtoken` is NOT used; migration from it is straightforward.

---

## ADR-002 — Discriminated Union for AuthError

**Status:** Accepted  
**Date:** 2026-03-27

### Context
Auth errors have distinct handling: expired tokens need refresh, revoked tokens need re-login, invalid tokens need 400 responses. A generic `Error` loses this distinction.

### Decision
Define `AuthError` as a TypeScript discriminated union with variants: `TokenExpired`, `TokenRevoked`, `TokenInvalid`, `TokenNotFound`, `Unauthorized`.

### Consequences
- Callers use exhaustive switch/match on error variants.
- TypeScript narrows the type in each branch.

---

## ADR-003 — Hexagonal Ports for Adapter Swappability

**Status:** Accepted  
**Date:** 2026-03-27

### Context
Production uses JWT + Redis token store. Tests use in-memory store. The domain should not know which is active.

### Decision
`TokenProvider`, `TokenStore`, and `TokenVerifier` are TypeScript interfaces (ports). All domain services receive them via dependency injection.

### Consequences
- Swapping to an opaque-token provider requires only a new adapter.
- No domain code imports `jose`, `redis`, or any infrastructure library.
