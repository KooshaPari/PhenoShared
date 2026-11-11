# Test Coverage Matrix

**Project**: Authvault  
**Document Version**: 1.0  
**Last Updated**: 2026-04-02

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| Functional Requirements | 9 implemented (FR-AUTH-001/002/003/006/008/009 + identity/policy/session) |
| Test Files | 9 (unit), 1 (integration) |
| Test Functions | 258 passing (run: `cargo test`) |
| Coverage Target | 80% |
| Current Coverage | Line coverage measured via `cargo-llvm-cov` — run `cargo llvm-cov` to generate report |

---

## Test Categories

### Unit Tests
- **Location**: As appropriate for language
- **Purpose**: Test individual components in isolation
- **Coverage Target**: 90%

### Integration Tests
- **Location**: tests/integration/
- **Purpose**: Test component interactions
- **Coverage Target**: 75%

---

## FR to Test Coverage Mapping

| FR ID | Description | Test Files | Coverage Status |
|-------|-------------|------------|-----------------|
| FR-AUTH-001 | JWT Token Generation | `src/domain/auth.rs` (inline), `tests/unit_tests.rs` | Covered |
| FR-AUTH-002 | JWT Token Validation | `src/domain/auth.rs` (inline), `tests/unit_tests.rs` | Covered |
| FR-AUTH-003 | Token Refresh | `src/domain/auth.rs` (inline), `tests/unit_tests.rs` | Covered |
| FR-AUTH-004 | API Key Management | — | Migrated to AuthKit |
| FR-AUTH-005 | Rate Limiting | — | Migrated to AuthKit |
| FR-AUTH-006 | Token Revocation | `src/domain/auth.rs` (inline), `tests/unit_tests.rs` | Covered |
| FR-AUTH-007 | OAuth2 Provider | — | Migrated to AuthKit |
| FR-AUTH-008 | Session Management | `src/domain/session.rs` (inline), `tests/session_is_valid.rs` | Covered |
| FR-AUTH-009 | Audit Logging | `src/adapters/` (inline), `tests/integration_tests.rs` | Covered |
| FR-AUTH-010 | Multi-Factor Authentication | — | Migrated to AuthKit |

---

## Coverage Gaps

### Critical Gaps
1. No fuzzing coverage on token parsing or crypto adapters (fuzz target now wires `jsonwebtoken::decode` — run via `cargo fuzz run crypto_fuzzer`)
2. No property-based tests for PKCE code-verifier/challenge generation

### Partial Coverage
1. Integration tests require Redis/Postgres — unit tests cover domain logic only without infrastructure
2. `src/adapters/vault.rs` — KMS/vault adapter has 2 ignored doc-tests (require HSM setup)

---

## Recommendations

### Immediate Actions
1. Add unit tests for domain types
2. Add integration tests for adapters

### Short-term Actions
1. Increase coverage to 80%

---

**Last Updated**: 2026-04-02
