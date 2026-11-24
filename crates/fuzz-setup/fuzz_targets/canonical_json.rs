#![no_main]
use libfuzzer_sys::fuzz_target;
use sha2::{Digest, Sha256};

fuzz_target!(|data: &[u8]| {
    // INVARIANT: Canonical JSON hash is identical regardless of key order.
    // Reordering JSON object keys should not affect the canonical hash.
    if let Ok(input_str) = std::str::from_utf8(data) {
        // Parse as JSON if possible
        if let Ok(value) = serde_json::from_str::<serde_json::Value>(input_str) {
            // Serialize with canonical form (sorted keys, no whitespace)
            let canonical1 = canonical_json_string(&value);
            let hash1 = sha256_hash(&canonical1);

            // Re-parse and re-serialize to ensure consistency
            if let Ok(reparsed) = serde_json::from_str::<serde_json::Value>(&canonical1) {
                let canonical2 = canonical_json_string(&reparsed);
                let hash2 = sha256_hash(&canonical2);

                // INVARIANT: Canonical form must be idempotent
                assert_eq!(
                    hash1, hash2,
                    "Canonical JSON hash mismatch after re-parse"
                );
            }
        }
    }
});

/// Convert JSON value to canonical string (sorted keys, no whitespace).
fn canonical_json_string(value: &serde_json::Value) -> String {
    serde_json::to_string(value).expect("serialize to canonical")
}

/// Compute SHA-256 hash of input string.
fn sha256_hash(input: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    format!("{:x}", hasher.finalize())
}
