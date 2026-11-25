//! W44-B4 in-tree KMS stub.
//!
//! This is a placeholder. The real implementation is human-gated (D-W44-1,
//! picked L22). Once the policy is in place, this file becomes the wrapper
//! around platform credential stores (macOS Keychain, Linux secret-service,
//! Windows Credential Manager).
//!
//! **Status**: stub. All calls return [`KmsError::NotImplemented`].

use std::fmt;

/// Errors surfaced by the in-tree KMS.
#[derive(Debug)]
pub enum KmsError {
    /// The platform credential store is reachable but the requested key
    /// is not present. (Real impl: Keychain returns errSecItemNotFound.)
    KeyNotFound { key: String },

    /// The human-gated policy decision (D-W44-1) has not been made yet.
    /// All KMS calls return this until the L22 path is implemented.
    NotImplemented,

    /// I/O error talking to the platform credential store.
    Io(String),
}

impl fmt::Display for KmsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            KmsError::KeyNotFound { key } => write!(f, "key not found: {key}"),
            KmsError::NotImplemented => write!(
                f,
                "sl-kms stub: human-gated D-W44-1 (L22 KMS path) not yet implemented; \
                 see docs/ops/w44-b4-kms-rollout.md"
            ),
            KmsError::Io(s) => write!(f, "KMS I/O error: {s}"),
        }
    }
}

impl std::error::Error for KmsError {}

/// Result alias for KMS operations.
pub type Result<T> = std::result::Result<T, KmsError>;

/// Look up a named secret in the platform credential store.
///
/// # Status
/// Stub: returns `Err(KmsError::NotImplemented)`.
pub fn get(_key: &str) -> Result<Vec<u8>> {
    Err(KmsError::NotImplemented)
}

/// Store a named secret in the platform credential store.
///
/// # Status
/// Stub: returns `Err(KmsError::NotImplemented)`.
pub fn put(_key: &str, _value: &[u8]) -> Result<()> {
    Err(KmsError::NotImplemented)
}

/// Delete a named secret from the platform credential store.
///
/// # Status
/// Stub: returns `Err(KmsError::NotImplemented)`.
pub fn delete(_key: &str) -> Result<()> {
    Err(KmsError::NotImplemented)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn get_returns_not_implemented() {
        assert!(matches!(get("any"), Err(KmsError::NotImplemented)));
    }

    #[test]
    fn put_returns_not_implemented() {
        assert!(matches!(put("any", b"value"), Err(KmsError::NotImplemented)));
    }

    #[test]
    fn delete_returns_not_implemented() {
        assert!(matches!(delete("any"), Err(KmsError::NotImplemented)));
    }

    #[test]
    fn display_messages_are_clear() {
        assert!(KmsError::NotImplemented.to_string().contains("D-W44-1"));
    }
}