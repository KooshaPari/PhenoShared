# FR-AUTH-005: Rate Limiting by Token

## ID
- **FR-ID**: FR-AUTH-005
- **Repository**: Authvault
- **Domain**: Security

## Description

The system SHALL enforce per-token rate limits to prevent abuse. Rate limits SHALL be configurable per token type (user, service, admin).

## Acceptance Criteria

- [ ] Tracks request counts per token
- [ ] Returns HTTP 429 when limit exceeded
- [ ] Includes Retry-After header in responses
- [ ] Supports burst allowances
- [ ] Resets counters on token refresh

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/rate_limit_tests.rs` | `test_token_rate_limit` | `// @trace FR-AUTH-005` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/rate_limit.rs` | `RateLimiter` | `// @trace FR-AUTH-005` |

## Related FRs

- FR-AUTH-002: JWT Token Validation

## Status

- **Current**: PLANNED
- **Since**: 2026-03-01
