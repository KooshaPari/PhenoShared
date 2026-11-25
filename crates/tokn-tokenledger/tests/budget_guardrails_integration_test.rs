use chrono::{Duration, TimeZone, Utc};
use tokenledger::analytics::SlidingWindow;
use tokenledger::guardrails::{BudgetLimit, evaluate_budget_guardrails};
use tokenledger::models::{TokenUsage, UsageEvent};

fn event(provider: &str, model: &str, tokens: u64, minutes_ago: i64) -> UsageEvent {
    UsageEvent {
        provider: provider.to_string(),
        model: model.to_string(),
        session_id: format!("{provider}-{model}"),
        timestamp: Utc.with_ymd_and_hms(2026, 7, 18, 12, 0, 0).unwrap()
            - Duration::minutes(minutes_ago),
        tenant_id: None,
        usage: TokenUsage {
            input_tokens: tokens,
            output_tokens: 0,
            cache_write_tokens: 0,
            cache_read_tokens: 0,
            tool_input_tokens: 0,
            tool_output_tokens: 0,
        },
    }
}

#[test]
fn budget_guardrails_report_provider_and_model_breaches() {
    let end = Utc.with_ymd_and_hms(2026, 7, 18, 12, 0, 0).unwrap();
    let events = [
        event("claude", "sonnet", 900, 2),
        event("claude", "haiku", 300, 10),
        event("codex", "gpt-5", 700, 20),
    ];
    let limits = [
        BudgetLimit {
            provider: Some("claude".to_string()),
            model: None,
            window: SlidingWindow::OneHour,
            max_tokens: 1_000,
        },
        BudgetLimit {
            provider: Some("claude".to_string()),
            model: Some("sonnet".to_string()),
            window: SlidingWindow::OneHour,
            max_tokens: 500,
        },
        BudgetLimit {
            provider: Some("codex".to_string()),
            model: None,
            window: SlidingWindow::OneHour,
            max_tokens: 1_000,
        },
    ];

    let alerts = evaluate_budget_guardrails(&events, end, &limits);

    assert_eq!(alerts.len(), 2);
    assert_eq!(alerts[0].provider.as_deref(), Some("claude"));
    assert_eq!(alerts[0].model, None);
    assert_eq!(alerts[0].observed_tokens, 1_200);
    assert_eq!(alerts[0].max_tokens, 1_000);
    assert_eq!(alerts[0].window, "1h");
    assert_eq!(alerts[1].model.as_deref(), Some("sonnet"));
    assert_eq!(alerts[1].observed_tokens, 900);
    assert!((alerts[1].utilization - 1.8).abs() < f64::EPSILON);
}
