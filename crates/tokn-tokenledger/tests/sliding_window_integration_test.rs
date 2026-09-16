use chrono::{Duration, TimeZone, Utc};
use std::collections::BTreeMap;
use tokenledger::analytics::build_sliding_window_metrics;
use tokenledger::models::{TokenUsage, UsageEvent};

fn event(provider: &str, session: &str, timestamp_offset_minutes: i64, tokens: u64) -> UsageEvent {
    UsageEvent {
        provider: provider.to_string(),
        model: "model-a".to_string(),
        session_id: session.to_string(),
        timestamp: Utc.with_ymd_and_hms(2026, 7, 18, 12, 0, 0).unwrap()
            + Duration::minutes(timestamp_offset_minutes),
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
fn trailing_windows_use_exclusive_start_and_inclusive_end() {
    let end = Utc.with_ymd_and_hms(2026, 7, 18, 12, 0, 0).unwrap();
    let metrics = build_sliding_window_metrics(
        &[
            event("claude", "session-5m", -4, 100),
            event("codex", "session-1h", -30, 200),
            event("claude", "session-24h", -120, 300),
            event("droid", "outside", -1_500, 400),
        ],
        end,
    );

    assert_eq!(metrics.len(), 3);
    assert_eq!(metrics[0].window, "5m");
    assert_eq!(metrics[0].event_count, 1);
    assert_eq!(metrics[0].session_count, 1);
    assert_eq!(metrics[0].tokens, 100);
    assert_eq!(
        metrics[0].tokens_by_provider,
        BTreeMap::from([(String::from("claude"), 100)])
    );

    assert_eq!(metrics[1].window, "1h");
    assert_eq!(metrics[1].event_count, 2);
    assert_eq!(metrics[1].tokens, 300);

    assert_eq!(metrics[2].window, "24h");
    assert_eq!(metrics[2].event_count, 3);
    assert_eq!(metrics[2].tokens, 600);
}
