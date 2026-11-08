//! Key derivation utilities.
//!
//! Provides PBKDF2 salt generation stubs.
//! Wraps: `pbkdf2` crate.

use pbkdf2::pbkdf2_hmac_array;
use rand::RngCore;
use sha2::Sha256;

/// Number of PBKDF2 iterations (OWASP recommendation as of 2023).
pub const PBKDF2_ITERATIONS: u32 = 600_000;

/// Key length for PBKDF2-HMAC-SHA256 derived keys (32 bytes).
pub const PBKDF2_KEY_LEN: usize = 32;

/// Marker type for PBKDF2-HMAC-SHA256 key derivation.
pub struct Pbkdf2Kdf;

impl Pbkdf2Kdf {
    /// Derive a key from a password using PBKDF2-HMAC-SHA256.
    ///
    /// # Arguments
    /// * `password` — the secret password
    /// * `salt` — a random salt (at least 16 bytes recommended)
    ///
    /// # Returns
    /// A 32-byte derived key.
    pub fn derive(password: &str, salt: &[u8]) -> [u8; PBKDF2_KEY_LEN] {
        pbkdf2_hmac_array::<Sha256, PBKDF2_KEY_LEN>(password.as_bytes(), salt, PBKDF2_ITERATIONS)
    }
}

/// Generate a cryptographically random salt (16 bytes) as a `Vec<u8>`.
pub fn generate_salt() -> Vec<u8> {
    let mut salt = vec![0u8; 16];
    rand::thread_rng().fill_bytes(&mut salt);
    salt
}

/// Generate a cryptographically random salt and return it as a lowercase hex string.
pub fn generate_salt_hex() -> String {
    hex::encode(generate_salt())
}
