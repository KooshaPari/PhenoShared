//! # Phenotype Crypto
//!
//! Comprehensive cryptographic utilities including hashing (SHA-256, Blake3),
//! symmetric encryption (AES-GCM), key derivation (PBKDF2),
//! HMAC signatures, and secure random generation.
//!
//! # FR Traceability
//! - FR-PHENO-CRYPTO-001: SHA-256 hashing functionality
//! - FR-PHENO-CRYPTO-002: Blake3 hashing functionality
//! - FR-PHENO-CRYPTO-003: HMAC signature computation and verification
//! - FR-PHENO-CRYPTO-004: Secure nonce generation
//! - FR-PHENO-CRYPTO-005: SecureRandom trait for randomness abstraction

pub mod hash;
pub mod kdf;
pub mod key;
pub mod random;
pub mod signing;

pub use hash::{blake3_hash, content_id, hash_blake3, hash_sha256, sha256_hash, HashAlgorithm};
pub use kdf::Pbkdf2Kdf;
pub use key::{KeyError, KeyPair, PublicKey};
pub use random::{generate_random_bytes, DefaultSecureRandom, RandomError, SecureRandom};
pub use signing::{
    compute_hmac, compute_hmac_hex, verify_hmac, verify_hmac_hex, Ed25519Signer, Ed25519Verifier,
    SignatureBundle, Signer, SigningError, Verifier, HMAC_SIZE,
};
