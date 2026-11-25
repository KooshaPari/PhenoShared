# Functional Requirements — phenotype-auth-ts

## FR-DOMAIN — Domain Model

| ID | Requirement |
|----|-------------|
| FR-DOMAIN-001 | The system SHALL define AccessToken, RefreshToken, and TokenClaims types. |
| FR-DOMAIN-002 | The system SHALL define an AuthError discriminated union covering all error cases. |
| FR-DOMAIN-003 | Token expiry SHALL be a first-class value object, not a raw number. |
| FR-DOMAIN-004 | The system SHALL support token revocation as a domain operation. |

## FR-PORTS — Ports

| ID | Requirement |
|----|-------------|
| FR-PORTS-001 | The system SHALL define a TokenProvider port with issue() and refresh() methods. |
| FR-PORTS-002 | The system SHALL define a TokenStore port with save(), find(), and revoke() methods. |
| FR-PORTS-003 | The system SHALL define a TokenVerifier port with verify() returning TokenClaims. |

## FR-ADAPT — Adapters

| ID | Requirement |
|----|-------------|
| FR-ADAPT-001 | The system SHALL provide a MemoryTokenStore adapter for development and testing. |
| FR-ADAPT-002 | The system SHALL provide a JwtTokenProvider adapter using the jose library. |
| FR-ADAPT-003 | The system SHALL provide a JwtTokenVerifier adapter that validates signature and expiry. |

## FR-FLOW — Auth Flows

| ID | Requirement |
|----|-------------|
| FR-FLOW-001 | The system SHALL support the OAuth2 authorization code flow with PKCE. |
| FR-FLOW-002 | The system SHALL support the client credentials flow. |
| FR-FLOW-003 | The system SHALL support token refresh with rotation. |

## FR-MW — Middleware

| ID | Requirement |
|----|-------------|
| FR-MW-001 | The system SHALL provide Express/Fastify middleware for bearer token extraction and verification. |
| FR-MW-002 | The middleware SHALL inject typed user claims into the request context on success. |
| FR-MW-003 | The middleware SHALL return 401 with a structured error body on verification failure. |
