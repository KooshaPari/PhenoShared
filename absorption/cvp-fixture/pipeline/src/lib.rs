//! Pipeline core library: items, filters, and the [`Pipeline`] orchestrator.
//!
//! The library is small and intentionally unopinionated. It exposes the
//! [`Item`] data model, a family of [`filters::Filter`] implementations, and
//! the [`Pipeline`] type that threads items through them.

pub mod error;
pub mod filters;
pub mod item;
pub mod pipeline;

pub use error::{PipelineError, Result};
pub use item::Item;
pub use pipeline::Pipeline;