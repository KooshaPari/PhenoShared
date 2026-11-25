//! `traceability-decorators` — source-file annotation scanner.
//!
//! Walks source trees for FR/spec trace annotations in Rust, TypeScript, Go,
//! and plain line-comment form, emitting [`ScanTraceLink`] records.
//!
//! Supported annotation patterns:
//! * **Rust attribute** `#[trace_fr(spec="SPEC-001", fr="FR-001")]`
//! * **Generic line comment** `// FR: FR-001` (any language)
//! * **TS/Go block comment** `@trace_fr spec="SPEC-001" fr="FR-001"`

#![forbid(unsafe_code)]
#![warn(missing_docs)]

pub mod patterns;
pub mod scanner;

pub use patterns::ScanTraceLink;
pub use scanner::{scan_dir, scan_file, ScanError};
