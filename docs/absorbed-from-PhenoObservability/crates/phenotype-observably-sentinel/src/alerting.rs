//! Alerting rule engine — threshold-based alert evaluation with a hexagonal
//! `AlertSink` port.
//!
//! # Design
//!
//! - [`AlertRule`] is pure data (serialisable config) that describes *when* an
//!   alert should fire.
//! - [`AlertEvaluator`] owns a collection of rules and a map of per-rule
//!   breach-tracking state.  It is driven by [`MetricSample`] values pushed by
//!   the caller.
//! - [`AlertSink`] is the **hexagonal port**: a trait that the evaluator writes
//!   fired/resolved alerts to.  Two adapters are provided:
//!   - [`InMemoryAlertSink`] — accumulates alerts in a `Vec`; ideal for tests.
//!   - [`LogAlertSink`]     — logs via `tracing::warn!` / `tracing::info!`.
//!
//! # Invariants
//! - An alert fires **only once** per rule until the rule clears (no re-fire
//!   while already active).
//! - A resolution is emitted **only once** when the metric drops back below
//!   the threshold.
//! - Multiple rules are evaluated independently.
//! - For-duration semantics: the threshold must be breached *continuously* for
//!   at least `for_duration` before the alert fires.  A single sample below the
//!   threshold resets the breach timer.

use chrono::{DateTime, Utc};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, sync::Arc, time::Duration};
use thiserror::Error;

// ── Error ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum AlertError {
    #[error("sink write failed: {0}")]
    SinkError(String),
}

// ── Domain types ──────────────────────────────────────────────────────────────

/// A single metric observation pushed to the evaluator.
#[derive(Debug, Clone)]
pub struct MetricSample {
    /// Name of the metric (must match [`AlertRule::metric`]).
    pub metric: String,
    /// Observed value.
    pub value: f64,
    /// Wall-clock time of the observation.
    pub timestamp: DateTime<Utc>,
}

impl MetricSample {
    pub fn new(metric: impl Into<String>, value: f64) -> Self {
        Self {
            metric: metric.into(),
            value,
            timestamp: Utc::now(),
        }
    }
}

/// Comparison operator for a threshold condition.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThresholdOp {
    /// Fire when `value > threshold`.
    GreaterThan,
    /// Fire when `value >= threshold`.
    GreaterThanOrEqual,
    /// Fire when `value < threshold`.
    LessThan,
    /// Fire when `value <= threshold`.
    LessThanOrEqual,
    /// Fire when `value == threshold` (floating-point exact; use with care).
    Equal,
}

impl ThresholdOp {
    fn evaluate(self, value: f64, threshold: f64) -> bool {
        match self {
            Self::GreaterThan => value > threshold,
            Self::GreaterThanOrEqual => value >= threshold,
            Self::LessThan => value < threshold,
            Self::LessThanOrEqual => value <= threshold,
            Self::Equal => (value - threshold).abs() < f64::EPSILON,
        }
    }
}

/// Importance level of a fired alert.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Severity {
    Info,
    Warning,
    Critical,
}

/// Data-driven rule describing when an alert should fire.
///
/// Rules are config-first: they are cheap to clone and serialise, and carry no
/// mutable state themselves (state lives in [`AlertEvaluator`]).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRule {
    /// Stable identifier for this rule (used as map key).
    pub id: String,
    /// Human-readable name.
    pub name: String,
    /// Name of the metric this rule watches.
    pub metric: String,
    /// Comparison operator applied to the metric value.
    pub op: ThresholdOp,
    /// Threshold value to compare against.
    pub threshold: f64,
    /// Importance level carried on fired alerts.
    pub severity: Severity,
    /// How long the threshold must be continuously breached before the alert
    /// fires.  Use [`Duration::ZERO`] for immediate-fire behaviour.
    #[serde(with = "duration_millis")]
    pub for_duration: Duration,
}

/// A fired or resolved alert emitted by [`AlertEvaluator`].
#[derive(Debug, Clone, PartialEq)]
pub struct Alert {
    /// ID of the [`AlertRule`] that produced this alert.
    pub rule_id: String,
    /// Human-readable rule name.
    pub rule_name: String,
    /// Name of the monitored metric.
    pub metric: String,
    /// Observed value that triggered the state change.
    pub value: f64,
    /// Severity copied from the rule.
    pub severity: Severity,
    /// Whether this is a firing (`true`) or resolving (`false`) alert.
    pub firing: bool,
    /// Wall-clock time the alert was emitted.
    pub fired_at: DateTime<Utc>,
}

// ── AlertSink port (hexagonal) ────────────────────────────────────────────────

/// Hexagonal port for alert dispatch.
///
/// Implementations must be object-safe (`dyn AlertSink`).
pub trait AlertSink: Send + Sync {
    /// Called when a rule fires or resolves.
    fn send(&self, alert: Alert) -> Result<(), AlertError>;
}

// ── In-memory adapter ─────────────────────────────────────────────────────────

/// Test-friendly adapter that accumulates alerts in an in-memory `Vec`.
#[derive(Debug, Default)]
pub struct InMemoryAlertSink {
    alerts: Mutex<Vec<Alert>>,
}

impl InMemoryAlertSink {
    pub fn new() -> Arc<Self> {
        Arc::new(Self::default())
    }

    /// Return a snapshot of all received alerts.
    pub fn alerts(&self) -> Vec<Alert> {
        self.alerts.lock().clone()
    }

    /// Return only firing alerts.
    pub fn firing(&self) -> Vec<Alert> {
        self.alerts
            .lock()
            .iter()
            .filter(|a| a.firing)
            .cloned()
            .collect()
    }

    /// Return only resolved alerts.
    pub fn resolved(&self) -> Vec<Alert> {
        self.alerts
            .lock()
            .iter()
            .filter(|a| !a.firing)
            .cloned()
            .collect()
    }
}

impl AlertSink for InMemoryAlertSink {
    fn send(&self, alert: Alert) -> Result<(), AlertError> {
        self.alerts.lock().push(alert);
        Ok(())
    }
}

// ── Log adapter ───────────────────────────────────────────────────────────────

/// Adapter that forwards alerts to the `tracing` framework.
#[derive(Debug, Default)]
pub struct LogAlertSink;

impl AlertSink for LogAlertSink {
    fn send(&self, alert: Alert) -> Result<(), AlertError> {
        if alert.firing {
            tracing::warn!(
                rule_id = %alert.rule_id,
                rule_name = %alert.rule_name,
                metric    = %alert.metric,
                value     = alert.value,
                severity  = ?alert.severity,
                "ALERT FIRING"
            );
        } else {
            tracing::info!(
                rule_id = %alert.rule_id,
                rule_name = %alert.rule_name,
                metric    = %alert.metric,
                value     = alert.value,
                "ALERT RESOLVED"
            );
        }
        Ok(())
    }
}

// ── Evaluator ─────────────────────────────────────────────────────────────────

/// Per-rule mutable breach-tracking state kept inside the evaluator.
#[derive(Debug)]
struct RuleState {
    /// Whether this rule is currently in firing state.
    is_firing: bool,
    /// When the current continuous breach started (`None` if not breaching).
    breach_started: Option<DateTime<Utc>>,
}

impl RuleState {
    fn new() -> Self {
        Self {
            is_firing: false,
            breach_started: None,
        }
    }
}

/// Stateful evaluator that maps metric samples to alert fire/resolve events.
///
/// The evaluator is intentionally *synchronous* and single-threaded in its
/// state (wrapped in a `Mutex` for `Send + Sync`).  Push samples from any
/// thread; the lock is held only for the duration of evaluation.
pub struct AlertEvaluator {
    rules: Vec<AlertRule>,
    state: Mutex<HashMap<String, RuleState>>,
    sink: Arc<dyn AlertSink>,
}

impl AlertEvaluator {
    /// Create a new evaluator with `rules` and a sink to write alerts to.
    pub fn new(rules: Vec<AlertRule>, sink: Arc<dyn AlertSink>) -> Self {
        let state = rules
            .iter()
            .map(|r| (r.id.clone(), RuleState::new()))
            .collect();
        Self {
            rules,
            state: Mutex::new(state),
            sink,
        }
    }

    /// Push a metric sample and evaluate all matching rules.
    ///
    /// May call `AlertSink::send` zero or more times depending on rule matches.
    pub fn push(&self, sample: &MetricSample) -> Result<(), AlertError> {
        let mut states = self.state.lock();

        for rule in &self.rules {
            if rule.metric != sample.metric {
                continue;
            }

            let state = states.entry(rule.id.clone()).or_insert_with(RuleState::new);

            let breaching = rule.op.evaluate(sample.value, rule.threshold);

            if breaching {
                // Start or extend breach window.
                let breach_start = *state.breach_started.get_or_insert(sample.timestamp);
                let elapsed = sample
                    .timestamp
                    .signed_duration_since(breach_start)
                    .to_std()
                    .unwrap_or(Duration::ZERO);

                if !state.is_firing && elapsed >= rule.for_duration {
                    // Fire!
                    state.is_firing = true;
                    self.sink.send(Alert {
                        rule_id: rule.id.clone(),
                        rule_name: rule.name.clone(),
                        metric: rule.metric.clone(),
                        value: sample.value,
                        severity: rule.severity,
                        firing: true,
                        fired_at: sample.timestamp,
                    })?;
                }
            } else {
                // Below threshold — reset breach timer.
                state.breach_started = None;
                if state.is_firing {
                    // Resolve!
                    state.is_firing = false;
                    self.sink.send(Alert {
                        rule_id: rule.id.clone(),
                        rule_name: rule.name.clone(),
                        metric: rule.metric.clone(),
                        value: sample.value,
                        severity: rule.severity,
                        firing: false,
                        fired_at: sample.timestamp,
                    })?;
                }
            }
        }

        Ok(())
    }

    /// Return the set of rule IDs currently in the firing state.
    pub fn firing_rule_ids(&self) -> Vec<String> {
        self.state
            .lock()
            .iter()
            .filter(|(_, s)| s.is_firing)
            .map(|(id, _)| id.clone())
            .collect()
    }
}

// ── serde helper: Duration ↔ milliseconds ─────────────────────────────────────

mod duration_millis {
    use serde::{Deserialize, Deserializer, Serializer};
    use std::time::Duration;

    pub fn serialize<S: Serializer>(d: &Duration, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_u64(d.as_millis() as u64)
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Duration, D::Error> {
        let ms = u64::deserialize(d)?;
        Ok(Duration::from_millis(ms))
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use std::time::Duration;

    // Helper: a simple "cpu_usage > 80%" rule, fires immediately.
    fn cpu_rule() -> AlertRule {
        AlertRule {
            id: "cpu-high".to_string(),
            name: "CPU High".to_string(),
            metric: "cpu_usage".to_string(),
            op: ThresholdOp::GreaterThan,
            threshold: 80.0,
            severity: Severity::Warning,
            for_duration: Duration::ZERO,
        }
    }

    // Helper: same rule but requires 10 s of sustained breach.
    fn cpu_rule_with_duration(dur: Duration) -> AlertRule {
        AlertRule {
            for_duration: dur,
            ..cpu_rule()
        }
    }

    fn sample(metric: &str, value: f64) -> MetricSample {
        MetricSample::new(metric, value)
    }

    fn sample_at(metric: &str, value: f64, ts: DateTime<Utc>) -> MetricSample {
        MetricSample {
            metric: metric.to_string(),
            value,
            timestamp: ts,
        }
    }

    // ── FR-OBS-012: rule fires when threshold is breached ────────────────────

    #[test]
    fn rule_fires_when_threshold_breached() {
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(vec![cpu_rule()], Arc::clone(&sink) as Arc<dyn AlertSink>);

        eval.push(&sample("cpu_usage", 95.0)).unwrap();

        let alerts = sink.firing();
        assert_eq!(alerts.len(), 1, "should fire exactly one alert");
        assert_eq!(alerts[0].rule_id, "cpu-high");
        assert!(alerts[0].firing);
        assert_eq!(alerts[0].severity, Severity::Warning);
    }

    // ── FR-OBS-012: rule does NOT fire when below threshold ──────────────────

    #[test]
    fn rule_does_not_fire_below_threshold() {
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(vec![cpu_rule()], Arc::clone(&sink) as Arc<dyn AlertSink>);

        eval.push(&sample("cpu_usage", 79.9)).unwrap();
        eval.push(&sample("cpu_usage", 50.0)).unwrap();

        assert!(sink.alerts().is_empty(), "no alert below threshold");
    }

    // ── FR-OBS-012: alert resolves when metric clears ────────────────────────

    #[test]
    fn alert_resolves_when_metric_clears() {
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(vec![cpu_rule()], Arc::clone(&sink) as Arc<dyn AlertSink>);

        eval.push(&sample("cpu_usage", 95.0)).unwrap(); // fire
        eval.push(&sample("cpu_usage", 70.0)).unwrap(); // resolve

        let all = sink.alerts();
        assert_eq!(all.len(), 2);
        assert!(all[0].firing, "first alert should be firing");
        assert!(!all[1].firing, "second alert should be resolved");
    }

    // ── FR-OBS-012: alert does NOT re-fire while already active ─────────────

    #[test]
    fn alert_does_not_refire_while_active() {
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(vec![cpu_rule()], Arc::clone(&sink) as Arc<dyn AlertSink>);

        eval.push(&sample("cpu_usage", 90.0)).unwrap(); // fire
        eval.push(&sample("cpu_usage", 92.0)).unwrap(); // still above — no second fire
        eval.push(&sample("cpu_usage", 99.0)).unwrap(); // still above — no second fire

        assert_eq!(sink.firing().len(), 1, "should have fired exactly once");
    }

    // ── FR-OBS-012: for-duration — does not fire before duration elapses ────

    #[test]
    fn for_duration_does_not_fire_before_elapsed() {
        let sink = InMemoryAlertSink::new();
        let rule = cpu_rule_with_duration(Duration::from_secs(30));
        let eval = AlertEvaluator::new(vec![rule], Arc::clone(&sink) as Arc<dyn AlertSink>);

        let now = Utc::now();
        // Sample 10 s after breach start — not enough.
        eval.push(&sample_at("cpu_usage", 95.0, now)).unwrap();
        eval.push(&sample_at(
            "cpu_usage",
            95.0,
            now + chrono::Duration::seconds(10),
        ))
        .unwrap();

        assert!(
            sink.firing().is_empty(),
            "should not fire before for_duration elapses"
        );
    }

    // ── FR-OBS-012: for-duration — fires after duration elapses ─────────────

    #[test]
    fn for_duration_fires_after_elapsed() {
        let sink = InMemoryAlertSink::new();
        let rule = cpu_rule_with_duration(Duration::from_secs(30));
        let eval = AlertEvaluator::new(vec![rule], Arc::clone(&sink) as Arc<dyn AlertSink>);

        let now = Utc::now();
        eval.push(&sample_at("cpu_usage", 95.0, now)).unwrap();
        // 31 s later — for_duration elapsed.
        eval.push(&sample_at(
            "cpu_usage",
            95.0,
            now + chrono::Duration::seconds(31),
        ))
        .unwrap();

        assert_eq!(sink.firing().len(), 1, "should fire after for_duration");
    }

    // ── FR-OBS-012: for-duration — breach reset resets timer ────────────────

    #[test]
    fn for_duration_breach_reset_resets_timer() {
        let sink = InMemoryAlertSink::new();
        let rule = cpu_rule_with_duration(Duration::from_secs(30));
        let eval = AlertEvaluator::new(vec![rule], Arc::clone(&sink) as Arc<dyn AlertSink>);

        let now = Utc::now();
        eval.push(&sample_at("cpu_usage", 95.0, now)).unwrap();
        // Drop below threshold — resets breach timer.
        eval.push(&sample_at(
            "cpu_usage",
            60.0,
            now + chrono::Duration::seconds(20),
        ))
        .unwrap();
        // Breach again; only 15 s since reset — not enough.
        eval.push(&sample_at(
            "cpu_usage",
            95.0,
            now + chrono::Duration::seconds(25),
        ))
        .unwrap();
        eval.push(&sample_at(
            "cpu_usage",
            95.0,
            now + chrono::Duration::seconds(35),
        ))
        .unwrap();

        assert!(sink.firing().is_empty(), "timer reset; should not fire yet");
    }

    // ── FR-OBS-012: severity is carried on the alert ─────────────────────────

    #[test]
    fn severity_is_carried_on_alert() {
        let mut rule = cpu_rule();
        rule.severity = Severity::Critical;
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(vec![rule], Arc::clone(&sink) as Arc<dyn AlertSink>);

        eval.push(&sample("cpu_usage", 95.0)).unwrap();

        assert_eq!(sink.firing()[0].severity, Severity::Critical);
    }

    // ── FR-OBS-012: multiple rules are independent ───────────────────────────

    #[test]
    fn multiple_rules_evaluated_independently() {
        let mem_rule = AlertRule {
            id: "mem-high".to_string(),
            name: "Memory High".to_string(),
            metric: "mem_usage".to_string(),
            op: ThresholdOp::GreaterThan,
            threshold: 90.0,
            severity: Severity::Critical,
            for_duration: Duration::ZERO,
        };
        let sink = InMemoryAlertSink::new();
        let eval = AlertEvaluator::new(
            vec![cpu_rule(), mem_rule],
            Arc::clone(&sink) as Arc<dyn AlertSink>,
        );

        eval.push(&sample("cpu_usage", 95.0)).unwrap(); // cpu fires
        eval.push(&sample("mem_usage", 95.0)).unwrap(); // mem fires
        eval.push(&sample("cpu_usage", 60.0)).unwrap(); // cpu resolves
                                                        // mem is still firing

        let firing_ids = eval.firing_rule_ids();
        assert!(firing_ids.contains(&"mem-high".to_string()));
        assert!(!firing_ids.contains(&"cpu-high".to_string()));
    }

    // ── AlertSink port object-safety ─────────────────────────────────────────

    #[test]
    fn alert_sink_is_object_safe() {
        let _: Arc<dyn AlertSink> = InMemoryAlertSink::new();
    }

    // ── AlertRule serde round-trip ───────────────────────────────────────────

    #[test]
    fn alert_rule_serde_roundtrip() {
        let rule = cpu_rule();
        let json = serde_json::to_string(&rule).unwrap();
        let decoded: AlertRule = serde_json::from_str(&json).unwrap();
        assert_eq!(decoded.id, rule.id);
        assert_eq!(decoded.metric, rule.metric);
        assert_eq!(decoded.threshold, rule.threshold);
        assert_eq!(decoded.severity, rule.severity);
        assert_eq!(decoded.for_duration, rule.for_duration);
    }

    // ── ThresholdOp: all operators ───────────────────────────────────────────

    #[test]
    fn threshold_op_greater_than() {
        assert!(ThresholdOp::GreaterThan.evaluate(5.0, 4.0));
        assert!(!ThresholdOp::GreaterThan.evaluate(4.0, 4.0));
        assert!(!ThresholdOp::GreaterThan.evaluate(3.0, 4.0));
    }

    #[test]
    fn threshold_op_greater_than_or_equal() {
        assert!(ThresholdOp::GreaterThanOrEqual.evaluate(4.0, 4.0));
        assert!(ThresholdOp::GreaterThanOrEqual.evaluate(5.0, 4.0));
        assert!(!ThresholdOp::GreaterThanOrEqual.evaluate(3.0, 4.0));
    }

    #[test]
    fn threshold_op_less_than() {
        assert!(ThresholdOp::LessThan.evaluate(3.0, 4.0));
        assert!(!ThresholdOp::LessThan.evaluate(4.0, 4.0));
    }

    #[test]
    fn threshold_op_less_than_or_equal() {
        assert!(ThresholdOp::LessThanOrEqual.evaluate(4.0, 4.0));
        assert!(ThresholdOp::LessThanOrEqual.evaluate(3.0, 4.0));
        assert!(!ThresholdOp::LessThanOrEqual.evaluate(5.0, 4.0));
    }

    #[test]
    fn threshold_op_equal() {
        assert!(ThresholdOp::Equal.evaluate(4.0, 4.0));
        assert!(!ThresholdOp::Equal.evaluate(4.1, 4.0));
    }
}
