use std::path::Path;
use tokenledger::cli::IngestProvider;
use tokenledger::ingest::normalize_ingest_record;

#[test]
fn droid_session_usage_normalizes_to_event_contract() {
    let value = serde_json::json!({
        "session": {
            "id": "droid-session-1",
            "agent_model": "factory-droid-latest",
            "started_at": "2026-07-18T12:00:00Z",
            "metrics": {
                "tokens": {
                    "user": 900,
                    "assistant": 350
                },
                "cache": {"create": 40, "read": 120},
                "tools": {"input": 60, "output": 20}
            }
        }
    });

    let event = normalize_ingest_record(
        IngestProvider::Droid,
        Path::new("/tmp/droid-session.jsonl"),
        &value,
    )
    .expect("Droid usage record should normalize");

    assert_eq!(event.provider, "droid");
    assert_eq!(event.model, "factory-droid-latest");
    assert_eq!(event.session_id, "droid-session-1");
    assert_eq!(event.timestamp.to_rfc3339(), "2026-07-18T12:00:00+00:00");
    assert_eq!(event.usage.input_tokens, 900);
    assert_eq!(event.usage.output_tokens, 350);
    assert_eq!(event.usage.cache_write_tokens, 40);
    assert_eq!(event.usage.cache_read_tokens, 120);
    assert_eq!(event.usage.tool_input_tokens, 60);
    assert_eq!(event.usage.tool_output_tokens, 20);
    assert_eq!(event.usage.total(), 1_490);
    assert_eq!(event.tenant_id, None);
}
