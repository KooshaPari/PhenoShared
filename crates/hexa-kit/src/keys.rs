//! Key derivation utilities (stub).
//!
//! Minimal placeholder API. These stubs exist to keep the top-level
//! `hexakit` crate compiling while the canonical migration is in progress.

/// PBKDF2 key-derivation function (stub).
#[derive(Debug, Clone)]
pub struct Pbkdf2Kdf {
    // Stored for eventual real implementation; unused in current stub.
    #[allow(dead_code)]
    iterations: u32,
}

impl Pbkdf2Kdf {
    /// Create a new PBKDF2 KDF with the given iteration count.
    pub fn new(iterations: u32) -> Self {
        Self { iterations }
    }

    /// Derive a key from a password and salt (stub: returns empty Vec).
    pub fn derive(&self, _password: &[u8], _salt: &[u8], _output_len: usize) -> Vec<u8> {
        Vec::new()
    }
}

impl Default for Pbkdf2Kdf {
    fn default() -> Self {
        Self::new(100_000)
    }
}

/// Generate a random salt (stub: returns empty Vec).
pub fn generate_salt(len: usize) -> Vec<u8> {
    vec![0u8; len]
}

/// Generate a random salt, hex-encoded (stub: returns empty String).
pub fn generate_salt_hex(len: usize) -> String {
    "0".repeat(len * 2)
}
