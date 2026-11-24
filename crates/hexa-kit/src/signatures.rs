//! HMAC-SHA256 signature utilities.
//!
//! Provides HMAC-based message authentication using SHA-256.
//! All functions operate on raw byte slices and hex-encoded forms.

use hmac::{Hmac, Mac};
use sha2::Sha256;

/// The HMAC-SHA256 algorithm type.
type HmacSha256 = Hmac<Sha256>;

/// Compute an HMAC-SHA256 signature.
pub fn compute_hmac(key: &[u8], data: &[u8]) -> Vec<u8> {
    let mut mac = HmacSha256::new_from_slice(key).expect("HMAC accepts any key length");
    mac.update(data);
    mac.finalize().into_bytes().to_vec()
}

/// Compute an HMAC-SHA256 signature, hex-encoded.
pub fn compute_hmac_hex(key: &[u8], data: &[u8]) -> String {
    hex::encode(compute_hmac(key, data))
}

/// Verify an HMAC-SHA256 signature.
pub fn verify_hmac(key: &[u8], data: &[u8], expected: &[u8]) -> bool {
    let mut mac = match HmacSha256::new_from_slice(key) {
        Ok(m) => m,
        Err(_) => return false,
    };
    mac.update(data);
    mac.verify_slice(expected).is_ok()
}

/// Verify a hex-encoded HMAC-SHA256 signature.
pub fn verify_hmac_hex(key: &[u8], data: &[u8], expected_hex: &str) -> bool {
    let expected = match hex::decode(expected_hex) {
        Ok(v) => v,
        Err(_) => return false,
    };
    verify_hmac(key, data, &expected)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_hmac_deterministic() {
        let key = b"secret-key";
        let data = b"hello world";
        let sig1 = compute_hmac(key, data);
        let sig2 = compute_hmac(key, data);
        assert_eq!(sig1, sig2, "HMAC must be deterministic");
        assert_eq!(sig1.len(), 32, "SHA-256 HMAC is 32 bytes");
    }

    #[test]
    fn test_compute_verify_roundtrip() {
        let key = b"my-key";
        let data = b"test data";
        let sig = compute_hmac(key, data);
        assert!(
            verify_hmac(key, data, &sig),
            "verify must accept correct signature"
        );
    }

    #[test]
    fn test_verify_rejects_wrong_key() {
        let data = b"message";
        let sig = compute_hmac(b"real-key", data);
        assert!(
            !verify_hmac(b"wrong-key", data, &sig),
            "wrong key must fail"
        );
    }

    #[test]
    fn test_verify_rejects_tampered_data() {
        let key = b"key";
        let sig = compute_hmac(key, b"original");
        assert!(
            !verify_hmac(key, b"tampered", &sig),
            "tampered data must fail"
        );
    }

    #[test]
    fn test_compute_hmac_hex_length() {
        let key = b"k";
        let data = b"d";
        let hex = compute_hmac_hex(key, data);
        assert_eq!(hex.len(), 64, "SHA-256 HMAC hex is 64 chars");
    }

    #[test]
    fn test_verify_hmac_hex_roundtrip() {
        let key = b"hex-key";
        let data = b"hex-data";
        let hex_sig = compute_hmac_hex(key, data);
        assert!(verify_hmac_hex(key, data, &hex_sig));
    }

    #[test]
    fn test_verify_hmac_hex_rejects_invalid_hex() {
        let key = b"k";
        let data = b"d";
        assert!(!verify_hmac_hex(key, data, "not-hex"));
    }

    #[test]
    fn test_verify_rejects_short_expected() {
        let key = b"k";
        let data = b"d";
        assert!(!verify_hmac(key, data, b"too-short"));
    }

    #[test]
    fn test_known_vector() {
        // RFC 4231 Test Case 2
        let key = b"Jefe";
        let data = b"what do ya want for nothing?";
        let expected = "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843";
        assert_eq!(compute_hmac_hex(key, data), expected);
    }
}
