//! Detect and wrap external profilers (samply, cargo-flamegraph, Instruments).
//!
//! Each profiler is probed at runtime via `which`/`where`; the harness degrades
//! gracefully when none are installed — data is still collected via the internal
//! RSS poller and wall-clock timings.

use std::process::Command;
use tracing::{debug, warn};

/// External profiler available on this system.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExternalProfiler {
    /// Mozilla samply — low-overhead sampling profiler, macOS + Linux.
    Samply,
    /// cargo-flamegraph (wraps perf on Linux, DTrace on macOS).
    CargoFlamegraph,
    /// Apple Instruments (macOS only) — xctrace.
    Instruments,
    /// No external profiler available; harness uses internal RSS + wall-clock.
    None,
}

impl ExternalProfiler {
    /// Probe the system for available profilers in priority order.
    pub fn detect() -> Self {
        if command_exists("samply") {
            debug!("detected external profiler: samply");
            return ExternalProfiler::Samply;
        }
        if command_exists("cargo-flamegraph") || command_exists("flamegraph") {
            debug!("detected external profiler: cargo-flamegraph");
            return ExternalProfiler::CargoFlamegraph;
        }
        if command_exists("xctrace") {
            debug!("detected external profiler: instruments (xctrace)");
            return ExternalProfiler::Instruments;
        }
        warn!("no external profiler found; using internal RSS + wall-clock only");
        ExternalProfiler::None
    }

    /// Human-readable name.
    pub fn name(&self) -> &'static str {
        match self {
            ExternalProfiler::Samply => "samply",
            ExternalProfiler::CargoFlamegraph => "cargo-flamegraph",
            ExternalProfiler::Instruments => "xctrace (Instruments)",
            ExternalProfiler::None => "none (internal only)",
        }
    }

    /// Whether any external profiler is available.
    pub fn is_available(&self) -> bool {
        !matches!(self, ExternalProfiler::None)
    }
}

fn command_exists(name: &str) -> bool {
    Command::new("which")
        .arg(name)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detect_returns_a_variant() {
        // Smoke test: detect() always returns a valid variant without panicking.
        let p = ExternalProfiler::detect();
        let _ = p.name();
    }

    #[test]
    fn none_is_not_available() {
        assert!(!ExternalProfiler::None.is_available());
    }
}
