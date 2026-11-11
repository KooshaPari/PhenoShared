# Session Management Audit Report

**Date**: 2026-04-01
**Scope**: Session lifecycle, logout cleanup, session leaks
**Codebase**: authkit `convoy/authkit-stabilization/a55a5c68`

---

## Executive Summary

The session management implementation has **four session leak vectors** and **two critical cleanup deficiencies**. While the basic session lifecycle (create, validate, revoke) is structurally sound, logout does not provide complete session termination, and the in-memory storage adapter leaks index entries.

**Severity distribution**:
- **Critical**: 2
- **High**: 2
- **Medium**: 1

---

## Findings

### CRIT-01: Logout Does Not Invalidate JWT Tokens

**Files**: `src/application/services.rs:116-127`, `src/domain/auth.rs:167-173`
**Severity**: Critical

The `logout` method revokes the server-side session but does **not** invalidate the JWT token. Since JWTs are stateless, a stolen JWT remains valid for up to 24 hours after logout. The `jti` claim is generated on every token but is never checked against a revocation store.

**Impact**: A user who logs out cannot guarantee their token is unusable. An attacker with a stolen JWT retains access until natural expiration.

**Fix**: Implement a JWT token blacklist that stores revoked `jti` values with TTL matching token expiration. Check `jti` during `verify_token`.

---

### CRIT-02: No `logout_all` — Single Session Logout Only

**File**: `src/application/services.rs:116-127`
**Severity**: Critical

The `logout` method accepts a single `SessionId` and only revokes that one session. The `SessionStorage` trait has `delete_by_user()` but it is never called from `AuthService`. This means:

- A compromised account can maintain persistent access through other active sessions
- Password changes do not invalidate existing sessions
- Users cannot "log out of all devices"

**Impact**: Multi-device compromise persistence. A single stolen session on another device remains active even after the user logs out from their current device.

**Fix**: Add `logout_all(user_id)` method to `AuthService` that calls `session_storage.delete_by_user()`.

---

### HIGH-01: InMemorySessionStorage Leaks `by_user` Index Entries

**File**: `src/adapters/storage.rs:125-129`
**Severity**: High

The `delete(&self, id: &SessionId)` method removes the session from the `sessions` HashMap but does **not** remove the session ID from the `by_user` index. Over time, the `by_user` HashMap accumulates stale session IDs for deleted sessions.

```rust
async fn delete(&self, id: &SessionId) -> Result<(), String> {
    let mut sessions = self.sessions.write().map_err(|e| e.to_string())?;
    sessions.remove(&id.to_string());
    // BUG: by_user index is NOT cleaned up
    Ok(())
}
```

**Impact**: Memory leak in the index. The `by_user` HashMap grows unbounded as sessions are individually deleted. `delete_by_user()` would also attempt to remove already-deleted sessions (harmless but wasteful).

**Fix**: Scan `by_user` to remove the session ID from the user's list, and remove empty user entries.

---

### HIGH-02: Session::refresh() Does Not Revoke Old Session

**File**: `src/domain/session.rs:130-136`
**Severity**: High

The `refresh()` method mutates the session in place, generating a new `SessionId` and resetting timestamps. However, the old session ID is lost without being explicitly revoked. If the session storage still holds a reference to the old session ID, it becomes an orphaned entry (zombie session).

Additionally, the method sets `state = SessionState::Refreshed` and then immediately overwrites it with `state = SessionState::Active` on the next line. The `Refreshed` state is never observable.

**Impact**: Orphaned sessions in storage. The `Refreshed` state is dead code.

**Fix**: `refresh()` should return the old session ID so the caller can revoke it in storage, or the application layer should handle old-session cleanup.

---

### MED-01: No Expired Session Cleanup Mechanism

**File**: `src/adapters/storage.rs`, `src/application/services.rs`
**Severity**: Medium

There is no mechanism to purge expired or revoked sessions from storage. The `InMemorySessionStorage` will accumulate sessions indefinitely. The `SessionStorage` trait has no `delete_expired()` or `cleanup()` method.

**Impact**: Unbounded memory growth in production. Stale sessions remain queryable (though `is_valid()` would reject them).

**Fix**: Add a `delete_expired()` method to the `SessionStorage` trait and implement periodic cleanup.

---

## Session Lifecycle Analysis

### Current Flow

```
login() → create session → store session → return JWT + session
verify_token() → validate JWT (no session check)
logout(session_id) → load session → set state=Revoked → update session
```

### Problems

1. **JWT bypasses session check**: `verify_token()` only validates the JWT signature and expiration. It does not check if the corresponding session is still active.
2. **Logout is not atomic with token invalidation**: The JWT token returned at login is independent of the session. Revoking the session does not revoke the JWT.
3. **No session validation on token use**: A valid JWT can be used even if the session has been revoked server-side.

### Expected Flow (Secure)

```
login() → create session → store session → return JWT (with jti) + session
verify_token() → validate JWT → check jti against blacklist → check session state
logout(session_id) → add jti to blacklist → revoke session → delete session
logout_all(user_id) → add all jtis to blacklist → delete all sessions for user
```

---

## Recommendations by Priority

| Priority | Item | File(s) | Effort |
|----------|------|---------|--------|
| P0 | Add `logout_all(user_id)` to AuthService | `application/services.rs` | Low |
| P0 | Fix InMemorySessionStorage `delete()` to clean `by_user` index | `adapters/storage.rs` | Low |
| P1 | Implement JWT revocation/blacklist with `jti` tracking | `domain/auth.rs`, `application/services.rs` | Medium |
| P1 | Check session state during token verification | `application/services.rs` | Low |
| P1 | Fix `Session::refresh()` to return old session ID | `domain/session.rs` | Low |
| P2 | Add `delete_expired()` to SessionStorage trait | `domain/ports.rs`, `adapters/storage.rs` | Low |
| P2 | Remove dead `SessionState::Refreshed` or make it observable | `domain/session.rs` | Low |

---

## Conclusion

The session management implementation has fundamental gaps in logout completeness. The most critical issues are:

1. **JWT tokens survive logout** — the stateless nature of JWTs means logout only affects server-side session state, not the token itself.
2. **Single-session logout only** — no mechanism to terminate all sessions for a user.
3. **Memory leak in storage adapter** — the `by_user` index is not cleaned up on individual session deletion.

These issues mean that the current implementation does **not** guarantee complete session cleanup on logout.
