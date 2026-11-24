use chrono::Utc;
use std::collections::HashMap;
use tokenledger::cli::OnUnpricedAction;
use tokenledger::cost::compute_costs;
use tokenledger::models::{ModelRate, PricingBook, ProviderPricing, TokenUsage, UsageEvent};

#[test]
fn monthly_aggregation_blends_variable_and_subscription_costs() {
    let mut models = HashMap::new();
    models.insert(
        "model-a".to_string(),
        ModelRate {
            input_usd_per_mtok: 1.0,
            output_usd_per_mtok: 2.0,
            cache_write_usd_per_mtok: None,
            cache_read_usd_per_mtok: None,
            tool_input_usd_per_mtok: None,
            tool_output_usd_per_mtok: None,
        },
    );

    let mut providers = HashMap::new();
    providers.insert(
        "provider-a".to_string(),
        ProviderPricing {
            subscription_usd_month: 30.0,
            models,
            model_aliases: HashMap::new(),
        },
    );

    let report = compute_costs(
        &[
            UsageEvent {
                provider: "provider-a".to_string(),
                model: "model-a".to_string(),
                session_id: "session-1".to_string(),
                timestamp: Utc::now(),
                tenant_id: None,
                usage: TokenUsage {
                    input_tokens: 1_000_000,
                    output_tokens: 1_000_000,
                    cache_write_tokens: 0,
                    cache_read_tokens: 0,
                    tool_input_tokens: 0,
                    tool_output_tokens: 0,
                },
            },
            UsageEvent {
                provider: "provider-a".to_string(),
                model: "model-a".to_string(),
                session_id: "session-2".to_string(),
                timestamp: Utc::now(),
                tenant_id: None,
                usage: TokenUsage {
                    input_tokens: 2_000_000,
                    output_tokens: 0,
                    cache_write_tokens: 0,
                    cache_read_tokens: 0,
                    tool_input_tokens: 0,
                    tool_output_tokens: 0,
                },
            },
        ],
        &PricingBook {
            providers,
            provider_aliases: HashMap::new(),
            meta: None,
        },
        OnUnpricedAction::Error,
    )
    .expect("priced monthly events should aggregate");

    assert_eq!(report.total_tokens, 4_000_000);
    assert_eq!(report.variable_cost_usd, 5.0);
    assert_eq!(report.subscription_allocated_usd, 30.0);
    assert_eq!(report.monthly_total_usd, 35.0);
    assert_eq!(report.blended_usd_per_mtok, 8.75);
    assert_eq!(report.session_count, 2);
    assert_eq!(report.skipped_unpriced_count, 0);
}
