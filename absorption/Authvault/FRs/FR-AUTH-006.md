# FR-AUTH-006: Token Revocation

## ID
- **FR-ID**: FR-AUTH-006
- **Repository**: Authvault
- **Domain**: Authentication

## Description

The system SHALL support token revocation for logout and security incidents. Revoked tokens SHALL be rejected immediately regardless of expiration time.

## Acceptance Criteria

- [ ] Maintains revocation list for access tokens
- [ ] Checks revocation on every validation
- [ ] Supports bulk revocation by user
- [ ] Supports revocation by token family
- [ ] Revocation takes effect within 5 seconds

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/revocation_tests.rs` | `test_token_revocation` | `// @trace FR-AUTH-006` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/revocation.rs` | `revoke_token()` | `// @trace FR-AUTH-006` |
| `src/token.rs` | `is_revoked()` | `// @trace FR-AUTH-006` |

## Related FRs

- FR-AUTH-002: JWT Token Validation
- FR-AUTH-003: Token Refresh

## Status

- **Current**: implemented
- **Since**: 2026-02-15
