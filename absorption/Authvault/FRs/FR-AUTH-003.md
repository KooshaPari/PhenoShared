# FR-AUTH-003: Token Refresh

## ID
- **FR-ID**: FR-AUTH-003
- **Repository**: Authvault
- **Domain**: Authentication

## Description

The system SHALL implement refresh token rotation. When an access token expires, users MAY exchange a valid refresh token for a new access token and refresh token pair.

## Acceptance Criteria

- [ ] Accepts valid refresh tokens and returns new token pair
- [ ] Invalidates used refresh tokens (single-use)
- [ ] Validates refresh token expiration
- [ ] Issues new refresh token with each exchange
- [ ] Maintains refresh token family for rotation detection

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/refresh_tests.rs` | `test_token_refresh` | `// @trace FR-AUTH-003` |
| `tests/refresh_tests.rs` | `test_refresh_token_rotation` | `// @trace FR-AUTH-003` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/refresh.rs` | `exchange_refresh_token()` | `// @trace FR-AUTH-003` |

## Related FRs

- FR-AUTH-001: JWT Token Generation
- FR-AUTH-002: JWT Token Validation

## Status

- **Current**: implemented
- **Since**: 2026-02-01
