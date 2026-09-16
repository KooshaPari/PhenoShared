use std::path::Path;
use tokenledger::cli::IngestProvider;
use tokenledger::ingest::normalize_ingest_record;

#[test]
fn cursor_record_usage_normalizes_to_event_contract() {
    let value = serde_json::json!({
        "record": {
            "agent": {"model": "cursor-codex-latest"},
            "workspace_id": "cursor-workspace-1",
            "timestamp_ms": 1784372400000_u64,
            "tokens": {
                "prompt": 1_000,
                "completion": 400,
                "cache": {"read": 200, "write": 50},
                "tooling": {"input": 75, "output": 25}
            }
        }
    });

    let event = normalize_ingest_record(
        IngestProvider::Cursor,
        Path::new("/tmp/cursor-usage.jsonl"),
        &value,
    )
    .expect("Cursor usage record should normalize");

    assert_eq!(event.provider, "cursor");
    assert_eq!(event.model, "cursor-codex-latest");
    assert_eq!(event.session_id, "cursor-workspace-1");
    assert_eq!(event.timestamp.to_rfc3339(), "2026-07-18T11:00:00+00:00");
    assert_eq!(event.usage.input_tokens, 1_000);
    assert_eq!(event.usage.output_tokens, 400);
    assert_eq!(event.usage.cache_read_tokens, 200);
    assert_eq!(event.usage.cache_write_tokens, 50);
    assert_eq!(event.usage.tool_input_tokens, 75);
    assert_eq!(event.usage.tool_output_tokens, 25);
    assert_eq!(event.usage.total(), 1_750);
    assert_eq!(event.tenant_id, None);
}
