use std::path::Path;
use tokenledger::cli::IngestProvider;
use tokenledger::ingest::normalize_ingest_record;

#[test]
fn codex_response_usage_normalizes_to_event_contract() {
    let value = serde_json::json!({
        "response": {
            "model": "gpt-5",
            "session_id": "codex-session-1",
            "created_at": "2026-07-18T11:00:00Z",
            "usage": {
                "prompt_tokens": 2_000,
                "completion_tokens": 500,
                "prompt_tokens_details": {
                    "cached_tokens": 300,
                    "cached_write_tokens": 100
                }
            }
        }
    });

    let event = normalize_ingest_record(
        IngestProvider::Codex,
        Path::new("/tmp/codex-session.jsonl"),
        &value,
    )
    .expect("Codex usage record should normalize");

    assert_eq!(event.provider, "codex");
    assert_eq!(event.model, "gpt-5");
    assert_eq!(event.session_id, "codex-session-1");
    assert_eq!(event.timestamp.to_rfc3339(), "2026-07-18T11:00:00+00:00");
    assert_eq!(event.usage.input_tokens, 2_000);
    assert_eq!(event.usage.output_tokens, 500);
    assert_eq!(event.usage.cache_read_tokens, 300);
    assert_eq!(event.usage.cache_write_tokens, 100);
    assert_eq!(event.usage.total(), 2_900);
    assert_eq!(event.tenant_id, None);
}
