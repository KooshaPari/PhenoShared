# Traceability Matrix

**Project**: Authvault  
**Branch**: integration/consolidate  
**Last Updated**: 2025-06-14

---

## Requirement | Source | Test | Status

| Requirement | Source | Test | Status |
|-------------|--------|------|--------|
| FR-AUTHVAULT-001: Register new user with email and password | `src/application/services.rs` | `tests/integration_tests.rs::test_register_new_user` | ✅ Pass |
| FR-AUTHVAULT-002: Reject duplicate registration for same email | `src/application/services.rs` | `tests/integration_tests.rs::test_register_duplicate_user_fails` | ✅ Pass |
| FR-AUTHVAULT-003: Authenticate user with valid credentials and issue session token | `src/application/services.rs` | `tests/integration_tests.rs::test_login_valid_credentials` | ✅ Pass |
| FR-AUTHVAULT-004: Reject login with invalid password | `src/application/services.rs` | `tests/integration_tests.rs::test_login_invalid_password` | ✅ Pass |
| FR-AUTHVAULT-070: Generate signed JWT token for authenticated user | `src/domain/auth.rs` | `tests/unit_tests.rs::authenticator_tests::test_authenticator_new` | ✅ Pass |

---

## Notes

- All five features are covered by existing automated tests in the `tests/` directory.
- Unit tests trace to domain-level requirements (`FR-AUTHVAULT-0xx` range).
- Integration tests trace to application-level requirements (`FR-AUTHVAULT-00x` range).
- Status reflects current CI/test suite results on `integration/consolidate`.
