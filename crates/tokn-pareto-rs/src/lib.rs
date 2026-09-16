//! ParetoOptimal cost engine — pure pricing & routing logic.
//!
//! No I/O, no CLI, no external API calls. Just pure business logic.

pub mod concurrent;
pub mod cost;
pub mod error;
pub mod event;
pub mod format;
pub mod metrics;
pub mod models;
pub mod plugin;
pub mod pricing;
pub mod utils;

pub use cost::*;
pub use models::*;
pub use plugin::*;
pub use pricing::*;
