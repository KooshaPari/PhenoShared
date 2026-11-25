//! # Phenotype Content Hash
//!
//! Content-addressed hashing utilities for data integrity.
//! Supports SHA-256, SHA3-256, and BLAKE3 hash algorithms.
//!
//! ## Example
//!
//! ```rust
//! use phenotype_content_hash::{ContentHash, HashAlgorithm};
//!
//! let data = b"hello world";
//! let hash = ContentHash::compute(data, HashAlgorithm::Blake3);
//! println!("Hash: {}", hash.to_hex());
//! ```

use sha2::{Digest as Sha2Digest, Sha256};
use sha3::Sha3_256;
use std::fmt;

/// Hash algorithm selection
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum HashAlgorithm {
    /// SHA-256 (32 bytes)
    Sha256,
    /// SHA3-256 (32 bytes)
    Sha3_256,
    /// BLAKE3 (32 bytes) - fastest, recommended
    Blake3,
}

impl Default for HashAlgorithm {
    fn default() -> Self {
        HashAlgorithm::Blake3
    }
}

impl fmt::Display for HashAlgorithm {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            HashAlgorithm::Sha256 => write!(f, "sha256"),
            HashAlgorithm::Sha3_256 => write!(f, "sha3-256"),
            HashAlgorithm::Blake3 => write!(f, "blake3"),
        }
    }
}

/// A computed content hash
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct ContentHash {
    algorithm: HashAlgorithm,
    bytes: Vec<u8>,
}

impl ContentHash {
    /// Create a new content hash from raw bytes
    pub fn new(algorithm: HashAlgorithm, bytes: Vec<u8>) -> Self {
        Self { algorithm, bytes }
    }

    /// Compute hash of data using specified algorithm
    pub fn compute(data: &[u8], algorithm: HashAlgorithm) -> Self {
        let bytes = match algorithm {
            HashAlgorithm::Sha256 => {
                let mut hasher = Sha256::new();
                hasher.update(data);
                hasher.finalize().to_vec()
            }
            HashAlgorithm::Sha3_256 => {
                let mut hasher = Sha3_256::new();
                hasher.update(data);
                hasher.finalize().to_vec()
            }
            HashAlgorithm::Blake3 => blake3::hash(data).as_bytes().to_vec(),
        };
        Self { algorithm, bytes }
    }

    /// Compute hash using default algorithm (Blake3)
    pub fn compute_default(data: &[u8]) -> Self {
        Self::compute(data, HashAlgorithm::default())
    }

    /// Get the algorithm used
    pub fn algorithm(&self) -> HashAlgorithm {
        self.algorithm
    }

    /// Get the hash bytes
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Convert to hex string
    pub fn to_hex(&self) -> String {
        hex::encode(&self.bytes)
    }

    /// Create from hex string
    pub fn from_hex(algorithm: HashAlgorithm, hex_str: &str) -> Result<Self, ContentHashError> {
        let bytes =
            hex::decode(hex_str).map_err(|e| ContentHashError::InvalidHex(e.to_string()))?;
        Ok(Self { algorithm, bytes })
    }

    /// Verify data matches this hash
    pub fn verify(&self, data: &[u8]) -> bool {
        let computed = Self::compute(data, self.algorithm);
        computed.bytes == self.bytes
    }

    /// Get hash with algorithm prefix (e.g., "blake3:abc123...")
    pub fn to_prefixed_hex(&self) -> String {
        format!("{}:{}", self.algorithm, self.to_hex())
    }

    /// Parse from prefixed hex string
    pub fn from_prefixed_hex(s: &str) -> Result<Self, ContentHashError> {
        let parts: Vec<&str> = s.splitn(2, ':').collect();
        if parts.len() != 2 {
            return Err(ContentHashError::InvalidFormat(
                "Expected format: algorithm:hex".to_string(),
            ));
        }

        let algorithm = match parts[0] {
            "sha256" => HashAlgorithm::Sha256,
            "sha3-256" => HashAlgorithm::Sha3_256,
            "blake3" => HashAlgorithm::Blake3,
            other => {
                return Err(ContentHashError::InvalidAlgorithm(other.to_string()));
            }
        };

        Self::from_hex(algorithm, parts[1])
    }
}

impl fmt::Display for ContentHash {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.to_prefixed_hex())
    }
}

/// Errors that can occur when working with content hashes
#[derive(Debug, thiserror::Error)]
pub enum ContentHashError {
    #[error("invalid hex: {0}")]
    InvalidHex(String),
    #[error("invalid format: {0}")]
    InvalidFormat(String),
    #[error("invalid algorithm: {0}")]
    InvalidAlgorithm(String),
}

/// Trait for types that can compute their own content hash
pub trait Hashable {
    /// Compute the content hash of this value
    fn content_hash(&self, algorithm: HashAlgorithm) -> ContentHash;

    /// Compute hash with default algorithm
    fn content_hash_default(&self) -> ContentHash {
        self.content_hash(HashAlgorithm::default())
    }
}

impl Hashable for [u8] {
    fn content_hash(&self, algorithm: HashAlgorithm) -> ContentHash {
        ContentHash::compute(self, algorithm)
    }
}

impl Hashable for Vec<u8> {
    fn content_hash(&self, algorithm: HashAlgorithm) -> ContentHash {
        ContentHash::compute(self, algorithm)
    }
}

impl Hashable for str {
    fn content_hash(&self, algorithm: HashAlgorithm) -> ContentHash {
        ContentHash::compute(self.as_bytes(), algorithm)
    }
}

impl Hashable for String {
    fn content_hash(&self, algorithm: HashAlgorithm) -> ContentHash {
        ContentHash::compute(self.as_bytes(), algorithm)
    }
}

/// Compute hash of a JSON-serializable value
pub fn hash_json_value<T: serde::Serialize>(
    value: &T,
    algorithm: HashAlgorithm,
) -> Result<ContentHash, serde_json::Error> {
    let json = serde_json::to_vec(value)?;
    Ok(ContentHash::compute(&json, algorithm))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256() {
        let data = b"hello";
        let hash = ContentHash::compute(data, HashAlgorithm::Sha256);
        assert_eq!(hash.algorithm, HashAlgorithm::Sha256);
        assert_eq!(hash.bytes.len(), 32);
        assert!(hash.verify(data));
    }

    #[test]
    fn test_blake3() {
        let data = b"hello";
        let hash = ContentHash::compute(data, HashAlgorithm::Blake3);
        assert_eq!(hash.algorithm, HashAlgorithm::Blake3);
        assert_eq!(hash.bytes.len(), 32);
        assert!(hash.verify(data));
    }

    #[test]
    fn test_hex_roundtrip() {
        let data = b"test data";
        let hash = ContentHash::compute_default(data);
        let hex = hash.to_hex();
        let restored = ContentHash::from_hex(HashAlgorithm::Blake3, &hex).unwrap();
        assert_eq!(hash.bytes, restored.bytes);
    }

    #[test]
    fn test_prefixed_hex() {
        let data = b"test";
        let hash = ContentHash::compute(data, HashAlgorithm::Sha256);
        let prefixed = hash.to_prefixed_hex();
        assert!(prefixed.starts_with("sha256:"));

        let restored = ContentHash::from_prefixed_hex(&prefixed).unwrap();
        assert_eq!(hash, restored);
    }

    #[test]
    fn test_verify_fails_on_wrong_data() {
        let hash = ContentHash::compute(b"correct", HashAlgorithm::Blake3);
        assert!(!hash.verify(b"wrong"));
    }
}
