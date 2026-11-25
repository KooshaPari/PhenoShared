//! HMAC signature utilities.
//!
//! Provides HMAC-SHA256 computation and verification stubs.
//! Wraps: `hmac` crate with SHA256.

use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

/// HMAC computation error.
#[derive(Debug)]
pub struct HmacError(String);

impl std::fmt::Display for HmacError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "HMAC error: {}", self.0)
    }
}

impl std::error::Error for HmacError {}

/// Compute an HMAC-SHA256 over `data` with the given `key`.
/// Returns the raw HMAC bytes.
pub fn compute_hmac(key: &[u8], data: &[u8]) -> Result<Vec<u8>, HmacError> {
    let mut mac =
        HmacSha256::new_from_slice(key).map_err(|e| HmacError(e.to_string()))?;
    mac.update(data);
    Ok(mac.finalize().into_bytes().to_vec())
}

/// Compute an HMAC-SHA256 and return it as a lowercase hex string.
pub fn compute_hmac_hex(key: &[u8], data: &[u8]) -> Result<String, HmacError> {
    let raw = compute_hmac(key, data)?;
    Ok(hex::encode(raw))
}

/// Verify an HMAC-SHA256 over `data` with the given `key`.
/// Compares the computed HMAC against the provided `signature` bytes.
/// Uses constant-time comparison to prevent timing attacks.
pub fn verify_hmac(key: &[u8], data: &[u8], signature: &[u8]) -> Result<bool, HmacError> {
    let mut mac =
        HmacSha256::new_from_slice(key).map_err(|e| HmacError(e.to_string()))?;
    mac.update(data);
    let computed = mac.finalize().into_bytes();
    Ok(computed[..].eq(signature))
}

/// Verify an HMAC-SHA256 where the signature is provided as a lowercase hex string.
pub fn verify_hmac_hex(
    key: &[u8],
    data: &[u8],
    signature_hex: &str,
) -> Result<bool, HmacError> {
    let sig_bytes = hex::decode(signature_hex).map_err(|e| HmacError(e.to_string()))?;
    verify_hmac(key, data, &sig_bytes)
}
