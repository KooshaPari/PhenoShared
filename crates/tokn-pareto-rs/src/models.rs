//! ParetoRs — pure data types shared by cost + pricing + format engines.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

// ─── Core Pricing Models ──────────────────────────────────────────────────────

/// Provider identifier (e.g. "openai/gpt-4o", "anthropic/claude-3-5-sonnet")
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ProviderKey(pub String);

/// Raw input/output token counts per model call
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct TokenCounts {
    pub input: u64,
    pub output: u64,
}

/// Output token cost per million tokens
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PricingRate {
    pub input_per_m: f64,
    pub output_per_m: f64,
    pub use_default: bool,
}

/// Per-model pricing configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelPricing {
    pub provider: String,
    pub model: String,
    pub input_per_m: f64,
    pub output_per_m: f64,
}

/// Provider-level price list
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderPrices {
    pub provider: String,
    pub models: Vec<ModelPricing>,
    pub updated_at: DateTime<Utc>,
}

// ─── Routing ─────────────────────────────────────────────────────────────────

/// Provider harness metrics used for routing decisions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderHarness {
    pub provider: String,
    pub model: String,
    pub input_cost: f64,
    pub output_cost: f64,
    pub p50_latency_ms: Option<f64>,
    pub p95_latency_ms: Option<f64>,
    pub success_rate: f64,
}

/// Routing criteria — what matters for a given request
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize, Default)]
pub enum RoutingCriteria {
    Cost,
    Latency,
    #[default]
    Balanced,
}

impl std::fmt::Display for RoutingCriteria {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RoutingCriteria::Cost => write!(f, "cost"),
            RoutingCriteria::Latency => write!(f, "latency"),
            RoutingCriteria::Balanced => write!(f, "balanced"),
        }
    }
}

// ─── Audit ───────────────────────────────────────────────────────────────────

/// How to handle unpriced models
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default, clap::ValueEnum)]
pub enum OnUnpricedAction {
    Skip,
    Error,
    #[default]
    Warn,
}

/// What to do when a provider returns no cost data
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MissingCostStrategy {
    #[default]
    Skip,
    UseProviderDefault,
    BestEffort,
}

/// Pricing audit result for a single call
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PricingAudit {
    pub provider: String,
    pub model: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub input_cost: f64,
    pub output_cost: f64,
    pub total_cost: f64,
    pub latency_ms: Option<f64>,
    pub timestamp: DateTime<Utc>,
    pub provider_price_per_m: Option<ModelPricing>,
}

/// Pricing lint finding
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PricingLint {
    pub severity: LintSeverity,
    pub provider: String,
    pub model: String,
    pub message: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LintSeverity {
    Error,
    Warn,
    Info,
}

// ─── Ledger / Cost Snapshot ───────────────────────────────────────────────────

/// Snapshot of costs for one call record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostSnapshot {
    pub id: String,
    pub provider: String,
    pub model: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub input_cost: f64,
    pub output_cost: f64,
    pub total_cost: f64,
    pub latency_ms: Option<f64>,
    pub timestamp: DateTime<Utc>,
    pub routing_criteria: Option<String>,
    pub routing_score: Option<f64>,
}

/// Aggregated cost across all calls
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostAggregate {
    pub total_input_tokens: u64,
    pub total_output_tokens: u64,
    pub total_input_cost: f64,
    pub total_output_cost: f64,
    pub total_cost: f64,
    pub call_count: usize,
}

/// Per-provider aggregation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderCostAggregate {
    pub provider: String,
    pub total_input_tokens: u64,
    pub total_output_tokens: u64,
    pub total_input_cost: f64,
    pub total_output_cost: f64,
    pub total_cost: f64,
    pub call_count: usize,
    pub avg_latency_ms: Option<f64>,
}

// ─── Format ─────────────────────────────────────────────────────────────────

/// Output format for pricing commands
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum OutputFormat {
    #[default]
    Table,
    Json,
    Csv,
    Markdown,
}

impl std::fmt::Display for OutputFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            OutputFormat::Table => write!(f, "table"),
            OutputFormat::Json => write!(f, "json"),
            OutputFormat::Csv => write!(f, "csv"),
            OutputFormat::Markdown => write!(f, "markdown"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_provider_key_equality() {
        let a = ProviderKey("openai/gpt-4o".to_string());
        let b = ProviderKey("openai/gpt-4o".to_string());
        let c = ProviderKey("anthropic/claude-3".to_string());
        assert_eq!(a, b);
        assert_ne!(a, c);
    }

    #[test]
    fn test_token_counts_default() {
        let tc = TokenCounts {
            input: 0,
            output: 0,
        };
        assert_eq!(tc.input, 0);
        assert_eq!(tc.output, 0);
    }

    #[test]
    fn test_pricing_rate_default() {
        let rate = PricingRate {
            input_per_m: 2.5,
            output_per_m: 10.0,
            use_default: false,
        };
        assert_eq!(rate.input_per_m, 2.5);
        assert_eq!(rate.output_per_m, 10.0);
        assert!(!rate.use_default);
    }

    #[test]
    fn test_model_pricing_clone() {
        let mp = ModelPricing {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        };
        let cloned = mp.clone();
        assert_eq!(mp.provider, cloned.provider);
        assert_eq!(mp.model, cloned.model);
        assert_eq!(mp.input_per_m, cloned.input_per_m);
        assert_eq!(mp.output_per_m, cloned.output_per_m);
    }

    #[test]
    fn test_routing_criteria_display() {
        assert_eq!(RoutingCriteria::Cost.to_string(), "cost");
        assert_eq!(RoutingCriteria::Latency.to_string(), "latency");
        assert_eq!(RoutingCriteria::Balanced.to_string(), "balanced");
    }

    #[test]
    fn test_routing_criteria_default() {
        let criteria: RoutingCriteria = Default::default();
        assert_eq!(criteria, RoutingCriteria::Balanced);
    }

    #[test]
    fn test_on_unpriced_action_default() {
        let action: OnUnpricedAction = Default::default();
        assert_eq!(action, OnUnpricedAction::Warn);
    }

    #[test]
    fn test_on_unpriced_action_variants() {
        assert_eq!(OnUnpricedAction::Skip, OnUnpricedAction::Skip);
        assert_eq!(OnUnpricedAction::Error, OnUnpricedAction::Error);
        assert_ne!(OnUnpricedAction::Skip, OnUnpricedAction::Error);
    }

    #[test]
    fn test_missing_cost_strategy_default() {
        let strategy: MissingCostStrategy = Default::default();
        assert_eq!(strategy, MissingCostStrategy::Skip);
    }

    #[test]
    fn test_lint_severity_equality() {
        assert_eq!(LintSeverity::Error, LintSeverity::Error);
        assert_eq!(LintSeverity::Warn, LintSeverity::Warn);
        assert_eq!(LintSeverity::Info, LintSeverity::Info);
        assert_ne!(LintSeverity::Error, LintSeverity::Warn);
    }

    #[test]
    fn test_cost_snapshot_creation() {
        let snapshot = CostSnapshot {
            id: "test-1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1000,
            output_tokens: 500,
            input_cost: 0.0025,
            output_cost: 0.005,
            total_cost: 0.0075,
            latency_ms: Some(150.0),
            timestamp: Utc::now(),
            routing_criteria: Some("cost".to_string()),
            routing_score: Some(0.95),
        };
        assert_eq!(snapshot.id, "test-1");
        assert_eq!(snapshot.provider, "openai");
        assert_eq!(snapshot.input_tokens, 1000);
        assert_eq!(snapshot.latency_ms, Some(150.0));
    }

    #[test]
    fn test_cost_aggregate_default() {
        let agg = CostAggregate {
            total_input_tokens: 0,
            total_output_tokens: 0,
            total_input_cost: 0.0,
            total_output_cost: 0.0,
            total_cost: 0.0,
            call_count: 0,
        };
        assert_eq!(agg.call_count, 0);
        assert_eq!(agg.total_cost, 0.0);
    }

    #[test]
    fn test_provider_cost_aggregate_creation() {
        let pca = ProviderCostAggregate {
            provider: "openai".to_string(),
            total_input_tokens: 1000,
            total_output_tokens: 500,
            total_input_cost: 0.0025,
            total_output_cost: 0.005,
            total_cost: 0.0075,
            call_count: 1,
            avg_latency_ms: Some(150.0),
        };
        assert_eq!(pca.provider, "openai");
        assert_eq!(pca.call_count, 1);
        assert_eq!(pca.avg_latency_ms, Some(150.0));
    }

    #[test]
    fn test_output_format_display() {
        assert_eq!(OutputFormat::Table.to_string(), "table");
        assert_eq!(OutputFormat::Json.to_string(), "json");
        assert_eq!(OutputFormat::Csv.to_string(), "csv");
        assert_eq!(OutputFormat::Markdown.to_string(), "markdown");
    }

    #[test]
    fn test_output_format_default() {
        let format: OutputFormat = Default::default();
        assert_eq!(format, OutputFormat::Table);
    }

    #[test]
    fn test_provider_harness_creation() {
        let harness = ProviderHarness {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_cost: 0.0025,
            output_cost: 0.01,
            p50_latency_ms: Some(100.0),
            p95_latency_ms: Some(200.0),
            success_rate: 0.99,
        };
        assert_eq!(harness.provider, "openai");
        assert_eq!(harness.success_rate, 0.99);
    }

    #[test]
    fn test_pricing_audit_creation() {
        let audit = PricingAudit {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1000,
            output_tokens: 500,
            input_cost: 0.0025,
            output_cost: 0.005,
            total_cost: 0.0075,
            latency_ms: Some(150.0),
            timestamp: Utc::now(),
            provider_price_per_m: None,
        };
        assert_eq!(audit.provider, "openai");
        assert_eq!(audit.total_cost, 0.0075);
    }

    #[test]
    fn test_pricing_lint_creation() {
        let lint = PricingLint {
            severity: LintSeverity::Warn,
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            message: "price changed".to_string(),
        };
        assert_eq!(lint.severity, LintSeverity::Warn);
        assert_eq!(lint.message, "price changed");
    }

    #[test]
    fn test_serde_roundtrip_model_pricing() {
        let mp = ModelPricing {
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_per_m: 2.5,
            output_per_m: 10.0,
        };
        let json = serde_json::to_string(&mp).unwrap();
        let decoded: ModelPricing = serde_json::from_str(&json).unwrap();
        assert_eq!(mp.provider, decoded.provider);
        assert_eq!(mp.model, decoded.model);
        assert_eq!(mp.input_per_m, decoded.input_per_m);
        assert_eq!(mp.output_per_m, decoded.output_per_m);
    }

    #[test]
    fn test_serde_roundtrip_cost_snapshot() {
        let now = Utc::now();
        let cs = CostSnapshot {
            id: "snap-1".to_string(),
            provider: "openai".to_string(),
            model: "gpt-4o".to_string(),
            input_tokens: 1000,
            output_tokens: 500,
            input_cost: 0.0025,
            output_cost: 0.005,
            total_cost: 0.0075,
            latency_ms: Some(150.0),
            timestamp: now,
            routing_criteria: Some("cost".to_string()),
            routing_score: Some(0.95),
        };
        let json = serde_json::to_string(&cs).unwrap();
        let decoded: CostSnapshot = serde_json::from_str(&json).unwrap();
        assert_eq!(cs.id, decoded.id);
        assert_eq!(cs.provider, decoded.provider);
        assert_eq!(cs.total_cost, decoded.total_cost);
        assert_eq!(cs.latency_ms, decoded.latency_ms);
    }
}
