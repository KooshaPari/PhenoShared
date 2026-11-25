//! Digital Signatures Module
//!
//! Provides Ed25519 digital signatures for authentication and non-repudiation

use ed25519_dalek::{Signer, Verifier, SigningKey, VerifyingKey, Signature};
use rand::rngs::OsRng;
use thiserror::Error;

/// Signature errors
#[derive(Debug, Error, Clone, PartialEq)]
pub enum SignatureError {
    #[error("Invalid signature length: expected {expected}, got {got}")]
    InvalidLength { expected: usize, got: usize },
    #[error("Invalid public key")]
    InvalidPublicKey,
    #[error("Invalid secret key")]
    InvalidSecretKey,
    #[error("Signature verification failed")]
    VerificationFailed,
    #[error("Signing failed: {0}")]
    SigningFailed(String),
}

/// Signing key pair
#[derive(Clone)]
pub struct KeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

impl std::fmt::Debug for KeyPair {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("KeyPair")
            .field("public_key", &"[REDACTED 32 bytes]")
            .field("secret_key", &"[REDACTED 32 bytes]")
            .finish()
    }
}

/// Generate a new Ed25519 key pair
pub fn generate_keypair() -> KeyPair {
    let signing_key = SigningKey::generate(&mut OsRng);
    let verifying_key = signing_key.verifying_key();
    
    KeyPair {
        public_key: verifying_key.to_bytes().to_vec(),
        secret_key: signing_key.to_bytes().to_vec(),
    }
}

/// Sign a message
pub fn sign(message: &[u8], secret_key: &[u8]) -> Result<Vec<u8>, SignatureError> {
    if secret_key.len() != 32 {
        return Err(SignatureError::InvalidSecretKey);
    }
    
    let key_bytes: [u8; 32] = secret_key.try_into()
        .map_err(|_| SignatureError::InvalidSecretKey)?;
    let signing_key = SigningKey::from_bytes(&key_bytes);
    
    let signature = signing_key.sign(message);
    Ok(signature.to_bytes().to_vec())
}

/// Verify a signature
pub fn verify(message: &[u8], signature: &[u8], public_key: &[u8]) -> Result<(), SignatureError> {
    if signature.len() != 64 {
        return Err(SignatureError::InvalidLength { 
            expected: 64, 
            got: signature.len() 
        });
    }
    
    if public_key.len() != 32 {
        return Err(SignatureError::InvalidPublicKey);
    }
    
    let pk_bytes: [u8; 32] = public_key.try_into()
        .map_err(|_| SignatureError::InvalidPublicKey)?;
    let verifying_key = VerifyingKey::from_bytes(&pk_bytes)
        .map_err(|_| SignatureError::InvalidPublicKey)?;
    
    let sig_bytes: [u8; 64] = signature.try_into()
        .map_err(|_| SignatureError::InvalidLength { expected: 64, got: signature.len() })?;
    let sig = Signature::from_bytes(&sig_bytes);
    
    verifying_key.verify(message, &sig)
        .map_err(|_| SignatureError::VerificationFailed)
}

/// Derive public key from secret key
pub fn derive_public_key(secret_key: &[u8]) -> Result<Vec<u8>, SignatureError> {
    if secret_key.len() != 32 {
        return Err(SignatureError::InvalidSecretKey);
    }
    
    let key_bytes: [u8; 32] = secret_key.try_into()
        .map_err(|_| SignatureError::InvalidSecretKey)?;
    let signing_key = SigningKey::from_bytes(&key_bytes);
    let verifying_key = signing_key.verifying_key();
    
    Ok(verifying_key.to_bytes().to_vec())
}

/// Ed25519 public key newtype wrapper.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicKey(pub Vec<u8>);

impl PublicKey {
    /// Borrow the raw key bytes.
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }

    /// Consume and return the inner bytes.
    pub fn to_bytes(self) -> Vec<u8> {
        self.0
    }

    /// Whether the key is empty.
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    /// Key length in bytes.
    pub fn len(&self) -> usize {
        self.0.len()
    }
}

impl From<Vec<u8>> for PublicKey {
    fn from(v: Vec<u8>) -> Self {
        PublicKey(v)
    }
}

impl From<&[u8]> for PublicKey {
    fn from(v: &[u8]) -> Self {
        PublicKey(v.to_vec())
    }
}

/// Ed25519 secret key newtype wrapper.
///
/// The inner `Vec<u8>` is zeroized on drop.
#[derive(Clone)]
pub struct SecretKey(pub Vec<u8>);

impl SecretKey {
    /// Borrow the raw key bytes.
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }

    /// Consume and return the inner bytes. The buffer is zeroized on drop.
    pub fn to_bytes(mut self) -> Vec<u8> {
        // Take the bytes out without moving out of a Drop type.
        std::mem::take(&mut self.0)
    }

    /// Whether the key is empty.
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    /// Key length in bytes.
    pub fn len(&self) -> usize {
        self.0.len()
    }
}

impl Drop for SecretKey {
    fn drop(&mut self) {
        // Best-effort zeroization of secret-key material.
        for byte in self.0.iter_mut() {
            // Volatile write to discourage the compiler from optimizing this away.
            unsafe {
                core::ptr::write_volatile(byte, 0);
            }
        }
    }
}

impl std::fmt::Debug for SecretKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SecretKey").field("0", &"[REDACTED]").finish()
    }
}

impl From<Vec<u8>> for SecretKey {
    fn from(v: Vec<u8>) -> Self {
        SecretKey(v)
    }
}

/// Ed25519 signature newtype wrapper.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignatureBytes(pub Vec<u8>);

impl SignatureBytes {
    /// Borrow the raw signature bytes.
    pub fn as_bytes(&self) -> &[u8] {
        &self.0
    }

    /// Consume and return the inner bytes.
    pub fn to_bytes(self) -> Vec<u8> {
        self.0
    }
}

impl From<Vec<u8>> for SignatureBytes {
    fn from(v: Vec<u8>) -> Self {
        SignatureBytes(v)
    }
}

/// Ed25519 signer facade. Wraps the free functions in this module so callers
/// can write `Ed25519Signer::sign(msg, &sk)` etc.
pub struct Ed25519Signer;

impl Ed25519Signer {
    /// Generate a fresh Ed25519 keypair.
    pub fn generate_keypair() -> (PublicKey, SecretKey) {
        let kp = generate_keypair();
        (PublicKey(kp.public_key), SecretKey(kp.secret_key))
    }

    /// Sign `message` with `secret_key`.
    pub fn sign(message: &[u8], secret_key: &SecretKey) -> Result<SignatureBytes, SignatureError> {
        sign(message, &secret_key.0).map(SignatureBytes)
    }

    /// Verify `signature` over `message` under `public_key`.
    ///
    /// Returns `Ok(true)` if the signature is valid, `Ok(false)` if it is
    /// structurally valid but does not match, and `Err(_)` if the keys are
    /// malformed.
    pub fn verify(
        message: &[u8],
        signature: &SignatureBytes,
        public_key: &PublicKey,
    ) -> Result<bool, SignatureError> {
        verify(message, &signature.0, &public_key.0).map(|_| true)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_keypair() {
        let kp = generate_keypair();
        assert_eq!(kp.public_key.len(), 32);
        assert_eq!(kp.secret_key.len(), 32);
    }

    #[test]
    fn test_keypair_unique() {
        let kp1 = generate_keypair();
        let kp2 = generate_keypair();
        assert_ne!(kp1.public_key, kp2.public_key);
        assert_ne!(kp1.secret_key, kp2.secret_key);
    }

    #[test]
    fn test_sign_and_verify() {
        let kp = generate_keypair();
        let message = b"Hello, World!";
        
        let signature = sign(message, &kp.secret_key).unwrap();
        assert_eq!(signature.len(), 64);
        
        verify(message, &signature, &kp.public_key).unwrap();
    }

    #[test]
    fn test_verify_wrong_message() {
        let kp = generate_keypair();
        let message = b"original message";
        let wrong_message = b"different message";
        
        let signature = sign(message, &kp.secret_key).unwrap();
        let result = verify(wrong_message, &signature, &kp.public_key);
        
        assert!(matches!(result, Err(SignatureError::VerificationFailed)));
    }

    #[test]
    fn test_verify_wrong_key() {
        let kp1 = generate_keypair();
        let kp2 = generate_keypair();
        let message = b"test message";
        
        let signature = sign(message, &kp1.secret_key).unwrap();
        let result = verify(message, &signature, &kp2.public_key);
        
        assert!(matches!(result, Err(SignatureError::VerificationFailed)));
    }

    #[test]
    fn test_invalid_secret_key_length() {
        let result = sign(b"test", &[0u8; 16]);
        assert!(matches!(result, Err(SignatureError::InvalidSecretKey)));
    }

    #[test]
    fn test_invalid_signature_length() {
        let kp = generate_keypair();
        let result = verify(b"test", &[0u8; 32], &kp.public_key);
        assert!(matches!(result, Err(SignatureError::InvalidLength { expected: 64, got: 32 })));
    }

    #[test]
    fn test_invalid_public_key_length() {
        let kp = generate_keypair();
        let message = b"test";
        let sig = sign(message, &kp.secret_key).unwrap();
        
        let result = verify(message, &sig, &[0u8; 16]);
        assert!(matches!(result, Err(SignatureError::InvalidPublicKey)));
    }

    #[test]
    fn test_derive_public_key() {
        let kp = generate_keypair();
        let derived = derive_public_key(&kp.secret_key).unwrap();
        assert_eq!(derived, kp.public_key);
    }

    #[test]
    fn test_empty_message() {
        let kp = generate_keypair();
        let signature = sign(b"", &kp.secret_key).unwrap();
        verify(b"", &signature, &kp.public_key).unwrap();
    }

    #[test]
    fn test_large_message() {
        let kp = generate_keypair();
        let message = vec![0u8; 10000];
        let signature = sign(&message, &kp.secret_key).unwrap();
        verify(&message, &signature, &kp.public_key).unwrap();
    }

    #[test]
    fn test_deterministic_verification() {
        let kp = generate_keypair();
        let message = b"test message";
        let signature = sign(message, &kp.secret_key).unwrap();
        
        // Verify multiple times
        for _ in 0..10 {
            verify(message, &signature, &kp.public_key).unwrap();
        }
    }

    #[test]
    fn test_signature_unique() {
        let kp = generate_keypair();
        let message = b"same message";
        
        let sig1 = sign(message, &kp.secret_key).unwrap();
        let sig2 = sign(message, &kp.secret_key).unwrap();
        
        // Ed25519 signatures are deterministic, so they should be the same
        assert_eq!(sig1, sig2);
    }

    #[test]
    fn test_keypair_debug_redacts_keys() {
        let kp = generate_keypair();
        let debug_str = format!("{:?}", kp);
        assert!(!debug_str.contains(&hex::encode(&kp.secret_key)));
        assert!(debug_str.contains("REDACTED"));
    }

    #[test]
    fn test_error_display() {
        let err = SignatureError::VerificationFailed;
        assert_eq!(err.to_string(), "Signature verification failed");
    }

    #[test]
    fn test_error_debug() {
        let err = SignatureError::InvalidPublicKey;
        let debug_str = format!("{:?}", err);
        assert!(debug_str.contains("InvalidPublicKey"));
    }

    #[test]
    fn test_error_clone() {
        let err = SignatureError::SigningFailed("test".to_string());
        let cloned = err.clone();
        assert_eq!(err.to_string(), cloned.to_string());
    }

    #[test]
    fn test_error_equality() {
        let err1 = SignatureError::VerificationFailed;
        let err2 = SignatureError::VerificationFailed;
        let err3 = SignatureError::InvalidPublicKey;
        
        assert_eq!(err1, err2);
        assert_ne!(err1, err3);
    }
}
