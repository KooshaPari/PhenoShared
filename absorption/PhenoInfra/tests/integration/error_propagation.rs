//! Integration tests: error type propagation across crates.
//!
//! Verifies that error types from `nvms-ffi` convert cleanly into
//! `pheno-compose-driver::errors::Error` and that display strings
//! are preserved.

/// Every `nvms_ffi::NvmsError` variant must convert into
/// `pheno_compose_driver::errors::Error` and produce a non-empty
/// display string.
#[test]
fn every_ffi_error_variant_converts_to_driver_error() {
    use pheno_compose_driver::errors::Error;

    let ffi_errors = [
        nvms_ffi::NvmsError::InitFailed,
        nvms_ffi::NvmsError::CreateFailed,
        nvms_ffi::NvmsError::StartFailed,
        nvms_ffi::NvmsError::StopFailed,
        nvms_ffi::NvmsError::DestroyFailed,
        nvms_ffi::NvmsError::AppleSiliconNotSupported,
        nvms_ffi::NvmsError::CudaInitFailed,
        nvms_ffi::NvmsError::RocmInitFailed,
    ];

    for ffi_err in &ffi_errors {
        let err: Error = (*ffi_err).into();
        let display = err.to_string();
        assert!(
            !display.is_empty(),
            "display string should not be empty for {ffi_err:?}"
        );
        assert!(
            display.len() > 3,
            "display string should be meaningful for {ffi_err:?}: got '{display}'"
        );
    }
}

/// Driver-level error variants must produce distinct, meaningful
/// display strings that identify the failure mode.
#[test]
fn driver_error_display_strings_are_distinct() {
    use pheno_compose_driver::errors::Error;

    let driver_errors = [
        Error::InitFailed("x".into()),
        Error::GpuInitFailed("x".into()),
        Error::CreateFailed("x".into()),
        Error::StartFailed("x".into()),
        Error::StopFailed("x".into()),
        Error::DestroyFailed("x".into()),
        Error::Config("x".into()),
        Error::AppleSiliconNotSupported,
        Error::CudaInitFailed("x".into()),
        Error::RocmInitFailed("x".into()),
        Error::UnsupportedPlatform,
        Error::Internal("x".into()),
    ];

    let mut display_set = std::collections::HashSet::new();
    for err in &driver_errors {
        let display = err.to_string();
        assert!(
            display_set.insert(display.clone()),
            "duplicate display string: '{display}'"
        );
    }
}

/// `Result<T>` type alias from errors module must work with `?` operator.
#[test]
fn result_alias_propagates_errors_with_question_mark() {
    use pheno_compose_driver::errors::{Error, Result};

    fn inner_operation() -> Result<i32> {
        Err(Error::Config("bad value".into()))
    }

    fn outer_operation() -> Result<i32> {
        inner_operation()?;
        Ok(0)
    }

    let err = outer_operation().unwrap_err();
    assert!(
        err.to_string().contains("bad value"),
        "error message should propagate: {err}"
    );
}
