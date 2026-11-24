//! AgilePlus Triage & Backlog adapter.
//!
//! Provides rule-based intent classification, backlog item management,
//! and CLAUDE.md/AGENTS.md prompt router generation.
//!
//! Traceability: FR-048, FR-049, FR-050 / WP17

pub mod backlog;
pub mod classifier;
pub mod error;
pub mod router;

pub use agileplus_domain::domain::backlog::{BacklogItem, BacklogPriority, BacklogStatus, Intent};
pub use classifier::{TriageClassifier, TriageResult};
pub use error::TriageError;
pub use router::RouterGenerator;
