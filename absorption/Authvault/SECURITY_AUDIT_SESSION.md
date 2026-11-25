# AuthKit Session Management — Security Audit Report

**Date**: 2026-04-02
**Scope**: Session token generation, session expiration, session fixation protection, secure cookie settings
**Codebase**: authkit `gt/polecat-43/f2f0b26f`

---

## Executive Summary

AuthKit implements server-side session management with UUID v4 session IDs, a 24-hour absolute expiration window, and an in-memory storage adapter. The library has no HTTP layer and therefore provides no cookie handling. Several gaps exist: JWT tokens are not invalidated on logout, there is no sliding/inactivity timeout, no session fixation protection during login, and no cookie security guidance for consumers.

**Severity distribution**:
- **Critical**: 1
- **High**: 3
- **Medium**: 3
- **Low / Informational**: 3

---

## 1. Session Token Generation

### LOW-01: UUID v4 Session IDs — Adequate Entropy

**File**: `src/domain/session.rs:11-13`

```rust
impl SessionId {
    pub fn new() -> Self {
        Self(uuid::Uuid::new_v4().to_string())
    }
}
```

**Finding**: Session IDs are generated using UUID v4, which provides 122 bits of randomness sourced from the OS CSPRNG via the `uuid` crate's `getrandom` dependency. This is cryptographically adequate for session identifiers.

**Risk**: Low. UUID v4 is a standard, well-vetted approach for session ID generation.

**Recommendation**: No change required. If additional entropy is desired in the future, consider appending server-side entropy or using `rand::rngs::OsRng` with a 256-bit random byte sequence encoded as base64url.

---

## 2. Session Expiration

### HIGH-01: 24-Hour Default Expiration Is Excessive

**File**: `src/domain/session.rs:73`

```rust
expires_at: now + chrono::Duration::hours(24),
```

**Finding**: Both session entities and JWT tokens default to a 24-hour expiration window. OWASP recommends 2-4 hours for session timeout for standard applications and 12-24 hours only for low-risk scenarios. For access tokens specifically, 5-15 minutes is recommended.

**Risk**: High. A stolen session or JWT remains usable for up to 24 hours without any server-side check.

**Recommendation**:
- Reduce default session expiration to 1-4 hours for standard use.
- Reduce default JWT access token expiration to 15 minutes.
- Implement a proper refresh token flow with longer-lived refresh tokens (the `refresh_token_id` field exists but is not used in a distinct refresh token validation path).

### HIGH-02: No Sliding/Inactivity Timeout

**File**: `src/domain/session.rs:114-116`

```rust
pub fn touch(&mut self) {
    self.last_activity = Utc::now();
}
```

**Finding**: The `touch()` method updates `last_activity` but does NOT extend `expires_at`. This means `last_activity` is tracked but never used for sliding expiration. Sessions expire on an absolute timer regardless of user activity.

**Risk**: High. Active users are logged out after the absolute timeout, while inactive sessions remain valid until the absolute expiration. This is the inverse of good session hygiene.

**Recommendation**: Implement sliding expiration by extending `expires_at` on each `touch()` call, up to a maximum session lifetime. Example:

```rust
pub fn touch(&mut self, max_lifetime: chrono::Duration) {
    self.last_activity = Utc::now();
    let new_expiry = self.last_activity + chrono::Duration::hours(1); // inactivity timeout
    let max_expiry = self.created_at + max_lifetime;
    self.expires_at = std::cmp::min(new_expiry, max_expiry);
}
```

### MED-01: Expired State Never Set

**File**: `src/domain/session.rs:29-37`

```rust
pub enum SessionState {
    #[default]
    Active,
    Expired,
    Revoked,
    Refreshed,
}
```

**Finding**: The `SessionState::Expired` variant exists but is never assigned anywhere in the codebase. Expiration is determined solely by comparing `expires_at` to `Utc::now()` in `is_expired()`. The state field is never updated to `Expired` when a session passes its expiration time.

**Risk**: Medium. This creates inconsistency: a session can be `Active` in state but expired by time. Consumers checking only `state` will miss expired sessions.

**Recommendation**: Either remove the `Expired` variant and rely solely on time-based checks, or update the state to `Expired` in `is_expired()` or during `delete_expired()` cleanup.

---

## 3. Session Fixation Protection

### HIGH-03: No Session Regeneration on Authentication

**File**: `src/application/services.rs:72-108`

**Finding**: The `login()` method creates a brand new session after successful authentication. There is no concept of anonymous or pre-authentication sessions in the current codebase. This partially mitigates classic session fixation (where an attacker plants a known session ID before the victim logs in), since sessions are only created server-side post-auth.

However, there is no protection if:
1. A consumer creates a session before authentication and passes it to `login()`.
2. A consumer reuses a session ID across authentication boundaries.

The `Session::refresh()` method (`src/domain/session.rs:124-131`) does regenerate the session ID, but it is never called during the login flow.

**Risk**: Medium-High. The current design mitigates the most common attack vector by not supporting anonymous sessions. But the library provides no explicit session fixation protection API or guidance.

**Recommendation**:
- Document that sessions should only be created after successful authentication.
- Add an explicit `regenerate_id()` method that creates a new session with the same user data but a new ID, and recommend calling it after privilege changes.
- Consider adding a `SessionFixationProtection` trait that consumers can implement.

---

## 4. Secure Cookie Settings

### CRIT-01: No Cookie Handling Whatsoever

**Finding**: A search for `cookie`, `Cookie`, `HttpOnly`, `Secure`, `SameSite`, and `Set-Cookie` across all source files returned zero matches. AuthKit is a library with no HTTP layer and provides:

- No cookie creation utilities
- No `Set-Cookie` header generation
- No guidance on secure cookie flags
- No enforcement of `HttpOnly`, `Secure`, or `SameSite` attributes

**Risk**: Critical. Consumers of this library are entirely responsible for cookie security. Without guidance or utilities, it is highly likely that consumers will set insecure cookies (missing `HttpOnly`, `Secure`, or `SameSite` flags), leading to XSS-based session theft, CSRF attacks, or cookie leakage over unencrypted connections.

**Recommendation**:
- Provide a `CookieBuilder` or `SessionCookieConfig` struct that enforces secure defaults:
  ```rust
  pub struct SessionCookieConfig {
      pub http_only: bool,    // default: true
      pub secure: bool,       // default: true
      pub same_site: SameSite, // default: Strict or Lax
      pub path: String,       // default: "/"
      pub max_age: Duration,  // derived from session expiry
  }
  ```
- Document secure cookie requirements prominently in README and API docs.
- Consider providing a `set_cookie_header()` method that returns a properly formatted `Set-Cookie` header string.

---

## 5. Session Invalidation

### HIGH-04: JWT Tokens Not Invalidated on Logout

**Files**: `src/application/services.rs:121-142`, `src/domain/auth.rs:144-160`

**Finding**: The `logout()` method correctly revokes and deletes the server-side session. However, the JWT token returned at login remains valid for up to 24 hours. The `verify_token()` method only validates the JWT signature and expiration — it does NOT:

1. Check the session store to verify the session is still active
2. Check a token blacklist/denylist
3. Validate the `jti` claim against any revocation store

A stolen JWT remains fully usable after the user has logged out, until its natural expiration.

**Risk**: High. Logout does not actually terminate the user's ability to make authenticated requests if the attacker has the JWT.

**Recommendation**:
- Implement a token denylist keyed by `jti` with TTL matching token expiration.
- On logout, add the current token's `jti` to the denylist.
- In `verify_token()`, check the `jti` against the denylist before accepting the token.
- Alternatively, cross-reference the JWT's `sub` claim against active sessions in the session store during verification.

### MED-02: `verify_token()` Does Not Check Session State

**File**: `src/application/services.rs:111-113`

```rust
pub fn verify_token(&self, token: &str) -> Result<Claims, AuthError> {
    self.authenticator.verify_token(token)
}
```

**Finding**: The `AuthService::verify_token()` method delegates directly to the JWT authenticator. It never checks whether the associated session is still active, revoked, or expired in the session store.

**Risk**: Medium. Even if a session is revoked server-side, JWT verification will succeed.

**Recommendation**: Add session state validation to the verification flow. Either:
1. Accept a `SessionStorage` reference in `verify_token()` and cross-reference.
2. Create a separate `verify_token_with_session()` method that performs both checks.

### MED-03: `logout()` Redundantly Updates Then Deletes

**File**: `src/application/services.rs:121-142`

```rust
session.revoke();
self.session_storage.update(&session).await?;
self.session_storage.delete(session_id).await?;
```

**Finding**: The logout flow revokes the session, updates it in storage, then immediately deletes it. The `update()` call is redundant since the session is deleted in the next line.

**Risk**: Low. This is a correctness/cleanliness issue, not a security vulnerability. However, if the `delete()` were to fail, the session would be left in a `Revoked` state rather than removed — which is actually safer than the alternative.

**Recommendation**: Keep the current flow as a defense-in-depth measure (revoked state persists if delete fails), but add a comment explaining the intent. Alternatively, remove the `update()` call if the storage implementation guarantees atomic operations.

---

## 6. Session Storage

### LOW-02: In-Memory Only — No Persistent Adapter

**File**: `src/adapters/storage.rs:78-180`

**Finding**: The only `SessionStorage` implementation is `InMemorySessionStorage` using `Arc<RwLock<HashMap>>`. No database, Redis, or other persistent storage adapter is provided.

**Risk**: Low for a reference implementation. However, consumers in production will need to implement their own persistent storage, and the library provides no guidance on secure session storage patterns (e.g., encrypting session data at rest, securing Redis connections).

**Recommendation**: Provide at least one persistent storage adapter (e.g., Redis) or document the requirements for a production-ready session store.

### LOW-03: Standard `RwLock` in Async Context

**File**: `src/adapters/storage.rs:7`

```rust
use std::sync::{Arc, RwLock};
```

**Finding**: The storage adapter uses `std::sync::RwLock` rather than `tokio::sync::RwLock`. Under async workloads, holding a synchronous lock across `.await` points can cause thread starvation.

**Risk**: Low. This is a performance/reliability concern rather than a security issue, but could lead to denial-of-service under high concurrency.

**Recommendation**: Switch to `tokio::sync::RwLock` or use `dashmap` for lock-free concurrent access.

---

## 7. Client Fingerprinting

### LOW-04: IP/User-Agent Tracked But Never Validated

**File**: `src/domain/session.rs:57-59`

```rust
pub ip_address: Option<String>,
pub user_agent: Option<String>,
```

**Finding**: The `Session` struct stores optional `ip_address` and `user_agent` fields, but these are never validated during session verification. A stolen session can be used from any IP address or user agent.

**Risk**: Low. The fields are present for future use but provide no current protection.

**Recommendation**: Make client fingerprinting configurable. Add an optional validation step during session verification that compares the current request's IP/user-agent against the stored values.

---

## 8. Refresh Token Handling

### HIGH-05: No Refresh Token Rotation

**File**: `src/application/services.rs:116-118`

```rust
pub fn refresh_token(&self, token: &str) -> Result<String, AuthError> {
    self.authenticator.refresh_token(token)
}
```

**Finding**: The `refresh_token()` method simply re-issues a new JWT from the old one without:
1. Validating a separate refresh token
2. Rotating the refresh token ID
3. Invalidating the old refresh token
4. Checking if the session is still active

The `refresh_token_id` field on `Session` is set during login but never used in the refresh flow.

**Risk**: High. A stolen refresh token can be used indefinitely to generate new access tokens. There is no token rotation to detect theft (if both the legitimate user and attacker try to use the same refresh token, there is no detection mechanism).

**Recommendation**:
- Implement proper refresh token rotation: generate a new refresh token on each use and invalidate the old one.
- Validate the refresh token ID against the session store before issuing a new access token.
- Implement refresh token reuse detection to identify token theft.

---

## Summary of Findings

| ID | Area | Severity | Title |
|----|------|----------|-------|
| CRIT-01 | Cookies | Critical | No cookie handling or guidance for consumers |
| HIGH-01 | Expiration | High | 24-hour default expiration is excessive |
| HIGH-02 | Expiration | High | No sliding/inactivity timeout |
| HIGH-03 | Fixation | High | No session regeneration on authentication |
| HIGH-04 | Invalidation | High | JWT tokens not invalidated on logout |
| HIGH-05 | Refresh | High | No refresh token rotation |
| MED-01 | Expiration | Medium | `Expired` state variant never assigned |
| MED-02 | Invalidation | Medium | `verify_token()` does not check session state |
| MED-03 | Invalidation | Medium | `logout()` redundantly updates then deletes |
| LOW-01 | Generation | Low | UUID v4 session IDs — adequate but could be stronger |
| LOW-02 | Storage | Low | In-memory only — no persistent adapter |
| LOW-03 | Storage | Low | `std::sync::RwLock` in async context |
| LOW-04 | Fingerprinting | Low | IP/user-agent tracked but never validated |

---

## Prioritized Recommendations

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P0 | Add cookie security utilities/config with secure defaults | Medium | Critical |
| P0 | Implement JWT revocation/denylist on logout | Medium | High |
| P1 | Reduce default session/JWT expiration | Low | High |
| P1 | Implement sliding/inactivity timeout | Low | High |
| P1 | Implement refresh token rotation | Medium | High |
| P2 | Add session state check to `verify_token()` | Low | Medium |
| P2 | Document session fixation prevention requirements | Low | Medium |
| P3 | Provide persistent storage adapter or documentation | Medium | Low |
| P3 | Add client fingerprinting validation | Medium | Low |

---

## Conclusion

AuthKit's session management has a reasonable foundation with UUID v4 session IDs, server-side session storage, and explicit revocation support. The most critical gaps are:

1. **No cookie security** — the library provides zero guidance or utilities for secure cookie handling, leaving consumers vulnerable to XSS and CSRF.
2. **JWT bypasses session state** — stateless JWT tokens remain valid after logout, undermining the purpose of server-side session management.
3. **Excessive default expiration** — 24-hour access tokens with no sliding window is inappropriate for most use cases.
4. **No refresh token rotation** — the refresh token mechanism is incomplete and vulnerable to token theft.

Addressing the P0 and P1 items would bring AuthKit's session management to a production-ready security posture.
