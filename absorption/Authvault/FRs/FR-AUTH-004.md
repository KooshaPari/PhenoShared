# FR-AUTH-004: API Key Management

## ID
- **FR-ID**: FR-AUTH-004
- **Repository**: Authvault
- **Domain**: Authentication

## Description

The system SHALL support API key authentication for service-to-service communication. API keys SHALL be stored as SHA-256 hashes, never in plaintext.

## Acceptance Criteria

- [ ] Generates unique API keys with configurable prefixes
- [ ] Stores only SHA-256 hashes of API keys
- [ ] Validates API keys via hash comparison
- [ ] Supports API key expiration dates
- [ ] Allows API key revocation

## Test References

| Test File | Function | FR Reference |
|-----------|----------|--------------|
| `tests/api_key_tests.rs` | `test_api_key_generation` | `// @trace FR-AUTH-004` |
| `tests/api_key_tests.rs` | `test_api_key_validation` | `// @trace FR-AUTH-004` |

## Code References

| File | Function/Struct | FR Reference |
|------|-----------------|--------------|
| `src/api_key.rs` | `generate_api_key()` | `// @trace FR-AUTH-004` |
| `src/api_key.rs` | `validate_api_key()` | `// @trace FR-AUTH-004` |

## Related FRs

- FR-AUTH-002: JWT Token Validation

## Status

- **Current**: PLANNED
- **Since**: 2026-02-10
