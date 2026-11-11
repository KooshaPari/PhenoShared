# FR-AUTH-009: Audit Logging

## ID
- **FR-ID**: FR-AUTH-009
- **Repository**: Authvault
- **Domain**: Security

## Description

The system SHALL emit audit logs for all authentication events including successful login, failed login, token refresh, and logout.

## Acceptance Criteria

- [ ] Logs all authentication attempts
- [ ] Records timestamp, IP, user agent, and result
- [ ] Logs token refresh events
- [ ] Logs token revocation events
- [ ] Supports log export

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/audit_tests.rs` | `test_login_audit` | `// @trace FR-AUTH-009` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/audit.rs` | `log_auth_event()` | `// @trace FR-AUTH-009` |

## Related FRs

- FR-AUTH-002: JWT Token Validation

## Status

- **Current**: implemented
- **Since**: 2026-02-25
