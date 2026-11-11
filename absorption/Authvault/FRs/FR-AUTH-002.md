# FR-AUTH-002: JWT Token Validation

## ID
- **FR-ID**: FR-AUTH-002
- **Repository**: Authvault
- **Domain**: Authentication

## Description

The system SHALL validate JWT tokens on every protected API request. Invalid, expired, or malformed tokens SHALL result in HTTP 401 Unauthorized responses.

## Acceptance Criteria

- [ ] Validates token signature against configured secret
- [ ] Rejects expired tokens (exp claim check)
- [ ] Rejects tokens with invalid format
- [ ] Rejects tokens from future (nbf check)
- [ ] Returns structured error for validation failures

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/token_tests.rs` | `test_token_validation` | `// @trace FR-AUTH-002` |
| `tests/token_tests.rs` | `test_expired_token` | `// @trace FR-AUTH-002` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/token.rs` | `validate_token()` | `// @trace FR-AUTH-002` |
| `src/middleware.rs` | `AuthMiddleware` | `// @trace FR-AUTH-002` |

## Related FRs

- FR-AUTH-001: JWT Token Generation
- FR-AUTH-003: Token Refresh

## Status

- **Current**: implemented
- **Since**: 2026-01-20
