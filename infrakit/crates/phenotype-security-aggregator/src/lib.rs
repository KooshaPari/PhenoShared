//! Security Alert Aggregation

use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AlertSeverity {
    Critical,
    High,
    Medium,
    Low,
    Info,
}

impl AlertSeverity {
    pub fn score(&self) -> f32 {
        match self {
            AlertSeverity::Critical => 100.0,
            AlertSeverity::High => 75.0,
            AlertSeverity::Medium => 50.0,
            AlertSeverity::Low => 25.0,
            AlertSeverity::Info => 10.0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct SecurityAlert {
    pub id: String,
    pub severity: AlertSeverity,
    pub title: String,
    pub repository: String,
    pub created_at: DateTime<Utc>,
}

impl SecurityAlert {
    pub fn new(
        id: String,
        severity: AlertSeverity,
        title: String,
        repository: String,
    ) -> Self {
        Self {
            id,
            severity,
            title,
            repository,
            created_at: Utc::now(),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct SecurityAggregator {
    total_alerts: usize,
    severity_counts: [usize; 5], // Critical, High, Medium, Low, Info
}

impl SecurityAggregator {
    pub fn new() -> Self {
        Self::default()
    }

    fn severity_index(severity: &AlertSeverity) -> usize {
        match severity {
            AlertSeverity::Critical => 0,
            AlertSeverity::High => 1,
            AlertSeverity::Medium => 2,
            AlertSeverity::Low => 3,
            AlertSeverity::Info => 4,
        }
    }

    /// Add an alert with the given severity.
    pub fn add_alert_with_severity(&mut self, severity: AlertSeverity) {
        self.total_alerts += 1;
        self.severity_counts[Self::severity_index(&severity)] += 1;
    }

    /// Add a critical alert (convenience method).
    pub fn add_critical(&mut self) {
        self.add_alert_with_severity(AlertSeverity::Critical);
    }

    /// Add a non-critical alert (convenience method, defaults to Medium).
    pub fn add_alert(&mut self) {
        self.add_alert_with_severity(AlertSeverity::Medium);
    }

    /// Calculate a health score from 0.0 (worst) to 100.0 (best).
    ///
    /// All severity levels contribute to the score: critical alerts are the
    /// heaviest penalty, but high, medium, low, and info alerts also reduce
    /// the score proportionally.
    pub fn calculate_score(&self) -> f32 {
        let weights = [10.0, 5.0, 2.0, 1.0, 0.5];
        let penalty: f32 = self
            .severity_counts
            .iter()
            .zip(weights.iter())
            .map(|(count, weight)| *count as f32 * weight)
            .sum();
        (100.0 - penalty).max(0.0).min(100.0)
    }

    pub fn total(&self) -> usize {
        self.total_alerts
    }

    /// Get count for a specific severity level.
    pub fn count_by_severity(&self, severity: AlertSeverity) -> usize {
        self.severity_counts[Self::severity_index(&severity)]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_aggregator() {
        let agg = SecurityAggregator::new();
        assert_eq!(agg.calculate_score(), 100.0);
        assert_eq!(agg.total(), 0);
    }

    #[test]
    fn test_critical_penalty() {
        let mut agg = SecurityAggregator::new();
        agg.add_critical();
        assert_eq!(agg.calculate_score(), 90.0);
    }

    #[test]
    fn test_all_severities() {
        let mut agg = SecurityAggregator::new();
        agg.add_alert_with_severity(AlertSeverity::Critical);
        agg.add_alert_with_severity(AlertSeverity::High);
        agg.add_alert_with_severity(AlertSeverity::Medium);
        agg.add_alert_with_severity(AlertSeverity::Low);
        agg.add_alert_with_severity(AlertSeverity::Info);
        // Penalty: 10 + 5 + 2 + 1 + 0.5 = 18.5
        assert_eq!(agg.calculate_score(), 81.5);
        assert_eq!(agg.total(), 5);
    }

    #[test]
    fn test_score_floor() {
        let mut agg = SecurityAggregator::new();
        for _ in 0..20 {
            agg.add_critical();
        }
        assert_eq!(agg.calculate_score(), 0.0);
    }
}
