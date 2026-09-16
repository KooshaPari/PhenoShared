//! Service Level Objectives (SLOs) for the phenotype-tooling ecosystem.
//!
//! SLOs are declarative: a `name`, `target` (success rate or latency
//! p95), and a `window_s`. [`default_slos`] returns the two SLOs that
//! all `phenotype-tooling` deployments should track.
//!
//! ## Burn-rate computation
//!
//! Burn rate at time t over window W is:
//!     burn = (1 - success_ratio_W) / (1 - target)
//! A burn rate of 1.0 means the SLO is exactly on track. >1.0 means the
//! error budget is being consumed faster than sustainable.
//!
//! Multi-window analysis follows the Google SRE workbook
//! (<https://sre.google/workbook/alerting-on-slos/>) -- short and long
//! windows are combined to reduce false positives and catch slow burns.

use std::time::Duration;

// =====================================================================
// SLO definition.
// =====================================================================

/// SLO definition.
///
/// `target` semantics depend on `kind`:
/// - [`SloKind::StartupLatencyP95`]: `target` is the p95 budget in **milliseconds**.
/// - [`SloKind::SuccessRate`]: `target` is the success rate as a **fraction** in `[0.0, 1.0]`.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
pub struct Slo {
    pub name: String,
    pub kind: SloKind,
    pub target: f64,
    pub window_s: u64,
    pub burn_rate_alert: f64,
}

/// Discriminator for the SLO target's unit.
#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SloKind {
    /// Latency budget in milliseconds, measured at p95.
    StartupLatencyP95,
    /// Success rate fraction (e.g. `0.999` for 99.9%).
    SuccessRate,
}

impl Slo {
    /// Construct a startup-latency SLO (ms p95).
    pub fn startup_latency(name: impl Into<String>, target_ms: f64, window_s: u64) -> Self {
        Self {
            name: name.into(),
            kind: SloKind::StartupLatencyP95,
            target: target_ms,
            window_s,
            burn_rate_alert: 2.0,
        }
    }

    /// Construct a success-rate SLO (fraction).
    pub fn success_rate(name: impl Into<String>, target: f64, window_s: u64) -> Self {
        Self {
            name: name.into(),
            kind: SloKind::SuccessRate,
            target,
            window_s,
            burn_rate_alert: 2.0,
        }
    }
}

/// Canonical SLOs for every phenotype-tooling deployment.
pub fn default_slos() -> Vec<Slo> {
    vec![
        Slo::startup_latency("cli_startup_p95", 200.0, 3600),
        Slo::success_rate("cli_success_rate", 0.999, 86_400),
    ]
}

// =====================================================================
// Burn-rate computation (absorbed from argis-monitor).
// =====================================================================

/// A pair of windows used for multi-window burn-rate alerts.
///
/// Following the Google SRE multi-window burn-rate recipe:
/// <https://sre.google/workbook/alerting-on-slos/>
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BurnWindow {
    pub short: Duration,
    pub long: Duration,
}

impl BurnWindow {
    /// The canonical "fast burn" pair: 5m / 1h.
    pub const FAST_BURN: BurnWindow = BurnWindow {
        short: Duration::from_secs(5 * 60),
        long: Duration::from_secs(3600),
    };
    /// The canonical "slow burn" pair: 30m / 6h.
    pub const SLOW_BURN: BurnWindow = BurnWindow {
        short: Duration::from_secs(30 * 60),
        long: Duration::from_secs(6 * 3600),
    };
}

/// Burn-rate math. Operates on (successes, failures, target) over a window.
///
/// Returns the burn rate as a multiplier of the error budget consumption.
/// Returns `f64::INFINITY` if the target is 1.0 (impossible SLO).
/// Returns 0.0 if no requests observed in the window.
pub fn burn_rate(successes: u64, failures: u64, target: f64) -> f64 {
    let total = successes + failures;
    if total == 0 {
        return 0.0;
    }
    let success_ratio = successes as f64 / total as f64;
    let error_ratio = 1.0 - success_ratio;
    let allowed_error = 1.0 - target;
    if allowed_error <= 0.0 {
        // SLO is "100% success". Any failure is unbounded burn.
        return if error_ratio > 0.0 {
            f64::INFINITY
        } else {
            0.0
        };
    }
    error_ratio / allowed_error
}

/// Multi-window burn. Returns the short and long burn rates.
///
/// Used by the SRE alerting recipe (alert when short_window_burn > 14.4 AND
/// long_window_burn > 14.4). Both values are returned for richer dashboards.
pub fn multi_window_burn(
    short_success: u64,
    short_failure: u64,
    long_success: u64,
    long_failure: u64,
    target: f64,
) -> (f64, f64) {
    let short = burn_rate(short_success, short_failure, target);
    let long = burn_rate(long_success, long_failure, target);
    (short, long)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_slos_returns_two() {
        let slos = default_slos();
        assert_eq!(slos.len(), 2);
    }

    #[test]
    fn cli_startup_target_is_200ms() {
        let slos = default_slos();
        let startup = slos
            .iter()
            .find(|s| matches!(s.kind, SloKind::StartupLatencyP95))
            .expect("startup slo");
        assert_eq!(startup.target, 200.0);
        assert_eq!(startup.window_s, 3600);
    }

    #[test]
    fn cli_success_rate_is_999() {
        let slos = default_slos();
        let sr = slos
            .iter()
            .find(|s| matches!(s.kind, SloKind::SuccessRate))
            .expect("success-rate slo");
        assert!((sr.target - 0.999).abs() < 1e-9);
        assert_eq!(sr.window_s, 86_400);
    }

    #[test]
    fn slo_roundtrips_via_serde_json() {
        let s = Slo::startup_latency("test", 100.0, 600);
        let json = serde_json::to_string(&s).unwrap();
        let back: Slo = serde_json::from_str(&json).unwrap();
        assert_eq!(back, s);
    }

    // --- burn-rate tests ---

    #[test]
    fn zero_traffic_returns_zero_burn() {
        assert_eq!(burn_rate(0, 0, 0.999), 0.0);
    }

    #[test]
    fn all_successes_returns_zero_burn() {
        assert_eq!(burn_rate(1000, 0, 0.999), 0.0);
    }

    #[test]
    fn at_target_returns_one_x_burn() {
        // 0.1% error rate against a 99.9% target = exactly 1x burn.
        let br = burn_rate(999, 1, 0.999);
        assert!((br - 1.0).abs() < 1e-9, "expected ~1.0, got {br}");
    }

    #[test]
    fn ten_x_overshoot() {
        // 1% error rate against 99.9% target = 10x burn.
        let br = burn_rate(990, 10, 0.999);
        assert!((br - 10.0).abs() < 1e-3, "expected ~10.0, got {br}");
    }

    #[test]
    fn target_one_zero_returns_inf_for_any_failure() {
        assert!(burn_rate(100, 1, 1.0).is_infinite());
        assert_eq!(burn_rate(100, 0, 1.0), 0.0);
    }

    #[test]
    fn multi_window_returns_short_and_long() {
        let (s, l) = multi_window_burn(999, 100, 9990, 10, 0.999);
        // short: 100/1099 error ratio vs 0.001 budget = ~90.99x
        let expected_short = (100.0_f64 / 1099.0) / 0.001;
        assert!((s - expected_short).abs() < 1e-3, "expected ~{expected_short}, got {s}");
        // long: 10/10000 error ratio vs 0.001 budget = 1x
        assert!((l - 1.0).abs() < 1e-9, "expected ~1.0, got {l}");
    }
}
