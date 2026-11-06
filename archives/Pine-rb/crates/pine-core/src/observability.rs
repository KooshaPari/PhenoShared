//! Observability module for Pine.
//!
//! Provides a centralized entry point for logging, tracing, and
//! telemetry initialization.  Use [`init_observability`] at the
//! start of any binary or integration test that needs structured
//! diagnostics.
//!
//! # Example
//!
//! ```
//! use pine_core::observability::init_observability;
//!
//! init_observability();
//! tracing::info!("pine-core observability is active");
//! ```

use tracing_subscriber::prelude::*;

/// Initialize the observability subsystem.
///
/// Sets up a `tracing-subscriber` with a console-friendly format
/// that writes to stderr.  Safe to call multiple times — subsequent
/// calls are no-ops.
///
/// # Example
///
/// ```
/// use pine_core::observability::init_observability;
///
/// init_observability();
/// tracing::info!("pine-core observability is active");
/// ```
pub fn init_observability() {
    let fmt_layer = tracing_subscriber::fmt::layer()
        .with_target(true)
        .with_level(true)
        .with_line_number(true);

    let subscriber = tracing_subscriber::registry().with(fmt_layer);

    let _ = tracing::subscriber::set_global_default(subscriber);
}
