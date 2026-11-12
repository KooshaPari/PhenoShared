// SPDX-License-Identifier: MIT OR Apache-2.0
//! Common error types for the PhenoCompose workspace.
//!
//! This module provides a unified error type that wraps errors from
//! all subordinate crates (nvms-ffi, pheno-config, etc.).  Callers
//! who need to handle specific subsystem failures can match on the
//! variant; all others can use `?` via the `From` impls.
//!
//! # Example
//!
//! ```rust
//! use pheno_compose_driver::errors::Error;
//!
//! fn example() -> Result<(), Error> {
//!     // All nvms_ffi::NvmsError values convert automatically.
//!     nvms_ffi::init()?;
//!     Ok(())
//! }
//! ```

use thiserror::Error;

/// Unified error type for the PhenoCompose driver and its FFI bridge.
///
/// Every error variant carries enough context to diagnose the failure
/// without crawling through CGo stack frames.
#[derive(Error, Debug)]
pub enum Error {
    // ── Initialization ────────────────────────────────────────────
    /// NVMS core initialisation failed (e.g. Go runtime panic).
    #[error("NVMS initialization failed: {0}")]
    InitFailed(String),

    /// GPU subsystem initialisation failed.
    #[error("GPU init failed: {0}")]
    GpuInitFailed(String),

    // ── Instance lifecycle ────────────────────────────────────────
    /// Instance creation returned a null pointer.
    #[error("instance creation failed: {0}")]
    CreateFailed(String),

    /// Instance could not be started.
    #[error("instance start failed: {0}")]
    StartFailed(String),

    /// Instance could not be stopped.
    #[error("instance stop failed: {0}")]
    StopFailed(String),

    /// Instance could not be destroyed (resource leak possible).
    #[error("instance destroy failed: {0}")]
    DestroyFailed(String),

    // ── FFI bridge ────────────────────────────────────────────────
    /// An error originating from the `nvms-ffi` crate.
    #[error("FFI error: {0}")]
    Ffi(#[from] nvms_ffi::NvmsError),

    /// A C string contained an interior nul byte.
    #[error("invalid C string: {0}")]
    InvalidCString(#[from] std::ffi::NulError),

    // ── Configuration ─────────────────────────────────────────────
    /// Configuration validation failed.
    #[error("configuration error: {0}")]
    Config(String),

    // ── Platform / backend ────────────────────────────────────────
    /// Apple Silicon (M-series) platform not supported.
    #[error("Apple Silicon platform is not supported on this host")]
    AppleSiliconNotSupported,

    /// CUDA GPU backend initialisation failed.
    #[error("CUDA init failed: {0}")]
    CudaInitFailed(String),

    /// ROCm GPU backend initialisation failed.
    #[error("ROCm init failed: {0}")]
    RocmInitFailed(String),

    /// No matching platform backend is available.
    #[error("no supported platform backend found")]
    UnsupportedPlatform,

    // ── Internal / unexpected ─────────────────────────────────────
    /// An internal invariant was violated (should never happen).
    #[error("internal error: {0}")]
    Internal(String),
}

/// Convenience alias for `Result<T, Error>`.
pub type Result<T> = std::result::Result<T, Error>;

// ── Conversions from nvms_ffi::NvmsError ──────────────────────────
// ── Conversions from String / &str (convenience for internal use) ─
impl From<&str> for Error {
    fn from(msg: &str) -> Self {
        Error::Internal(msg.to_owned())
    }
}

impl From<String> for Error {
    fn from(msg: String) -> Self {
        Error::Internal(msg)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn error_display_formatting() {
        let err = Error::InitFailed("test".into());
        assert_eq!(err.to_string(), "NVMS initialization failed: test");
    }

    #[test]
    fn ffi_error_conversion() {
        let ffi_err = nvms_ffi::NvmsError::InitFailed;
        let err: Error = ffi_err.into();
        assert!(err.to_string().contains("NVMS init"));
    }

    #[test]
    fn all_error_variants_are_debug_and_display() {
        let variants: Vec<Error> = vec![
            Error::InitFailed("x".into()),
            Error::GpuInitFailed("x".into()),
            Error::CreateFailed("x".into()),
            Error::StartFailed("x".into()),
            Error::StopFailed("x".into()),
            Error::DestroyFailed("x".into()),
            Error::Ffi(nvms_ffi::NvmsError::InitFailed),
            Error::InvalidCString(std::ffi::CString::new("a\0b").unwrap_err()),
            Error::Config("x".into()),
            Error::AppleSiliconNotSupported,
            Error::CudaInitFailed("x".into()),
            Error::RocmInitFailed("x".into()),
            Error::UnsupportedPlatform,
            Error::Internal("x".into()),
        ];
        for v in &variants {
            let _ = format!("{v}"); // Display
            let _ = format!("{v:?}"); // Debug
        }
    }

    #[test]
    fn result_alias_works_with_question_mark() {
        fn fallible() -> Result<i32> {
            Ok(42)
        }
        assert_eq!(fallible().unwrap(), 42);
    }

    #[test]
    fn from_str_and_string() {
        let _: Error = "oops".into();
        let _: Error = "oops".to_string().into();
    }
}
