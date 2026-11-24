# PRD — phenotype-auth-ts

## Overview

`phenotype-auth-ts` provides TypeScript OAuth2/OIDC authentication patterns using hexagonal architecture. It defines domain types, ports (`TokenProvider`, `TokenStore`, `TokenVerifier`), and swappable adapters including an in-memory token store and a JWT provider.

## Goals

- Supply a reusable, framework-agnostic auth layer for TypeScript Phenotype services.
- Enable adapter swap between JWT, opaque tokens, and session-based auth without domain changes.
- Enforce token validation, expiry, and revocation as first-class domain concerns.

## Epics

### E1 — Token Domain Model
- E1.1 Define `AccessToken`, `RefreshToken`, `TokenClaims` types.
- E1.2 Define `AuthError` discriminated union for all error cases.
- E1.3 Token expiry and revocation as value objects.

### E2 — Ports
- E2.1 `TokenProvider`: issue and refresh tokens.
- E2.2 `TokenStore`: store and retrieve tokens by ID.
- E2.3 `TokenVerifier`: verify and decode a token into claims.

### E3 — Adapters
- E3.1 `MemoryTokenStore`: in-memory store for testing and dev.
- E3.2 `PlaceholderJwtVerifier`: skeleton for real JWT verification.
- E3.3 Production `JwtTokenProvider` using `jose` library.

### E4 — OAuth2/OIDC Flows
- E4.1 Authorization code flow with PKCE.
- E4.2 Client credentials flow for service-to-service auth.
- E4.3 Token refresh flow with rotation.

### E5 — Middleware Integration
- E5.1 Express/Fastify middleware that extracts and verifies bearer tokens.
- E5.2 Typed `request.user` injection after successful verification.

## Acceptance Criteria

- A token issued by JwtTokenProvider is verifiable by JwtTokenVerifier.
- An expired token returns AuthError.TokenExpired, not a generic error.
- Swapping MemoryTokenStore for a Redis adapter requires no domain code changes.
