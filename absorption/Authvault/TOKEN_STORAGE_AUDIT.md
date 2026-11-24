# AuthKit Token Storage Security Assessment

**Date:** 2026-04-01
**Scope:** `/workspace/rigs/dcce7578-2463-4dc2-9619-cc7b56d73896/worktrees/gt__polecat-43__3df2e431`
**Auditor:** Polecat-43

---

## Executive Summary

AuthKit is a Rust-based authentication and authorization framework using hexagonal architecture. It provides JWT generation/verification, session management, password hashing (Argon2id/Bcrypt), and RBAC/ABAC policy enforcement.

**Critical finding:** As a library, AuthKit does not implement token storage, HTTP transport, or cookie handling. All security of token persistence and transmission is delegated to the consumer. The library itself has several significant security gaps in token lifecycle management.

**Overall Risk Level:** HIGH — due to missing JWT revocation, no refresh token rotation, and plain-text secret key handling.

---

## 1. Token Storage Review

### 1.1 JWT Tokens
- **Storage Mechanism:** None. JWTs are generated as `String` values and returned to the caller.
- **Location:** `domain/auth.rs` — `generate_token()` returns `Result<String, AuthError>`.
- **Assessment:** Correct design for a library — the consumer decides where to store tokens. However, the library provides no guidance or utilities for secure storage.

### 1.2 Session Tokens
- **Storage Mechanism:** In-memory only via `InMemorySessionStorage`.
- **Implementation:** `Arc<RwLock<HashMap<String, Session>>>` in `adapters/storage.rs`.
- **Session fields:** `session_id`, `user_id`, `created_at`, `expires_at`, `state`, `ip_address`, `user_agent`, `refresh_token_id`.
- **Assessment:** Acceptable for a reference implementation. No persistent storage adapter exists. Sessions are not encrypted in memory.

### 1.3 OAuth2 Tokens
- **Status:** `AuthMethod::OAuth2` exists as an enum variant (`domain/auth.rs:15`) but has **zero implementation**.
- **Assessment:** Dead code path. No token exchange, provider integration, or OAuth2 flow exists.

### 1.4 API Keys
- **Status:** `AuthMethod::ApiKey` exists as an enum variant (`domain/auth.rs:14`) but has **zero implementation**.
- **Assessment:** Dead code path. No generation, storage, or validation logic.

### 1.5 Secret Key Storage
- **Finding (HIGH):** Signing secret stored as plain `String` in `Authenticator` struct (`domain/auth.rs:97`).
- **Risk:** Secret remains in heap memory without zeroization. Vulnerable to memory dumps, core dumps, and swap file exposure.
- **Missing:** No use of `zeroize` crate or `SecretString` pattern.

---

## 2. XSS Vulnerability Assessment

### 2.1 Token Exposure Surface
- **Finding (MEDIUM):** The library has no HTTP layer, so XSS is primarily a consumer concern.
- **However,** the library provides no CSRF token generation, no token binding (to IP/user-agent), and no nonce support that would help consumers mitigate XSS-based token theft.

### 2.2 JWT in Claims
- **Finding (MEDIUM):** `Claims.extra` field (`domain/auth.rs:46`) accepts arbitrary `HashMap<String, serde_json::Value>`.
- **Risk:** If custom claims contain user-controlled data and are reflected in responses without sanitization, this could enable injection attacks downstream.

### 2.3 Token Binding
- **Finding (LOW):** Sessions track `ip_address` and `user_agent`, but JWT claims do not include any device binding.
- **Risk:** A stolen JWT works from any device/location until expiration (up to 24 hours).

---

## 3. Secure Transmission (HTTPS)

### 3.1 Transport Security
- **Finding (MEDIUM):** The library has **no HTTP layer whatsoever**. No HTTPS enforcement, no `Set-Cookie` header generation, no `HttpOnly`/`Secure`/`SameSite` cookie flags.
- **Assessment:** Token transmission security is entirely the consumer's responsibility. The library neither helps nor hinders secure transport.

### 3.2 Cookie Handling
- **Finding:** Zero cookie handling code exists in the entire codebase.
- **Impact:** Consumers must implement their own cookie management for web applications. No guidance or utilities provided.

---

## 4. Token Expiration and Refresh Logic

### 4.1 JWT Expiration
- **Default:** 24 hours (`domain/auth.rs:57`).
- **Customization:** `generate_token_with_expiry()` accepts custom `chrono::Duration`.
- **Validation:** Uses `jsonwebtoken` library's built-in expiration check. `ExpiredSignature` maps to `AuthError::TokenExpired`.
- **Additional claims:** `nbf` (not-before) set to issuance time, `iat` (issued-at), `jti` (unique token ID).
- **Assessment:** Expiration logic is sound. 24-hour default is reasonable but on the longer side for access tokens.

### 4.2 JWT Refresh
- **Finding (HIGH):** `refresh_token()` (`domain/auth.rs:168-173`) reuses the same token pattern:
  1. Verifies existing token is valid.
  2. Extracts `sub` and `roles`.
  3. Generates a brand new token with fresh timestamps.
- **Critical Gap — No Refresh Token Rotation:** There is no separate short-lived access token + long-lived refresh token pattern. The same JWT is used for both access and refresh.
- **Critical Gap — No Token Revocation:** JWT tokens are stateless. Once issued, they cannot be revoked until expiration. The `logout()` method revokes the session but does NOT invalidate the JWT. A stolen JWT remains valid for up to 24 hours after logout.

### 4.3 Session Expiration
- **Default:** 24 hours (`domain/session.rs:79`).
- **Customization:** `with_expiry()` method accepts custom duration.
- **Validation:** `is_expired()` compares `Utc::now()` against `expires_at`. `is_valid()` checks both `state == Active` AND not expired.
- **Refresh:** `Session::refresh()` generates a new `SessionId`, resets timestamps, restores `Active` state.
- **Revocation:** `Session::revoke()` sets `state = SessionState::Revoked`. `logout()` in `application/services.rs` properly revokes sessions.
- **Assessment:** Session expiration logic is well-implemented.

---

## 5. Additional Security Findings

### 5.1 Signing Algorithm
- **Finding (HIGH):** Uses HS256 (symmetric) via `jsonwebtoken::Header::default()`.
- **Risk:** Same secret signs and verifies tokens. If the secret leaks, anyone can forge tokens.
- **Missing:** No RS256/ES256 (asymmetric) support.

### 5.2 Rate Limiting
- **Finding (MEDIUM):** `login()` has no rate limiting, account lockout after failed attempts, or exponential backoff.
- **Risk:** Vulnerable to brute-force and credential stuffing attacks.

### 5.3 Audit Logging
- **Finding (LOW):** `tracing` crate is a dependency but is never used. No logging of authentication events (login, logout, token refresh, failed attempts).

### 5.4 Missing Dependency
- **Finding (MEDIUM):** `regex::Regex::new()` is used in `domain/policy.rs:62` but `regex` is not listed in `Cargo.toml` dependencies. This would cause a compilation error.

---

## 6. Summary of Findings

| # | Finding | Severity | File |
|---|---------|----------|------|
| H1 | Secret key stored as plain `String` with no zeroization | HIGH | `domain/auth.rs:97` |
| H2 | No JWT token revocation/blacklist — tokens valid until expiration even after logout | HIGH | `domain/auth.rs` |
| H3 | No refresh token rotation — same token used for access and refresh | HIGH | `domain/auth.rs:168-173` |
| H4 | HS256 symmetric signing only — no asymmetric (RS256/ES256) support | HIGH | `domain/auth.rs` |
| M1 | No rate limiting or brute force protection on login | MEDIUM | `application/services.rs` |
| M2 | No cookie handling (HttpOnly, Secure, SameSite flags) | MEDIUM | N/A |
| M3 | No HTTPS/transport security enforcement | MEDIUM | N/A |
| M4 | No CSRF token or token binding support | MEDIUM | N/A |
| M5 | `Claims.extra` accepts arbitrary JSON — potential claim injection | MEDIUM | `domain/auth.rs:46` |
| M6 | `regex` dependency missing from Cargo.toml | MEDIUM | `domain/policy.rs:62` |
| L1 | JWT claims lack IP/user-agent binding | LOW | `domain/auth.rs` |
| L2 | No audit logging of auth events | LOW | All |
| L3 | `nbf` set to exact issuance time — no clock skew grace | LOW | `domain/auth.rs` |

---

## 7. Recommendations

### Immediate (HIGH)
1. **Implement JWT revocation:** Add a token blacklist or use short-lived JWTs with session-based validation.
2. **Implement refresh token rotation:** Separate access tokens (short-lived, 15min) from refresh tokens (long-lived, 7 days). Rotate refresh tokens on each use.
3. **Zeroize secret key:** Use `zeroize` crate and `SecretString` pattern for the signing secret.
4. **Add asymmetric signing support:** Implement RS256/ES256 for production deployments.

### Short-term (MEDIUM)
5. **Add rate limiting** to login endpoint with account lockout after N failed attempts.
6. **Add `regex` to `Cargo.toml`** dependencies to fix compilation.
7. **Provide cookie utilities** or documented patterns for `HttpOnly`, `Secure`, `SameSite` flags.
8. **Validate `Claims.extra`** with schema validation to prevent claim injection.

### Long-term (LOW)
9. **Add token binding** to JWT claims (IP hash, user-agent hash).
10. **Implement audit logging** using the existing `tracing` dependency.
11. **Add clock skew tolerance** to `nbf` validation.

---

## 8. Conclusion

AuthKit is a well-structured library with clean hexagonal architecture. Password hashing (Argon2id/Bcrypt) and session management are implemented correctly. However, the token lifecycle has critical gaps: no JWT revocation, no refresh token rotation, and insecure secret key handling. As a library, the absence of HTTP/cookie handling is acceptable, but the library should provide security guidance and utilities for consumers.

**The library is not production-ready in its current state** for any application requiring secure token management. The HIGH severity findings should be addressed before deployment.
