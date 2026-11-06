#![no_main]
use httpora_core::{CircuitBreaker, RateLimiter, RetryLayer};
use libfuzzer_sys::fuzz_target;
use std::time::Duration;

fuzz_target!(|data: &[u8]| {
    // Fuzz RateLimiter construction: first 8 bytes = capacity, next 8 = rate bits
    if data.len() >= 16 {
        let bytes: [u8; 8] = data[..8].try_into().expect("len checked");
        let capacity = u64::from_be_bytes(bytes);
        let bytes: [u8; 8] = data[8..16].try_into().expect("len checked");
        let rate = f64::from_bits(u64::from_be_bytes(bytes));
        let _ = RateLimiter::token_bucket(capacity, rate);
    }

    // Fuzz RetryLayer construction: first 4 bytes = retries, next 8 = delay
    if data.len() >= 12 {
        let bytes: [u8; 4] = data[..4].try_into().expect("len checked");
        let max_retries = u32::from_be_bytes(bytes) as usize;
        let bytes: [u8; 8] = data[4..12].try_into().expect("len checked");
        let delay_ms = u64::from_be_bytes(bytes);
        let _ = RetryLayer::new(max_retries, Duration::from_millis(delay_ms));
    }

    // Fuzz CircuitBreaker construction: first 8 bytes = threshold bits, next 8 = timeout
    if data.len() >= 16 {
        let bytes: [u8; 8] = data[..8].try_into().expect("len checked");
        let threshold = f64::from_bits(u64::from_be_bytes(bytes));
        let bytes: [u8; 8] = data[8..16].try_into().expect("len checked");
        let timeout_secs = u64::from_be_bytes(bytes);
        let _ = CircuitBreaker::new(threshold, Duration::from_secs(timeout_secs));
    }
});
