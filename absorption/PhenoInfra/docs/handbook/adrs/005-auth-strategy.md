# ADR-005: Authentication & Authorization Strategy

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

Phenotype services must authenticate humans (dashboard users, CLI operators) and machine identities (service-to-service calls, CI pipelines). We need a solution that supports standard OAuth/OIDC flows for human users, API-key and JWT-based machine auth, and centralised policy enforcement without requiring each service to implement its own auth logic.

## Decision

We adopt **Firepass** as the unified authentication and authorisation platform for all Phenotype services.

Firepass provides a single control plane for issuing and validating JWTs, managing OAuth/OIDC identity providers, and enforcing RBAC/ABAC policies. Centralising auth in Firepass means individual services validate tokens against a well-known JWKS endpoint rather than owning credential stores. This pattern is already live across Civis and the heliosApp family; any new service adopts it by adding the Firepass middleware and declaring its required scopes in the service manifest.

## Consequences

### Positive
- Single auth surface reduces the blast radius of credential compromise
- Services are stateless with respect to auth — no session stores required
- RBAC policies are auditable and version-controlled in the Firepass config repo
- Standard OIDC means any OIDC-compatible IdP (GitHub, Google) can be wired in

### Negative / Trade-offs
- Firepass is the hard dependency for every service; availability impacts propagate widely
- Local dev requires either a Firepass stub or live credentials (see `KIMI_API_KEY`/`FIREPASS_BASE_URL` env vars)
- Key rotation requires coordinated rollout across all consumer services

## References

- ADR-004 — API Design (auth headers flow through the REST/RPC boundary)
- [Civis infra stack notes](../MEMORY/project_civis_infra_stack.md)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
