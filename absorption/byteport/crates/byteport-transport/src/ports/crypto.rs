//! Lightweight symmetric encryption — XOR-based encrypt / decrypt helpers.
//!
//! The `AesKey` wrapper holds a 32-byte key (AES-256 size) but the actual
//! transform is a simple byte-wise XOR.  This keeps the dependency tree
//! zero while still giving the crate a realistic crypto-shaped surface for
//! testing and downstream mocking.

use thiserror::Error;

/// A 32-byte symmetric key.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AesKey {
    key: [u8; 32],
}

impl AesKey {
    /// Build a key from a caller-supplied 32-byte slice.
    pub fn new(key: [u8; 32]) -> Self {
        Self { key }
    }

    /// Return a reference to the raw key bytes.
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.key
    }
}

/// Errors produced by crypto operations.
#[derive(Debug, Clone, PartialEq, Eq, Error)]
pub enum CryptoError {
    #[error("input is empty")]
    EmptyInput,
    #[error("a key is required")]
    KeyRequired,
}

/// XOR-encrypt `plaintext` by cycling through the 32-byte key.
pub fn encrypt(plaintext: &[u8], key: &AesKey) -> Vec<u8> {
    plaintext.iter().enumerate().map(|(i, b)| b ^ key.key[i % 32]).collect()
}

/// XOR-decrypt `ciphertext` — identical to [`encrypt`] because XOR is
/// self-inverse.
pub fn decrypt(ciphertext: &[u8], key: &AesKey) -> Vec<u8> {
    encrypt(ciphertext, key)
}

/// XOR-encrypt with a combined key + nonce stream.  Each byte is XOR-ed
/// with `(key[i] ^ nonce[i % nonce_len])`.
pub fn encrypt_with_nonce(plaintext: &[u8], key: &AesKey, nonce: &[u8]) -> Vec<u8> {
    if nonce.is_empty() {
        return encrypt(plaintext, key);
    }
    plaintext
        .iter()
        .enumerate()
        .map(|(i, b)| b ^ key.key[i % 32] ^ nonce[i % nonce.len()])
        .collect()
}

/// XOR-decrypt with nonce — reverse of [`encrypt_with_nonce`].
pub fn decrypt_with_nonce(ciphertext: &[u8], key: &AesKey, nonce: &[u8]) -> Vec<u8> {
    encrypt_with_nonce(ciphertext, key, nonce)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_key() -> AesKey {
        AesKey::new([
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12,
            0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20,
        ])
    }

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = sample_key();
        let plaintext = b"Hello, BytePort!";
        let ciphertext = encrypt(plaintext, &key);
        let recovered = decrypt(&ciphertext, &key);
        assert_eq!(recovered, plaintext);
    }

    #[test]
    fn test_encrypt_produces_different_output() {
        let key = sample_key();
        let plaintext = b"non-empty data for comparison";
        let ciphertext = encrypt(plaintext, &key);
        assert_ne!(ciphertext, plaintext);
    }

    #[test]
    fn test_decrypt_empty_input() {
        let key = sample_key();
        let result = decrypt(&[], &key);
        assert!(result.is_empty());
    }

    #[test]
    fn test_encrypt_decrypt_with_nonce_roundtrip() {
        let key = sample_key();
        let nonce = b"unique-nonce-123";
        let plaintext = b"nonce-protected payload";
        let ciphertext = encrypt_with_nonce(plaintext, &key, nonce);
        let recovered = decrypt_with_nonce(&ciphertext, &key, nonce);
        assert_eq!(recovered, plaintext);
    }
}
