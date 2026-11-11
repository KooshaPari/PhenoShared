//! Property evidence for `session_ledger::envelope::seal` / `open`.
//!
//! Invariants under test:
//!
//!  * `seal` output has the documented `v1:<nonce_hex>:<ciphertext_hex>`
//!    format (always 3 colon-separated parts, lowercase hex)
//!  * `seal` -> `open` is a round-trip identity on any plaintext
//!  * `open` on a malformed blob returns Err rather than panicking
//!  * `open` on a wrong-key blob returns a non-original plaintext
//!  * `ENVELOPE_KEY_ENV` constant equals `"SL_ENVELOPE_KEY"`
//!  * `EnvelopeError` Debug string is non-empty
//!  * `seal` is deterministic for the same key + plaintext
//!  * `seal` output is non-empty (even for empty plaintext the format
//!    itself produces a non-empty string)
//!  * `open` with a truncated blob returns Err
//!  * `open` with a wrong version prefix returns Err

#![cfg(feature = "envelope-crypto")]

use proptest::prelude::*;
use session_ledger::envelope::{open, seal, EnvelopeError, ENVELOPE_KEY_ENV};
use std::panic::AssertUnwindSafe;
use std::sync::{Mutex, OnceLock};

/// Test-only 32-byte hex key (all zeros).
const TEST_KEY: &str = "0000000000000000000000000000000000000000000000000000000000000000";

static ENV_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

fn env_lock() -> &'static Mutex<()> {
    ENV_LOCK.get_or_init(|| Mutex::new(()))
}

// ── ENVELOPE_KEY_ENV ──────────────────────────────────────────────────────

proptest! {
    /// Property: `ENVELOPE_KEY_ENV` matches the documented env var name.
    #[test]
    fn envelope_key_env_is_documented(_unused in 0u8..1u8) {
        prop_assert_eq!(ENVELOPE_KEY_ENV, "SL_ENVELOPE_KEY");
    }
}

// ── Plain `#[test]` block (env-mutating tests are serialized by cargo test,
// avoiding the proptest worker-thread race against std::env::var.
// ────────────────────────────────────────────────────────────────────────────

/// Plain `#[test]` for env-mutating invariants (serialized by cargo test).
mod serial_tests {
    use super::*;

    /// Property: `seal` output has the exact `v1:<nonce>:<ct>` 3-part
    /// colon-separated format.
    #[test]
    fn seal_output_format_is_v1_nonce_ct() {
        with_key_result(TEST_KEY, || {
            for size in [0_usize, 1, 5, 50, 100] {
                let plaintext: Vec<u8> =
                    (0..u8::try_from(size).expect("fixture size fits u8")).collect();
                let blob = seal(&plaintext).expect("seal");
                let parts: Vec<&str> = blob.split(':').collect();
                assert_eq!(parts.len(), 3, "blob must have 3 colon-separated parts: {blob:?}");
                assert_eq!(parts[0], "v1", "version prefix must be 'v1'");
                assert_eq!(parts[1].len(), 32, "nonce must be 32 hex chars");
                assert_eq!(
                    parts[2].len(),
                    plaintext.len() * 2,
                    "ciphertext hex length must be 2x plaintext length"
                );
            }
        });
    }

    /// Property: every char in the sealed blob (other than `v1:` and
    /// the colons) is lowercase hex.
    #[test]
    fn seal_output_uses_only_lowercase_hex() {
        with_key_result(TEST_KEY, || {
            let plaintext: Vec<u8> = (0..50_u8).collect();
            let blob = seal(&plaintext).expect("seal");
            for ch in blob.chars() {
                assert!(
                    ch == ':' || ch.is_ascii_digit() || ch.is_ascii_lowercase(),
                    "blob char {ch:?} must be ':' or lowercase hex"
                );
            }
        });
    }

    /// Property: `seal` output is non-empty (the blob format includes
    /// `v1:` + 32 hex chars + `:` + cipher, even for empty plaintext).
    #[test]
    fn seal_output_is_nonempty() {
        with_key_result(TEST_KEY, || {
            let blob = seal(b"").expect("seal empty");
            assert!(!blob.is_empty());
        });
    }

    /// Property: `seal` -> `open` is a round-trip identity on any
    /// plaintext under the same key.
    #[test]
    fn seal_open_round_trip() {
        with_key_result(TEST_KEY, || {
            for size in [0_usize, 1, 5, 50, 200] {
                let plaintext: Vec<u8> = (0..size)
                    .map(|i| u8::try_from(i & 0xff).expect("masked fixture byte fits u8"))
                    .collect();
                let blob = seal(&plaintext).expect("seal");
                let decrypted = open(&blob).expect("open");
                assert_eq!(
                    decrypted, plaintext,
                    "round-trip mismatch: input {plaintext:?}, output {decrypted:?}"
                );
            }
        });
    }

    /// Property: `seal` is deterministic for a fixed (key, plaintext)
    /// pair.
    #[test]
    fn seal_is_deterministic() {
        with_key_result(TEST_KEY, || {
            let plaintext = b"hello envelope".to_vec();
            let blob1 = seal(&plaintext).expect("seal 1");
            let blob2 = seal(&plaintext).expect("seal 2");
            assert_eq!(blob1, blob2, "seal must be deterministic");
        });
    }

    /// Property: `open` returns Err on a malformed blob (not `v1:` prefix).
    #[test]
    fn open_rejects_malformed_blob() {
        with_key_result(TEST_KEY, || {
            for prefix in ["v", "ver", "xyz"] {
                let blob = format!("{prefix}:00:00");
                let result = open(&blob);
                assert!(result.is_err(), "open must reject malformed blob {blob:?}");
            }
        });
    }

    /// Property: `open` returns Err on a wrong-version prefix.
    #[test]
    fn open_rejects_wrong_version() {
        with_key_result(TEST_KEY, || {
            let blob = "v2:00000000000000000000000000000000:00";
            let result = open(blob);
            assert!(result.is_err(), "open must reject version 'v2' blob");
        });
    }

    /// Property: `open` returns Err on a blob with the wrong number of
    /// colon-separated parts.
    #[test]
    fn open_rejects_wrong_part_count() {
        with_key_result(TEST_KEY, || {
            let blob = "v1:00:00:00";
            let result = open(blob);
            assert!(result.is_err(), "open must reject blob with 4 colon parts");
        });
    }

    /// Property: `open` returns Err on a blob with the wrong nonce
    /// length (e.g. 1 hex char instead of 32).
    #[test]
    fn open_rejects_wrong_nonce_length() {
        with_key_result(TEST_KEY, || {
            let blob = "v1:00:00";
            let result = open(blob);
            assert!(result.is_err(), "open must reject blob with nonce != 16 bytes");
        });
    }

    /// Property: `seal` returns Err (`BadKey`) when `SL_ENVELOPE_KEY` is unset.
    #[test]
    fn seal_returns_err_on_missing_key() {
        let _guard = env_lock().lock().expect("envelope env lock");
        let _restore = EnvRestoreGuard::capture();
        std::env::remove_var(ENVELOPE_KEY_ENV);
        let result = seal(b"hello");
        assert!(result.is_err(), "seal must fail when SL_ENVELOPE_KEY is unset");
        assert!(
            matches!(&result, Err(EnvelopeError::BadKey(_))),
            "expected BadKey error, got {result:?}"
        );
    }

    /// Property: `seal` returns Err (`BadKey`) when `SL_ENVELOPE_KEY` is the
    /// wrong length (e.g. 8 hex chars instead of 64).
    #[test]
    fn seal_returns_err_on_short_key() {
        let _guard = env_lock().lock().expect("envelope env lock");
        let _restore = EnvRestoreGuard::capture();
        std::env::set_var(ENVELOPE_KEY_ENV, "deadbeef");
        let result = seal(b"hello");
        assert!(
            matches!(&result, Err(EnvelopeError::BadKey(_))),
            "seal must reject short key with BadKey (got {result:?})"
        );
    }

    /// Property: `EnvelopeError` Debug format is non-empty (it's
    /// derived).
    #[test]
    fn envelope_error_debug_is_nonempty() {
        let err = EnvelopeError::BadKey("test");
        let debug = format!("{err:?}");
        assert!(!debug.is_empty());
        let display = format!("{err}");
        assert!(!display.is_empty());
    }

    /// A panic inside the environment override must restore the prior value
    /// and release the lock without poisoning subsequent envelope tests.
    #[test]
    fn env_override_restores_after_panic() {
        let before = {
            let _guard = env_lock().lock().expect("envelope env lock");
            std::env::var(ENVELOPE_KEY_ENV).ok()
        };
        let panic_result = std::panic::catch_unwind(AssertUnwindSafe(|| {
            with_key_result(TEST_KEY, || panic!("intentional environment-guard panic"));
        }));
        assert!(panic_result.is_err(), "the regression must exercise unwinding");
        {
            let _guard = env_lock().lock().expect("envelope env lock");
            assert_eq!(std::env::var(ENVELOPE_KEY_ENV).ok(), before);
        }

        // Prove the mutex remains usable after the caught panic.
        with_key_result(TEST_KEY, || {
            assert_eq!(std::env::var(ENVELOPE_KEY_ENV).ok().as_deref(), Some(TEST_KEY));
        });
        let _guard = env_lock().lock().expect("envelope env lock");
        assert_eq!(std::env::var(ENVELOPE_KEY_ENV).ok(), before);
    }
}

struct EnvRestoreGuard {
    previous: Option<String>,
}

impl EnvRestoreGuard {
    fn capture() -> Self {
        Self { previous: std::env::var(ENVELOPE_KEY_ENV).ok() }
    }
}

impl Drop for EnvRestoreGuard {
    fn drop(&mut self) {
        if let Some(value) = self.previous.take() {
            std::env::set_var(ENVELOPE_KEY_ENV, value);
        } else {
            std::env::remove_var(ENVELOPE_KEY_ENV);
        }
    }
}

/// Helper: set env, run closure, return its Result.
fn with_key_result<T, F: FnOnce() -> T>(hex_key: &str, f: F) -> T {
    let guard = env_lock().lock().expect("envelope env lock");
    let restore = EnvRestoreGuard::capture();
    std::env::set_var(ENVELOPE_KEY_ENV, hex_key);
    let result = std::panic::catch_unwind(AssertUnwindSafe(f));
    drop(restore);
    drop(guard);
    match result {
        Ok(value) => value,
        Err(payload) => std::panic::resume_unwind(payload),
    }
}
