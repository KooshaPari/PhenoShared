//! Auth middleware — PASETO-style token validation and owner-scoping.
//!
//! Tokens carry a subject (owner), expiry, issued-at timestamp, and scope.
//! Validation checks expiry and verifies a signature derived from the token
//! fields XOR-ed with a shared secret.  Owner-scoping checks that
//! `token.sub` matches the resource owner.

use std::time::{SystemTime, UNIX_EPOCH};

use thiserror::Error;

/// An authentication token modelling a simplified PASETO claim set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthToken {
    /// Subject — the owner/principal the token was issued to.
    pub sub: String,
    /// Expiry as seconds since the Unix epoch.
    pub exp: u64,
    /// Issued-at as seconds since the Unix epoch.
    pub iat: u64,
    /// Scope / role granted by the token (e.g. `"upload"`, `"admin"`).
    pub scope: String,
    /// Signature bytes computed over `sub`, `exp`, `iat`, and `scope`.
    pub signature: Vec<u8>,
}

/// Errors produced by auth operations.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum AuthError {
    #[error("token has expired")]
    ExpiredToken,
    #[error("invalid token signature")]
    InvalidSignature,
    #[error("token is missing required claims")]
    MissingClaims,
    #[error("unauthorized: subject does not match resource owner")]
    Unauthorized,
}

/// Compute a pseudo-signature by XOR-ing bytes of the token fields with the
/// shared secret.  This is intentionally simple — real deployments should use
/// HMAC / Ed25519 — but it is sufficient for unit-test coverage of the auth
/// middleware flow.
fn compute_signature(sub: &str, exp: u64, iat: u64, scope: &str, secret: &[u8]) -> Vec<u8> {
    let mut payload = Vec::new();
    payload.extend_from_slice(sub.as_bytes());
    payload.extend_from_slice(&exp.to_le_bytes());
    payload.extend_from_slice(&iat.to_le_bytes());
    payload.extend_from_slice(scope.as_bytes());

    if secret.is_empty() {
        return payload;
    }

    payload
        .iter()
        .enumerate()
        .map(|(i, b)| b ^ secret[i % secret.len()])
        .collect()
}

/// Create a fresh [`AuthToken`] with `iat` set to the current wall-clock time
/// and `exp` set to `iat + expiry_secs`.
pub fn create_token(sub: &str, secret: &[u8], expiry_secs: u64) -> AuthToken {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock is before Unix epoch")
        .as_secs();

    let exp = now.saturating_add(expiry_secs);
    let scope = "upload".to_string();
    let signature = compute_signature(sub, exp, now, &scope, secret);

    AuthToken {
        sub: sub.to_string(),
        exp,
        iat: now,
        scope,
        signature,
    }
}

/// Validate that a token is not expired and that its signature matches the
/// one computed with the given `secret`.
pub fn validate_token(token: &AuthToken, secret: &[u8]) -> Result<(), AuthError> {
    if token.sub.is_empty() || token.scope.is_empty() {
        return Err(AuthError::MissingClaims);
    }

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock is before Unix epoch")
        .as_secs();

    if token.exp <= now {
        return Err(AuthError::ExpiredToken);
    }

    let expected = compute_signature(&token.sub, token.exp, token.iat, &token.scope, secret);
    if token.signature != expected {
        return Err(AuthError::InvalidSignature);
    }

    Ok(())
}

/// Check that `token.sub` matches the `resource_owner`, confirming the token
/// holder is authorised to access the resource.
pub fn check_owner_permission(token: &AuthToken, resource_owner: &str) -> Result<(), AuthError> {
    if token.sub == resource_owner {
        Ok(())
    } else {
        Err(AuthError::Unauthorized)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_token_valid() {
        let secret = b"super-secret-key";
        let token = create_token("alice", secret, 3600);
        assert!(validate_token(&token, secret).is_ok());
    }

    #[test]
    fn test_validate_token_expired() {
        let secret = b"super-secret-key";
        let mut token = create_token("alice", secret, 3600);
        // Force expiry into the past.
        token.exp = 1;
        assert_eq!(validate_token(&token, secret), Err(AuthError::ExpiredToken));
    }

    #[test]
    fn test_check_owner_permission_match() {
        let secret = b"key";
        let token = create_token("alice", secret, 600);
        assert!(check_owner_permission(&token, "alice").is_ok());
    }

    #[test]
    fn test_check_owner_permission_mismatch() {
        let secret = b"key";
        let token = create_token("alice", secret, 600);
        assert_eq!(check_owner_permission(&token, "bob"), Err(AuthError::Unauthorized));
    }
}
