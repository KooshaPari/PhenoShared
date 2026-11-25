//! Core Cryptographic Primitives
//!
//! Error types and shared aliases used across the cipher crate.

pub mod encryption;
pub mod hashing;
pub mod signatures;

pub use encryption::CipherError;
pub use encryption::CipherResult;

/// Symmetric secret key bytes (AES-256 / ChaCha20 use 32-byte keys).
pub type Key = Vec<u8>;

/// Per-message nonce bytes.
pub type Nonce = Vec<u8>;
