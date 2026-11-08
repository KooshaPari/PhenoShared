//! AES-GCM symmetric encryption utilities.
//!
//! Provides encrypt/decrypt stubs for AES-256-GCM.
//! Wraps: `aes-gcm` crate.

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CryptoError {
    #[error("encryption error: {0}")]
    Encryption(String),

    #[error("decryption error: {0}")]
    Decryption(String),

    #[error("invalid key length: expected 32 bytes, got {0}")]
    InvalidKeyLength(usize),

    #[error("invalid nonce length: expected 12 bytes, got {0}")]
    InvalidNonceLength(usize),

    #[error("hex decode error: {0}")]
    HexDecode(String),
}

/// Encrypt `plaintext` using AES-256-GCM with the given 32-byte key.
/// Returns ciphertext as raw bytes (nonce prepended).
pub fn encrypt_aes_gcm(key: &[u8], plaintext: &[u8]) -> Result<Vec<u8>, CryptoError> {
    if key.len() != 32 {
        return Err(CryptoError::InvalidKeyLength(key.len()));
    }
    let cipher =
        Aes256Gcm::new_from_slice(key).map_err(|e| CryptoError::Encryption(e.to_string()))?;
    let nonce_bytes = rand::random::<[u8; 12]>();
    let nonce = Nonce::from_slice(&nonce_bytes);
    let mut ciphertext = nonce_bytes.to_vec();
    let encrypted = cipher
        .encrypt(nonce, plaintext)
        .map_err(|e| CryptoError::Encryption(e.to_string()))?;
    ciphertext.extend(encrypted);
    Ok(ciphertext)
}

/// Decrypt `ciphertext` (nonce prepended) using AES-256-GCM with the given 32-byte key.
pub fn decrypt_aes_gcm(key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>, CryptoError> {
    if key.len() != 32 {
        return Err(CryptoError::InvalidKeyLength(key.len()));
    }
    if ciphertext.len() < 12 {
        return Err(CryptoError::Decryption("ciphertext too short".into()));
    }
    let cipher =
        Aes256Gcm::new_from_slice(key).map_err(|e| CryptoError::Encryption(e.to_string()))?;
    let nonce = Nonce::from_slice(&ciphertext[..12]);
    let decrypted = cipher
        .decrypt(nonce, &ciphertext[12..])
        .map_err(|e| CryptoError::Decryption(e.to_string()))?;
    Ok(decrypted)
}

/// Encrypt and return ciphertext as a lowercase hex string (nonce || ciphertext).
pub fn encrypt_aes_gcm_hex(key: &[u8], plaintext: &[u8]) -> Result<String, CryptoError> {
    let ct = encrypt_aes_gcm(key, plaintext)?;
    Ok(hex::encode(ct))
}

/// Decrypt ciphertext from a lowercase hex string (nonce || ciphertext).
pub fn decrypt_aes_gcm_hex(key: &[u8], ciphertext_hex: &str) -> Result<Vec<u8>, CryptoError> {
    let ct = hex::decode(ciphertext_hex).map_err(|e| CryptoError::HexDecode(e.to_string()))?;
    decrypt_aes_gcm(key, &ct)
}
