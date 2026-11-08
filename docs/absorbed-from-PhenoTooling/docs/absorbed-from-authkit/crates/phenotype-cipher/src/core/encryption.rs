//! Encryption Module
//!
//! Authenticated symmetric encryption using AES-256-GCM and ChaCha20-Poly1305.
//!
//! Both ciphers produce a [`Ciphertext`] containing the encrypted `data`
//! and a fresh `nonce`. The nonce is prepended to the ciphertext bytes
//! during decryption when needed (kept separate here so callers can
//! inspect both halves independently).

use aes_gcm::aead::{Aead, KeyInit, Payload};
use aes_gcm::{Aes256Gcm, Key as AesKey, Nonce as AesNonce};
use chacha20poly1305::{ChaCha20Poly1305, Key as ChaKey, Nonce as ChaNonce};
use rand::rngs::OsRng;
use rand::RngCore;
use thiserror::Error;

/// Errors produced by the encryption layer.
#[derive(Debug, Error)]
pub enum CipherError {
    #[error("invalid key: {0}")]
    InvalidKey(String),
    #[error("invalid nonce length: expected {expected}, got {got}")]
    InvalidNonce { expected: usize, got: usize },
    #[error("encryption failed: {0}")]
    EncryptFailed(String),
    #[error("decryption failed: {0}")]
    DecryptFailed(String),
}

/// Result alias for cipher operations.
pub type CipherResult<T> = Result<T, CipherError>;

/// Encrypted payload with its associated nonce.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ciphertext {
    /// Ciphertext + authentication tag.
    pub data: Vec<u8>,
    /// Nonce used to produce `data`. Must be supplied to `decrypt`.
    pub nonce: Vec<u8>,
}

const AES_KEY_LEN: usize = 32;
const CHACHA_KEY_LEN: usize = 32;
const AES_NONCE_LEN: usize = 12;
const CHACHA_NONCE_LEN: usize = 12;

/// AES-256-GCM authenticated encryption.
#[derive(Clone)]
pub struct AesGcmCipher {
    cipher: Aes256Gcm,
}

impl std::fmt::Debug for AesGcmCipher {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("AesGcmCipher").finish_non_exhaustive()
    }
}

impl AesGcmCipher {
    /// Generate a fresh 32-byte AES-256 key.
    ///
    /// # Examples
    ///
    /// Round-trip with a freshly generated key:
    ///
    /// ```
    /// use phenotype_cipher::AesGcmCipher;
    ///
    /// let key = AesGcmCipher::generate_key();
    /// let cipher = AesGcmCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn generate_key() -> Vec<u8> {
        let mut key = vec![0u8; AES_KEY_LEN];
        OsRng.fill_bytes(&mut key);
        key
    }

    /// Construct a cipher from a 32-byte key.
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::AesGcmCipher;
    ///
    /// let key = AesGcmCipher::generate_key();
    /// let cipher = AesGcmCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn new(key: &[u8]) -> CipherResult<Self> {
        if key.len() != AES_KEY_LEN {
            return Err(CipherError::InvalidKey(format!(
                "AES-256 requires {AES_KEY_LEN} bytes, got {}",
                key.len()
            )));
        }
        let key = AesKey::<Aes256Gcm>::from_slice(key);
        Ok(Self { cipher: Aes256Gcm::new(key) })
    }

    /// Encrypt `plaintext` with a fresh random nonce.
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::AesGcmCipher;
    ///
    /// let key = AesGcmCipher::generate_key();
    /// let cipher = AesGcmCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn encrypt(&self, plaintext: &[u8]) -> CipherResult<Ciphertext> {
        let mut nonce_bytes = [0u8; AES_NONCE_LEN];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = AesNonce::from_slice(&nonce_bytes);
        let data = self
            .cipher
            .encrypt(nonce, plaintext)
            .map_err(|e| CipherError::EncryptFailed(e.to_string()))?;
        Ok(Ciphertext { data, nonce: nonce_bytes.to_vec() })
    }

    /// Decrypt a [`Ciphertext`] produced by [`Self::encrypt`].
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::AesGcmCipher;
    ///
    /// let key = AesGcmCipher::generate_key();
    /// let cipher = AesGcmCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn decrypt(&self, ct: &Ciphertext) -> CipherResult<Vec<u8>> {
        if ct.nonce.len() != AES_NONCE_LEN {
            return Err(CipherError::InvalidNonce {
                expected: AES_NONCE_LEN,
                got: ct.nonce.len(),
            });
        }
        let nonce = AesNonce::from_slice(&ct.nonce);
        self.cipher
            .decrypt(nonce, Payload { msg: &ct.data, aad: b"" })
            .map_err(|e| CipherError::DecryptFailed(e.to_string()))
    }
}

/// ChaCha20-Poly1305 authenticated encryption.
#[derive(Clone)]
pub struct ChaChaCipher {
    cipher: ChaCha20Poly1305,
}

impl std::fmt::Debug for ChaChaCipher {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ChaChaCipher").finish_non_exhaustive()
    }
}

impl ChaChaCipher {
    /// Generate a fresh 32-byte ChaCha20 key.
    ///
    /// # Examples
    ///
    /// Round-trip with a freshly generated key:
    ///
    /// ```
    /// use phenotype_cipher::ChaChaCipher;
    ///
    /// let key = ChaChaCipher::generate_key();
    /// let cipher = ChaChaCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn generate_key() -> Vec<u8> {
        let mut key = vec![0u8; CHACHA_KEY_LEN];
        OsRng.fill_bytes(&mut key);
        key
    }

    /// Construct a cipher from a 32-byte key.
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::ChaChaCipher;
    ///
    /// let key = ChaChaCipher::generate_key();
    /// let cipher = ChaChaCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn new(key: &[u8]) -> CipherResult<Self> {
        if key.len() != CHACHA_KEY_LEN {
            return Err(CipherError::InvalidKey(format!(
                "ChaCha20 requires {CHACHA_KEY_LEN} bytes, got {}",
                key.len()
            )));
        }
        let key = ChaKey::from_slice(key);
        Ok(Self { cipher: ChaCha20Poly1305::new(key) })
    }

    /// Encrypt `plaintext` with a fresh random nonce.
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::ChaChaCipher;
    ///
    /// let key = ChaChaCipher::generate_key();
    /// let cipher = ChaChaCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn encrypt(&self, plaintext: &[u8]) -> CipherResult<Ciphertext> {
        let mut nonce_bytes = [0u8; CHACHA_NONCE_LEN];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = ChaNonce::from_slice(&nonce_bytes);
        let data = self
            .cipher
            .encrypt(nonce, plaintext)
            .map_err(|e| CipherError::EncryptFailed(e.to_string()))?;
        Ok(Ciphertext { data, nonce: nonce_bytes.to_vec() })
    }

    /// Decrypt a [`Ciphertext`] produced by [`Self::encrypt`].
    ///
    /// # Examples
    ///
    /// ```
    /// use phenotype_cipher::ChaChaCipher;
    ///
    /// let key = ChaChaCipher::generate_key();
    /// let cipher = ChaChaCipher::new(&key).unwrap();
    /// let ct = cipher.encrypt(b"hello").unwrap();
    /// assert_eq!(cipher.decrypt(&ct).unwrap(), b"hello");
    /// ```
    pub fn decrypt(&self, ct: &Ciphertext) -> CipherResult<Vec<u8>> {
        if ct.nonce.len() != CHACHA_NONCE_LEN {
            return Err(CipherError::InvalidNonce {
                expected: CHACHA_NONCE_LEN,
                got: ct.nonce.len(),
            });
        }
        let nonce = ChaNonce::from_slice(&ct.nonce);
        self.cipher
            .decrypt(nonce, Payload { msg: &ct.data, aad: b"" })
            .map_err(|e| CipherError::DecryptFailed(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aes_key_is_32_bytes() {
        assert_eq!(AesGcmCipher::generate_key().len(), 32);
    }

    #[test]
    fn chacha_key_is_32_bytes() {
        assert_eq!(ChaChaCipher::generate_key().len(), 32);
    }

    #[test]
    fn aes_rejects_wrong_key_size() {
        let err = AesGcmCipher::new(&[0u8; 16]).unwrap_err();
        assert!(matches!(err, CipherError::InvalidKey(_)));
    }

    #[test]
    fn aes_fresh_nonce_per_encryption() {
        let key = AesGcmCipher::generate_key();
        let cipher = AesGcmCipher::new(&key).unwrap();
        let a = cipher.encrypt(b"same").unwrap();
        let b = cipher.encrypt(b"same").unwrap();
        assert_ne!(a.nonce, b.nonce);
        assert_ne!(a.data, b.data);
    }

    /// Round-trip: encrypting then decrypting recovers the exact original bytes.
    #[test]
    fn encrypt_decrypt_round_trip_returns_same_bytes() {
        let key = AesGcmCipher::generate_key();
        let cipher = AesGcmCipher::new(&key).unwrap();
        let plaintext = b"the quick brown fox jumps over the lazy dog";
        let ciphertext = cipher.encrypt(plaintext).unwrap();
        let decrypted = cipher.decrypt(&ciphertext).unwrap();
        assert_eq!(plaintext.as_slice(), decrypted.as_slice());
    }
}
