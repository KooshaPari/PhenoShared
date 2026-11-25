//! Tracing setup helpers for the BytePort CLI.
//!
//! Provides a small surface over the `tracing` facade so the CLI can emit
//! structured log lines without pulling in a heavyweight telemetry stack.
//! Macros like `tracing::info!` compile to no-ops when no subscriber is
//! installed, so this module is safe to call unconditionally.

/// Emit a single startup breadcrumb so the binary always produces one
/// `tracing` event. Useful for verifying log wiring in CI and local dev.
pub fn log_startup_banner() {
    tracing::info!("byteport-cli starting");
}

/// Emit a shutdown breadcrumb when the [`ShutdownBanner`] guard is dropped.
pub fn log_shutdown_banner() {
    tracing::info!("byteport-cli exiting");
}

/// Drop guard that emits a shutdown breadcrumb on scope exit.
///
/// Install it at the top of `main` so a matching breadcrumb is emitted
/// regardless of how `main` returns (normal completion or panic unwind).
pub struct ShutdownBanner;

impl Drop for ShutdownBanner {
    fn drop(&mut self) {
        log_shutdown_banner();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn banners_do_not_panic_without_subscriber() {
        // No tracing subscriber installed; macros must compile and run as no-ops.
        log_startup_banner();
        log_shutdown_banner();
    }

    #[test]
    fn shutdown_banner_runs_on_drop() {
        // Triggering Drop on a local binding emits the breadcrumb; safe to run
        // repeatedly in a test without any external state.
        let _guard = ShutdownBanner;
    }
}
