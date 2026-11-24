//! Alert rule definitions and stub evaluator.

use serde::{Deserialize, Serialize};

/// Severity level of an alert.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    Info,
    Warning,
    Critical,
}

/// Condition operator for threshold comparisons.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum Operator {
    GreaterThan,
    LessThan,
    Equal,
}

/// A single alert rule definition.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertRule {
    pub id: String,
    pub name: String,
    pub query: String,
    pub threshold: f64,
    pub operator: Operator,
    pub severity: Severity,
}

impl AlertRule {
    pub fn new(
        id: impl Into<String>,
        name: impl Into<String>,
        query: impl Into<String>,
        threshold: f64,
        operator: Operator,
        severity: Severity,
    ) -> Self {
        Self {
            id: id.into(),
            name: name.into(),
            query: query.into(),
            threshold,
            operator,
            severity,
        }
    }

    /// Evaluate the rule against a sample value.
    pub fn evaluate(&self, value: f64) -> bool {
        match self.operator {
            Operator::GreaterThan => value > self.threshold,
            Operator::LessThan => value < self.threshold,
            Operator::Equal => (value - self.threshold).abs() < f64::EPSILON,
        }
    }
}

/// A fired alert instance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub rule_id: String,
    pub severity: Severity,
    pub value: f64,
    pub message: String,
}

/// Evaluate a set of rules against sample values and return fired alerts.
pub fn evaluate_rules(rules: &[AlertRule], values: &[(String, f64)]) -> Vec<Alert> {
    let mut alerts = Vec::new();
    for rule in rules {
        if let Some((_, value)) = values.iter().find(|(id, _)| id == &rule.id) {
            if rule.evaluate(*value) {
                alerts.push(Alert {
                    rule_id: rule.id.clone(),
                    severity: rule.severity,
                    value: *value,
                    message: format!(
                        "{}: value {:.2} {} threshold {:.2}",
                        rule.name,
                        value,
                        match rule.operator {
                            Operator::GreaterThan => ">",
                            Operator::LessThan => "<",
                            Operator::Equal => "==",
                        },
                        rule.threshold
                    ),
                });
            }
        }
    }
    alerts
}

/// Default alert rules for PhenoObservability.
pub fn default_rules() -> Vec<AlertRule> {
    vec![
        AlertRule::new(
            "error-rate",
            "High Error Rate",
            "rate(errors_total[5m])",
            0.05,
            Operator::GreaterThan,
            Severity::Critical,
        ),
        AlertRule::new(
            "p99-latency",
            "P99 Latency",
            "histogram_quantile(0.99, latency_ms)",
            1000.0,
            Operator::GreaterThan,
            Severity::Warning,
        ),
        AlertRule::new(
            "span-rate-low",
            "Low Span Rate",
            "rate(spans_total[1m])",
            1.0,
            Operator::LessThan,
            Severity::Info,
        ),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evaluate_greater_than_fires() {
        let rule = AlertRule::new(
            "r1",
            "Test",
            "q",
            10.0,
            Operator::GreaterThan,
            Severity::Warning,
        );
        assert!(rule.evaluate(11.0));
        assert!(!rule.evaluate(9.0));
        assert!(!rule.evaluate(10.0));
    }

    #[test]
    fn evaluate_less_than_fires() {
        let rule = AlertRule::new("r2", "Test", "q", 5.0, Operator::LessThan, Severity::Info);
        assert!(rule.evaluate(4.0));
        assert!(!rule.evaluate(6.0));
    }

    #[test]
    fn evaluate_rules_returns_fired() {
        let rules = default_rules();
        let values = vec![
            ("error-rate".to_string(), 0.1),    // > 0.05 → fires
            ("p99-latency".to_string(), 500.0), // < 1000 → no fire
        ];
        let alerts = evaluate_rules(&rules, &values);
        assert_eq!(alerts.len(), 1);
        assert_eq!(alerts[0].rule_id, "error-rate");
        assert_eq!(alerts[0].severity, Severity::Critical);
    }

    #[test]
    fn severity_ordering() {
        assert!(Severity::Critical > Severity::Warning);
        assert!(Severity::Warning > Severity::Info);
    }
}
