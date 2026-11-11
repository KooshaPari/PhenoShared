#![no_main]
use libfuzzer_sys::fuzz_target;

use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct FuzzClaims {
    sub: String,
    exp: u64,
}

// Fuzz the JWT decoding path: arbitrary bytes fed as a "token" must never panic.
// Expected outcomes are Err(_) variants — never a panic or UB.
fuzz_target!(|data: &[u8]| {
    // Attempt header parsing — must not panic on arbitrary input.
    let s = match std::str::from_utf8(data) {
        Ok(s) => s,
        Err(_) => return, // non-UTF8 is rejected before JWT logic
    };

    let _ = decode_header(s);

    // Attempt full decode with a fixed HMAC key and permissive validation.
    let key = DecodingKey::from_secret(b"fuzz-seed-key-authvault");
    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = false;
    validation.required_spec_claims = std::collections::HashSet::new();

    let _ = decode::<FuzzClaims>(s, &key, &validation);
});
