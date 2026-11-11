# AuthKit Security Audit Report

**Date**: 2026-04-01
**Scope**: Cryptographic practices, key management, password hashing, JWT handling, session management
**Codebase**: authkit `convoy/authkit-stabilization/a55a5c68`

---

## Executive Summary

AuthKit is a Rust-based authentication and authorization library implementing JWT tokens, password hashing (Argon2id/Bcrypt), session management, and RBAC/ABAC policy. The codebase demonstrates good architectural hygiene (ports-and-adapters, async traits, clear domain boundaries) but contains several security concerns that range from design-level gaps to implementation weaknesses.

**Severity distribution**:
- **Critical**: 2
- **High**: 4
- **Medium**: 3
- **Low / Informational**: 3

---

## 1. Key Management

### CRIT-01: Hardcoded JWT Secret with No Key Derivation
**File**: `src/domain/auth.rs:96-110`
**Severity**: Critical

The `Authenticator` struct stores the JWT signing secret as a plain `String` and accepts it directly via `Authenticator::new(secret: impl Into<String>)`. There is no key derivation function (KDF) applied — the raw secret bytes are fed directly into the HMAC-SHA256 signing key.

**Risks**:
- Weak or short secrets produce weak HMAC keys directly.
- No key stretching means brute-force attacks on the secret are feasible if it leaks.
- No key rotation mechanism exists.

**Recommendation**:
- Accept a minimum secret length (>= 256 bits / 32 bytes) and reject shorter values.
- Provide an optional KDF (HKDF-SHA256) to derive the signing key from a master secret.
- Implement a key versioning / rotation scheme (e.g., include `kid` in the JWT header).

### CRIT-02: Secret Held in Memory as Plain Text
**File**: `src/domain/auth.rs:97`
**Severity**: Critical

The `secret: String` field in `Authenticator` holds the signing key in plaintext for the lifetime of the struct. Rust's memory safety does not zero out dropped `String` values, meaning the secret may persist in memory after the struct is dropped.

**Recommendation**:
- Use `zeroize::Zeroize` or `secrecy::Secret` to ensure the secret is zeroed on drop.
- Consider using `ring` or `libsodium` for key material handling.

---

## 2. JWT Handling

### HIGH-01: HS256 Algorithm — Vulnerable to Algorithm Confusion
**File**: `src/domain/auth.rs:125-128`
**Severity**: High

Token generation uses `jsonwebtoken::Header::default()`, which defaults to HS256 (HMAC-SHA256). The library supports RS256/ES256 asymmetric algorithms, but they are not exposed. HS256 requires the same secret for signing and verification, which:
- Prevents distributing verification keys to untrusted parties.
- Is vulnerable to algorithm confusion attacks if the verification side ever accepts `alg: none` or switches to RS256 with the HS256 secret as a public key.

**Recommendation**:
- Support RS256/ES256 for asymmetric signing.
- Explicitly set and validate the algorithm in the `Validation` struct (currently done implicitly via `default()`, which defaults to HS256 — this should be explicit).
- Add `validation.validate_exp = true` explicitly (it is true by default in jsonwebtoken 9.x, but should be documented).

### HIGH-02: 24-Hour Token Lifetime is Excessive
**File**: `src/domain/auth.rs:57`
**Severity**: High

Default token expiration is 24 hours. For access tokens, this is an unacceptably long window for abuse if a token is stolen.

**Recommendation**:
- Default access token lifetime should be 5-15 minutes.
- Implement a separate refresh token mechanism with longer lifetime (the code has `refresh_token_id` in sessions but no distinct refresh token generation or validation logic).

### HIGH-03: No Token Revocation / Blacklist
**File**: `src/domain/auth.rs:167-173`
**Severity**: High

The `refresh_token` method simply re-issues a new token from the old one. There is no mechanism to:
- Revoke a specific JWT before its natural expiration.
- Maintain a token blacklist / denylist.
- Detect token replay (the `jti` claim is generated but never checked against a store).

**Recommendation**:
- Store issued `jti` values in a token store with TTL matching token expiration.
- Check `jti` against the store during `verify_token`.
- On logout, add the current token's `jti` to the denylist.

### MED-01: Hardcoded Issuer and Audience Defaults
**File**: `src/domain/auth.rs:55-56, 107-108`
**Severity**: Medium

Default issuer and audience are both `"authkit"`. While configurable via `with_issuer()`, the defaults are weak and could cause confusion in multi-tenant deployments where different services share the same default.

**Recommendation**:
- Require explicit issuer and audience configuration (no defaults).
- Validate that `iss` and `aud` in incoming tokens match expected values.

---

## 3. Password Hashing

### HIGH-04: Argon2 Iteration Count Too Low
**File**: `src/adapters/hashers.rs:24`
**Severity**: High

Argon2id parameters: `memory=65536 KB (64 MB), iterations=3, parallelism=4, hash_length=32`.

The OWASP recommendation for Argon2id is **at least 3 iterations** (minimum) but **recommends higher** when memory is constrained. With 64 MB memory, 3 iterations is at the absolute minimum. The RFC 9106 recommendation is to maximize memory first, then iterations. For a server-side application, 64 MB is reasonable but iterations should be at least 4-6.

**Recommendation**:
- Increase iterations to at least 4 (preferably 6+).
- Make parameters configurable rather than hardcoded.
- Consider increasing memory to 128 MB or 256 MB for server-side hashing.

### MED-02: Bcrypt Cost Factor of 12 May Be Insufficient
**File**: `src/adapters/hashers.rs:49`
**Severity**: Medium

Default bcrypt cost is 12. As of 2026, OWASP recommends a cost factor of at least 10, but 12-14 is preferred for new applications. The current default of 12 is acceptable but should be configurable and periodically reassessed.

**Recommendation**:
- Make the cost factor configurable via constructor or builder.
- Document the recommended cost factor and review it annually.
- Consider Argon2id as the primary recommendation over bcrypt.

---

## 4. Session Management

### MED-03: Logout Does Not Revoke All User Sessions
**File**: `src/application/services.rs:116-127`
**Severity**: Medium

The `logout` method only revokes a single session by ID. It does not call `session_storage.delete_by_user()` to clear all sessions for the user. This means:
- A compromised account can maintain persistent access through other active sessions.
- Password changes do not invalidate existing sessions.

**Recommendation**:
- Add a `logout_all(user_id)` method that calls `delete_by_user()`.
- Call `delete_by_user()` on password change.
- Consider session fixation prevention by regenerating session IDs on privilege changes.

### LOW-01: Session ID Generation Uses Standard UUID v4
**File**: `src/domain/session.rs:13`
**Severity**: Low

`SessionId::new()` uses `uuid::Uuid::new_v4()`. UUID v4 provides 122 bits of randomness, which is generally sufficient. However, the `SessionId` wraps a `String` rather than the raw UUID bytes, and there is no additional entropy mixing.

**Recommendation**:
- Use `uuid::Uuid::new_v4()` directly without string wrapping for internal use, or ensure the string representation is not guessable.
- Consider adding server-side entropy to session IDs.

### LOW-02: No Session Binding to Client Fingerprint
**File**: `src/domain/session.rs:63-65`
**Severity**: Low

The `Session` struct has `ip_address` and `user_agent` fields, but they are optional and never validated during session verification. A stolen session token can be used from any IP or user agent.

**Recommendation**:
- Make IP and user agent binding configurable.
- Validate client fingerprint during session verification.
- Implement anomaly detection for session usage from new locations.

---

## 5. Storage Security

### LOW-03: In-Memory Storage Uses RwLock — Potential DoS
**File**: `src/adapters/storage.rs`
**Severity**: Low

The `InMemoryUserStorage` and `InMemorySessionStorage` use `Arc<RwLock<HashMap>>`. Under high concurrency, write lock contention could cause thread starvation. This is an implementation concern for the reference adapter, not a security vulnerability per se.

**Recommendation**:
- Use `tokio::sync::RwLock` for async-aware locking.
- Consider `dashmap` for lock-free concurrent access.

---

## 6. Missing Security Controls

### INFO-01: No Rate Limiting
There is no rate limiting on login attempts. The `AuthService::login` method has no mechanism to detect or prevent brute-force attacks.

**Recommendation**: Implement account lockout after N failed attempts, or integrate with a rate-limiting middleware.

### INFO-02: No Password Strength Validation
The `register` method accepts any password without strength checks. The `AuthError::PasswordTooWeak` variant exists but is never used.

**Recommendation**: Enforce minimum password length (>= 12 characters) and complexity requirements.

### INFO-03: No Audit Logging
There is no audit trail for authentication events (login, logout, token refresh, authorization decisions).

**Recommendation**: Add structured audit logging via the `tracing` crate for all security-relevant events.

---

## Summary of Recommendations by Priority

| Priority | Item | Effort |
|----------|------|--------|
| P0 | Implement key derivation (HKDF) for JWT secrets | Medium |
| P0 | Zeroize secrets in memory | Low |
| P0 | Add minimum secret length enforcement | Low |
| P1 | Reduce default token lifetime to 15 minutes | Low |
| P1 | Implement JWT revocation / denylist | Medium |
| P1 | Support asymmetric signing (RS256/ES256) | Medium |
| P1 | Increase Argon2id iterations to >= 4 | Low |
| P2 | Add `logout_all` to revoke all user sessions | Low |
| P2 | Make issuer/audience required configuration | Low |
| P2 | Make password hasher parameters configurable | Low |
| P3 | Implement rate limiting on login | Medium |
| P3 | Add password strength validation | Low |
| P3 | Add audit logging for security events | Medium |

---

## Conclusion

AuthKit has a solid architectural foundation with clear separation of concerns and good use of Rust's type system. The primary security concerns are:

1. **Key management** — secrets are handled too casually (no derivation, no zeroization, no rotation).
2. **Token lifecycle** — 24-hour access tokens with no revocation mechanism is a significant risk.
3. **Password hashing parameters** — Argon2id iteration count is at the minimum threshold.

Addressing the P0 and P1 items would bring AuthKit to a production-ready security posture.
