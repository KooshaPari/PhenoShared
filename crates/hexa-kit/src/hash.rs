//! Hash utilities.
//!
//! Lightweight, self-contained implementations used by the top-level
//! `hexakit` crate.

use sha2::{Digest, Sha256};

/// Supported hash algorithms.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HashAlgorithm {
    Sha256,
    Blake3,
}

/// Compute SHA-256 hash of bytes, returned as hex string.
pub fn sha256_hash(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

/// Compute Blake3 hash of bytes, returned as hex string.
pub fn blake3_hash(data: &[u8]) -> String {
    let hash = blake3::hash(data);
    hash.to_hex().to_string()
}

/// Compute a content-addressable ID using the specified algorithm.
/// Format: `{algorithm}:{hex_hash}`
pub fn content_id(data: &[u8], algorithm: HashAlgorithm) -> String {
    match algorithm {
        HashAlgorithm::Sha256 => format!("sha256:{}", sha256_hash(data)),
        HashAlgorithm::Blake3 => format!("blake3:{}", blake3_hash(data)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_vector() {
        let hash = sha256_hash(b"");
        assert_eq!(
            hash,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn blake3_deterministic() {
        let h1 = blake3_hash(b"test data");
        let h2 = blake3_hash(b"test data");
        assert_eq!(h1, h2);
        assert_eq!(h1.len(), 64);
    }
}
