#![no_main]

use libfuzzer_sys::fuzz_target;

/// Fuzz target that exercises [`pheno_errors::AppError`] construction and
/// [`Display`] / [`AppError::kind()`] for arbitrary byte inputs that can
/// be lossily decoded as UTF-8.
///
/// This ensures that no variant's `Display` impl panics or produces invalid
/// output for any conceivable string payload (including multi-byte Unicode,
/// null bytes, control characters, etc.).
fuzz_target!(|data: &[u8]| {
    // Use a lossy conversion so we always get a valid String to test with.
    let msg = String::from_utf8_lossy(data).into_owned();

    // Exercise every constructor at least once, verifying Display + kind
    // do not panic.
    let domain = pheno_errors::AppError::domain(&msg);
    let _ = format!("{domain}");
    let _ = domain.kind();

    let conflict = pheno_errors::AppError::conflict(&msg);
    let _ = format!("{conflict}");

    let validation = pheno_errors::AppError::validation(&msg);
    let _ = format!("{validation}");

    let storage = pheno_errors::AppError::storage(&msg);
    let _ = format!("{storage}");

    let not_found = pheno_errors::AppError::not_found(&msg, &msg);
    let _ = format!("{not_found}");

    // Also exercise the From<String> / From<&'static str> conversions.
    let _: pheno_errors::AppError = msg.clone().into();
    let _: pheno_errors::AppError = "static literal".into();

    // Exercise the `log_warn` / `log_error` helpers (they emit tracing
    // events but should never panic).
    let _ = pheno_errors::AppError::domain(&msg).log_warn();
    let _ = pheno_errors::AppError::storage(&msg).log_error();
});
