# FR-AUTH-001: JWT Token Generation

## ID
- **FR-ID**: FR-AUTH-001
- **Repository**: Authvault
- **Domain**: Authentication

## Description

The system SHALL generate cryptographically secure JWT access tokens containing user identity claims. Tokens SHALL be signed using HMAC-SHA256 with a 256-bit secret key.

## Acceptance Criteria

- [ ] Generates valid JWT tokens with standard claims (sub, iss, exp, iat)
- [ ] Uses cryptographically secure random for token IDs
- [ ] Signs tokens with HMAC-SHA256
- [ ] Supports configurable token lifetime
- [ ] Returns error for invalid signing keys

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/token_tests.rs` | `test_jwt_generation` | `// @trace FR-AUTH-001` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/token.rs` | `generate_token()` | `// @trace FR-AUTH-001` |

## Related FRs

- FR-AUTH-002: JWT Token Validation
- FR-AUTH-003: Token Refresh

## Status

- **Current**: implemented
- **Since**: 2026-01-15
