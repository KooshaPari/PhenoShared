//! Re-export canonical error types from phenotype-error-core.
//! Provides type alias for automation-specific operations.
//!
//! `phenotype-error-core` exposes the layer-specific error enums directly
//! (e.g. `ApiError`, `DomainError`). We define the legacy umbrella alias
//! `PhenoError` and the convenience `Result` type locally so the rest of
//! the Eidolon API surface (and downstream crates like `eidolon-desktop`,
//! `eidolon-mobile`, `eidolon-sandbox`) keep their public types stable.

use phenotype_error_core::ApiError;

/// Phenotype umbrella error alias for cross-crate consumers (Sidekick, Eidolon, etc.).
///
/// Equivalent to [`ApiError`]; provided so downstream crates can `use
/// eidolon_core::PhenoError` (or `eidolon_core::error::PhenoError`)
/// without coupling to the underlying alias name.
pub type PhenoError = ApiError;

/// Convenience result type.
pub type Result<T> = std::result::Result<T, ApiError>;

/// Automation-specific result type (alias for convenience).
pub type AutomationResult<T> = Result<T>;
