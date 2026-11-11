//! Soft envelope-encryption stub (C02 L22).
//!
//! Phase-0 **non-production** helpers. Format: `v1:<nonce_hex>:<ciphertext_hex>`
//! with a SHA-256 keystream (not AES-GCM). Keys come from `SL_ENVELOPE_KEY`
//! (32-byte hex). This is **not** a KMS, sealed-secret client, or at-rest store
//! integration — see `docs/ops/crypto-inventory.md`.
//!
//! A future `envelope-crypto` revision may swap the keystream for AES-GCM
//! behind a Cargo feature once the dep graph is accepted.

use sha2::{Digest, Sha256};
use thiserror::Error;

/// Env var for the soft 32-byte hex DEK (test / operator experiments only).
pub const ENVELOPE_KEY_ENV: &str = "SL_ENVELOPE_KEY";

/// Errors from the soft envelope helpers.
#[derive(Debug, Error)]
pub enum EnvelopeError {
    /// Missing or invalid `SL_ENVELOPE_KEY` (must be 64 hex chars → 32 bytes).
    #[error("SL_ENVELOPE_KEY must be 64 hex characters (32 bytes); {0}")]
    BadKey(&'static str),
    /// Encryption / decryption failure.
    #[error("envelope crypto failed: {0}")]
    Crypto(String),
}

/// Encrypt `plaintext` with the soft SHA-256 keystream under `SL_ENVELOPE_KEY`.
///
/// Output format (UTF-8 string): `v1:<nonce_hex>:<ciphertext_hex>`.
///
/// # Errors
///
/// Returns [`EnvelopeError::BadKey`] when `SL_ENVELOPE_KEY` is missing or not
/// 32 decoded bytes, or [`EnvelopeError::Crypto`] on encoding failures.
pub fn seal(plaintext: &[u8]) -> Result<String, EnvelopeError> {
    let key = load_key()?;
    let mut nonce = [0_u8; 16];
    // Deterministic-enough soft nonce for tests: hash(key || plaintext || len).
    // Operators wanting uniqueness should prefer a future AES-GCM revision.
    let mut h = Sha256::new();
    h.update(key);
    h.update(plaintext);
    h.update((plaintext.len() as u64).to_le_bytes());
    let digest = h.finalize();
    nonce.copy_from_slice(&digest[..16]);
    let ct = xor_keystream(&key, &nonce, plaintext);
    Ok(format!("v1:{}:{}", hex_encode(&nonce), hex_encode(&ct)))
}

/// Decrypt a `v1:…` blob produced by [`seal`].
///
/// # Errors
///
/// Returns [`EnvelopeError::BadKey`] when `SL_ENVELOPE_KEY` is missing or invalid,
/// or [`EnvelopeError::Crypto`] when the blob is malformed or undecodable.
pub fn open(blob: &str) -> Result<Vec<u8>, EnvelopeError> {
    let key = load_key()?;
    let parts: Vec<&str> = blob.split(':').collect();
    if parts.len() != 3 || parts[0] != "v1" {
        return Err(EnvelopeError::Crypto(
            "blob must look like v1:<nonce_hex>:<ciphertext_hex>".into(),
        ));
    }
    let nonce = hex_decode(parts[1])?;
    if nonce.len() != 16 {
        return Err(EnvelopeError::Crypto("nonce must be 16 bytes".into()));
    }
    let ciphertext = hex_decode(parts[2])?;
    Ok(xor_keystream(&key, &nonce, &ciphertext))
}

fn load_key() -> Result<[u8; 32], EnvelopeError> {
    let raw = std::env::var(ENVELOPE_KEY_ENV)
        .map_err(|_| EnvelopeError::BadKey("environment variable is unset"))?;
    let bytes = hex_decode(raw.trim())?;
    if bytes.len() != 32 {
        return Err(EnvelopeError::BadKey("decoded length must be 32 bytes"));
    }
    let mut key = [0_u8; 32];
    key.copy_from_slice(&bytes);
    Ok(key)
}

fn xor_keystream(key: &[u8; 32], nonce: &[u8], data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    let mut counter = 0_u64;
    let mut offset = 0_usize;
    while offset < data.len() {
        let mut h = Sha256::new();
        h.update(key);
        h.update(nonce);
        h.update(counter.to_le_bytes());
        let block = h.finalize();
        let take = (data.len() - offset).min(block.len());
        for i in 0..take {
            out.push(data[offset + i] ^ block[i]);
        }
        offset += take;
        counter = counter.wrapping_add(1);
    }
    out
}

fn hex_encode(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push(HEX[(b >> 4) as usize] as char);
        s.push(HEX[(b & 0xf) as usize] as char);
    }
    s
}

fn hex_decode(s: &str) -> Result<Vec<u8>, EnvelopeError> {
    let s = s.as_bytes();
    if s.len() % 2 != 0 {
        return Err(EnvelopeError::Crypto("odd hex length".into()));
    }
    let mut out = Vec::with_capacity(s.len() / 2);
    let mut i = 0;
    while i < s.len() {
        let hi = from_hex(s[i])?;
        let lo = from_hex(s[i + 1])?;
        out.push((hi << 4) | lo);
        i += 2;
    }
    Ok(out)
}

fn from_hex(c: u8) -> Result<u8, EnvelopeError> {
    match c {
        b'0'..=b'9' => Ok(c - b'0'),
        b'a'..=b'f' => Ok(c - b'a' + 10),
        b'A'..=b'F' => Ok(c - b'A' + 10),
        _ => Err(EnvelopeError::Crypto("invalid hex digit".into())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_and_bad_key_errors() {
        // 32 zero bytes — test-only; never a production secret.
        std::env::set_var(
            ENVELOPE_KEY_ENV,
            "0000000000000000000000000000000000000000000000000000000000000000",
        );
        let blob = seal(b"hello envelope").expect("seal");
        assert!(blob.starts_with("v1:"));
        let plain = open(&blob).expect("open");
        assert_eq!(plain, b"hello envelope");

        std::env::set_var(ENVELOPE_KEY_ENV, "deadbeef");
        let err = seal(b"x").expect_err("must fail on short key");
        assert!(matches!(err, EnvelopeError::BadKey(_)));
    }
}
