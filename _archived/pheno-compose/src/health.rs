// SPDX-License-Identifier: MIT OR Apache-2.0
//! Health-check / monitoring for the PhenoCompose NVMS driver.
//!
//! Provides a simple health probe that verifies:
//! - The NVMS FFI layer can be initialised.
//! - The Go core version is reachable.
//! - Platform info is available.
//!
//! # Usage
//!
//! ```rust
//! use pheno_compose_driver::health::{check, HealthReport};
//!
//! let report = check();
//! println!("healthy: {}", report.healthy);
//! ```

use std::time::Instant;

/// Overall health status of the NVMS subsystem.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct HealthReport {
    /// Whether all health checks passed.
    pub healthy: bool,
    /// NVMS core version string.
    pub version: String,
    /// Platform identifier.
    pub platform: String,
    /// Duration of the health check in milliseconds.
    pub check_duration_ms: u64,
    /// Individual probe results.
    pub probes: Vec<ProbeResult>,
    /// Human-readable summary.
    pub message: String,
}

/// Result of a single health probe.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProbeResult {
    /// Probe name (e.g. `"init"`, `"version"`, `"platform"`).
    pub name: String,
    /// Whether this probe passed.
    pub ok: bool,
    /// Error message if the probe failed.
    pub error: Option<String>,
}

/// Run a full health check against the NVMS subsystem.
///
/// All errors are caught and reported inside the returned
/// [`HealthReport`]; this function never panics.
pub fn check() -> HealthReport {
    let start = Instant::now();
    let mut probes = Vec::new();
    let mut healthy = true;

    // Probe 1: initialise the NVMS core.
    {
        let probe = match nvms_ffi::init() {
            Ok(()) => ProbeResult {
                name: "init".into(),
                ok: true,
                error: None,
            },
            Err(e) => {
                healthy = false;
                ProbeResult {
                    name: "init".into(),
                    ok: false,
                    error: Some(format!("{e:?}")),
                }
            }
        };
        probes.push(probe);
    }

    // Probe 2: read the version string.
    let version = {
        let v = nvms_ffi::version();
        probes.push(ProbeResult {
            name: "version".into(),
            ok: !v.is_empty(),
            error: if v.is_empty() {
                Some("version string is empty".into())
            } else {
                None
            },
        });
        v
    };

    // Probe 3: read platform info.
    let platform = {
        let p = nvms_ffi::platform_info();
        probes.push(ProbeResult {
            name: "platform".into(),
            ok: !p.is_empty(),
            error: if p.is_empty() {
                Some("platform info is empty".into())
            } else {
                None
            },
        });
        p
    };

    let elapsed = start.elapsed();
    HealthReport {
        healthy,
        version,
        platform,
        check_duration_ms: elapsed.as_millis() as u64,
        probes,
        message: if healthy {
            "NVMS subsystem is operational".into()
        } else {
            "NVMS subsystem has degraded or failed probes".into()
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_check_never_panics() {
        let report = check();
        // Should always produce a report without panicking.
        assert!(!report.version.is_empty());
        assert!(!report.platform.is_empty());
        assert!(!report.probes.is_empty());
    }

    #[test]
    fn health_report_is_serializable() {
        let report = check();
        let json = serde_json::to_string(&report).expect("serialisation should work");
        assert!(json.contains("healthy"));
        assert!(json.contains("probes"));
    }

    #[test]
    fn health_report_deserializes() {
        let report = check();
        let json = serde_json::to_string(&report).unwrap();
        let deserialized: HealthReport = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.healthy, report.healthy);
        assert_eq!(deserialized.version, report.version);
    }

    #[test]
    fn check_duration_is_reasonable() {
        let report = check();
        // Should complete well under 10 s (usually < 1 ms).
        assert!(
            report.check_duration_ms < 10_000,
            "health check took too long: {} ms",
            report.check_duration_ms
        );
    }
}
