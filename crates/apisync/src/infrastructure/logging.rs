//! Logging infrastructure

use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Initialize the global tracing subscriber with an env-filter defaulting to `info`.
pub fn init() {
    let _ = tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer())
        .try_init();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn init_does_not_panic() {
        // A second call after the subscriber is already set just returns an
        // error from `try_init()`, which `init()` discards; it must never panic.
        init();
        init();
    }
}
