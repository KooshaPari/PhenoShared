//! `phenotype-diff` — line-level unified diff and patch apply.
//!
//! Migrated from KooshaPari/Diffuse (archived skeleton, `patch` crate intent).
//!
//! Wraps the [`similar`] crate for diffing rather than hand-rolling.
//!
//! # Features
//!
//! * [`diff`] — produce a [`UnifiedDiff`] from two text strings
//! * [`apply`] — apply a patch to a source string
//! * Serialisable output via `serde`
//!
//! # Example
//!
//! ```rust
//! use phenotype_diff::{diff, apply};
//!
//! let old = "hello world\n";
//! let new = "hello rust\n";
//! let patch = diff(old, new);
//! assert!(!patch.hunks.is_empty());
//! let result = apply(old, &patch).unwrap();
//! assert_eq!(result, new);
//! ```

pub mod error;
pub mod model;
pub mod ops;

pub use error::DiffError;
pub use model::{DiffLine, HunkHeader, UnifiedDiff};
pub use ops::{apply, diff};
