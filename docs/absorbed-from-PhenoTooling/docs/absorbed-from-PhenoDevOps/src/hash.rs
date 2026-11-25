//! Hash utilities.
//!
//! Provides SHA-256, Blake3 hashing and content-addressing stubs.
//! Wraps: `sha2` crate for SHA-256, `blake3` crate for Blake3.

use sha2::{Digest, Sha256};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum HashError {
    #[error("blake3 hash error: {0}")]
    Blake3(String),

    #[error("sha256 hash error: {0}")]
    Sha256(String),

    #[error("hex decode error: {0}")]
    HexDecode(String),
}

/// Supported hash algorithms for content-addressing.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HashAlgorithm {
    /// BLAKE3 — fastest option available
    Blake3,
    /// SHA-256 — widely compatible
    Sha256,
}

/// Compute a BLAKE3 hash of the given bytes.
/// Returns a 32-byte hash as a hex string.
pub fn blake3_hash(data: &[u8]) -> String {
    use blake3::Hasher;
    let mut hasher = Hasher::new();
    hasher.update(data);
    hasher.finalize().to_hex().to_string()
}

/// Compute a SHA-256 hash of the given bytes.
/// Returns a 32-byte hash as a hex string.
pub fn sha256_hash(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    hex::encode(result)
}

/// Derive a stable content-addressable ID from bytes using BLAKE3.
/// Shortcut for `blake3_hash(data)`; useful for content-addressing patterns.
pub fn content_id(data: &[u8]) -> String {
    blake3_hash(data)
}
