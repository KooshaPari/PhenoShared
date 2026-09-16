//! PhenoCrypto - Cryptographic Utilities

use aes_gcm::{Aes256Gcm, KeyInit as AesKeyInit, Nonce, aead::Aead};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64_STANDARD};
use hmac::{Hmac, KeyInit, Mac};
use sha2::Sha256;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum CryptoError {
    #[error("encryption failed")]
    EncryptionFailed,
    #[error("decryption failed")]
    DecryptionFailed,
    #[error("invalid key")]
    InvalidKey,
}

/// AES-256-GCM encryption
pub struct AesEncryptor {
    cipher: Aes256Gcm,
}

impl AesEncryptor {
    pub fn new(key: &[u8; 32]) -> Self {
        let cipher = Aes256Gcm::new(key.into());
        Self { cipher }
    }

    pub fn encrypt(&self, plaintext: &[u8]) -> Result<Vec<u8>, CryptoError> {
        let binding: [u8; 12] = rand::random();
        let nonce = Nonce::from_slice(&binding);
        let ciphertext = self
            .cipher
            .encrypt(nonce, plaintext)
            .map_err(|_| CryptoError::EncryptionFailed)?;

        let mut result = binding.to_vec();
        result.extend(ciphertext);
        Ok(result)
    }

    pub fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>, CryptoError> {
        if data.len() < 12 {
            return Err(CryptoError::DecryptionFailed);
        }

        let nonce = Nonce::from_slice(&data[..12]);
        let ciphertext = &data[12..];

        self.cipher
            .decrypt(nonce, ciphertext)
            .map_err(|_| CryptoError::DecryptionFailed)
    }
}

/// HMAC-SHA256
pub fn hmac_sha256(key: &[u8], data: &[u8]) -> Vec<u8> {
    type HmacSha256 = Hmac<Sha256>;
    let mac = HmacSha256::new_from_slice(key).expect("HMAC key size must be valid");
    mac.chain_update(data).finalize().into_bytes().to_vec()
}

/// Secure random bytes
pub fn random_bytes(len: usize) -> Vec<u8> {
    use rand::RngExt;
    let mut bytes = vec![0u8; len];
    rand::rng().fill(&mut bytes[..]);
    bytes
}

/// Base64 encode
pub fn base64_encode(data: &[u8]) -> String {
    BASE64_STANDARD.encode(data)
}

pub fn base64_decode(data: &str) -> Result<Vec<u8>, CryptoError> {
    BASE64_STANDARD
        .decode(data)
        .map_err(|_| CryptoError::InvalidKey)
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-003
    #[test]
    fn hmac_sha256_matches_known_vector() {
        let digest = hmac_sha256(b"key", b"The quick brown fox jumps over the lazy dog");

        assert_eq!(
            digest,
            [
                0xf7, 0xbc, 0x83, 0xf4, 0x30, 0x53, 0x84, 0x24, 0xb1, 0x32, 0x98, 0xe6, 0xaa, 0x6f,
                0xb1, 0x43, 0xef, 0x4d, 0x59, 0xa1, 0x49, 0x46, 0x17, 0x59, 0x97, 0x47, 0x9d, 0xbc,
                0x2d, 0x1a, 0x3c, 0xd8,
            ]
        );
    }

    // Traces to: FR-003
    #[test]
    fn base64_decode_rejects_invalid_input() {
        assert!(matches!(
            base64_decode("not valid base64!"),
            Err(CryptoError::InvalidKey)
        ));
    }

    // Traces to: FR-003
    #[test]
    fn random_bytes_returns_requested_length() {
        assert_eq!(random_bytes(32).len(), 32);
        assert!(random_bytes(0).is_empty());
    }
}
