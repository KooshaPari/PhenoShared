use std::path::Path;
use tokenledger::cli::IngestProvider;
use tokenledger::ingest::normalize_ingest_record;

#[test]
fn claude_message_usage_normalizes_to_event_contract() {
    let value = serde_json::json!({
        "message": {
            "model": "claude-sonnet-4-5",
            "session_id": "claude-session-1",
            "created_at": "2026-07-18T10:00:00Z",
            "usage": {
                "input_tokens": 1_000,
                "output_tokens": 250,
                "cache_creation_input_tokens": 400,
                "cache_read_input_tokens": 100,
                "tool_input_tokens": 50,
                "tool_output_tokens": 25
            }
        }
    });

    let event = normalize_ingest_record(
        IngestProvider::Claude,
        Path::new("/tmp/claude-session.jsonl"),
        &value,
    )
    .expect("Claude usage record should normalize");

    assert_eq!(event.provider, "claude");
    assert_eq!(event.model, "claude-sonnet-4-5");
    assert_eq!(event.session_id, "claude-session-1");
    assert_eq!(event.timestamp.to_rfc3339(), "2026-07-18T10:00:00+00:00");
    assert_eq!(event.usage.input_tokens, 1_000);
    assert_eq!(event.usage.output_tokens, 250);
    assert_eq!(event.usage.cache_write_tokens, 400);
    assert_eq!(event.usage.cache_read_tokens, 100);
    assert_eq!(event.usage.tool_input_tokens, 50);
    assert_eq!(event.usage.tool_output_tokens, 25);
    assert_eq!(event.usage.total(), 1_825);
    assert_eq!(event.tenant_id, None);
}
