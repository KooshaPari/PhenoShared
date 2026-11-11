# Authvault Core Tasks

## Active Work

### Implementation Tasks

- [x] Implement Identity entity with email and password
- [x] Implement JWT token generation and validation
- [x] Implement password hashing with argon2 and bcrypt
- [x] Implement RBAC role hierarchy
- [x] Implement ABAC policy engine
- [x] Implement session management
- [x] Document and ship middleware adapter wiring for consumer repos
- [ ] Implement MFA (Multi-factor authentication)
- [ ] Implement passwordless authentication

### Quality Tasks

- [x] Add inline tests for domain logic
- [x] Verify clippy passes with zero warnings
- [ ] Add integration tests for auth flow
- [ ] Add performance benchmarks for token validation

## Status Log

- 2026-04-02: Core auth framework stabilized, 15 tests passing
- 2026-05-28: Resolved `cargo fmt --check` drift and normalized Rust formatting
- 2026-05-28: Added bearer-token JWT validation with explicit expired, signature,
  audience, and malformed error handling
- 2026-05-29: Added Authvault middleware adapter docs and request-claims injection layer
