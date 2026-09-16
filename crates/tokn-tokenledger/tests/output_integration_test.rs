use chrono::Utc;
use std::collections::HashMap;
use tokenledger::cli::OnUnpricedAction;
use tokenledger::cost::compute_costs;
use tokenledger::models::{ModelRate, PricingBook, ProviderPricing, TokenUsage, UsageEvent};

#[test]
fn cost_report_json_and_suggestions_are_stable() {
    let mut models = HashMap::new();
    models.insert(
        "model-a".to_string(),
        ModelRate {
            input_usd_per_mtok: 20.0,
            output_usd_per_mtok: 20.0,
            cache_write_usd_per_mtok: None,
            cache_read_usd_per_mtok: None,
            tool_input_usd_per_mtok: Some(20.0),
            tool_output_usd_per_mtok: Some(20.0),
        },
    );

    let mut providers = HashMap::new();
    providers.insert(
        "provider-a".to_string(),
        ProviderPricing {
            subscription_usd_month: 0.0,
            models,
            model_aliases: HashMap::new(),
        },
    );

    let report = compute_costs(
        &[UsageEvent {
            provider: "provider-a".to_string(),
            model: "model-a".to_string(),
            session_id: "session-1".to_string(),
            timestamp: Utc::now(),
            tenant_id: None,
            usage: TokenUsage {
                input_tokens: 100_000,
                output_tokens: 0,
                cache_write_tokens: 0,
                cache_read_tokens: 0,
                tool_input_tokens: 300_000,
                tool_output_tokens: 300_000,
            },
        }],
        &PricingBook {
            providers,
            provider_aliases: HashMap::new(),
            meta: None,
        },
        OnUnpricedAction::Error,
    )
    .expect("priced event should produce a report");

    let json = serde_json::to_value(&report).expect("cost report should serialize as JSON");
    assert_eq!(json["total_tokens"], 700_000);
    assert_eq!(json["provider_breakdown"][0]["name"], "provider-a");
    assert!(
        report
            .suggestions
            .iter()
            .any(|tip| tip.contains("Tool-token share is high"))
    );
    assert!(
        report
            .suggestions
            .iter()
            .any(|tip| tip.contains("Blended variable $/MTok is high"))
    );
}
