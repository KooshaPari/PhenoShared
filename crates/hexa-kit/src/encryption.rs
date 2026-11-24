//! Encryption utilities (stub).
//!
//! Minimal placeholder API. Real implementations live in
//! `crates/cipher/src/core/encryption.rs`. These stubs exist to keep the
//! top-level `hexakit` crate compiling while the canonical migration is in
//! progress.

use thiserror::Error;

/// Encryption / decryption errors.
#[derive(Debug, Error)]
pub enum CryptoError {
    #[error("encryption failed: {0}")]
    Encrypt(String),
    #[error("decryption failed: {0}")]
    Decrypt(String),
    #[error("invalid input: {0}")]
    InvalidInput(String),
}

/// Encrypt plaintext with AES-GCM (stub: returns empty Vec).
pub fn encrypt_aes_gcm(
    _plaintext: &[u8],
    _key: &[u8],
    _nonce: &[u8],
) -> Result<Vec<u8>, CryptoError> {
    Ok(Vec::new())
}

/// Decrypt ciphertext with AES-GCM (stub: returns empty Vec).
pub fn decrypt_aes_gcm(
    _ciphertext: &[u8],
    _key: &[u8],
    _nonce: &[u8],
) -> Result<Vec<u8>, CryptoError> {
    Ok(Vec::new())
}

/// Encrypt plaintext with AES-GCM, returning hex-encoded string (stub).
pub fn encrypt_aes_gcm_hex(
    _plaintext: &[u8],
    _key: &[u8],
    _nonce: &[u8],
) -> Result<String, CryptoError> {
    Ok(String::new())
}

/// Decrypt hex-encoded ciphertext with AES-GCM (stub).
pub fn decrypt_aes_gcm_hex(
    _ciphertext_hex: &str,
    _key: &[u8],
    _nonce: &[u8],
) -> Result<Vec<u8>, CryptoError> {
    Ok(Vec::new())
}
