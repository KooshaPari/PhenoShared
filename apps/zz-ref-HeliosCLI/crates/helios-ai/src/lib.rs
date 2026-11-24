//! OpenAI-compatible AI client for helios-cli.
//!
//! Supports OpenAI, Anthropic (via compatible proxy), Ollama, LM Studio,
//! vLLM, and any OpenAI-compatible API endpoint.

pub mod client;
pub mod cost;
pub mod persistence;
pub mod session;
pub mod sse;
pub mod types;

pub use client::AiClient;
pub use cost::CostTracker;
pub use persistence::*;
pub use session::ChatSession;
pub use sse::{parse_sse_line, SseEvent};
pub use types::*;

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn provider_config_openai() {
        let config = ProviderConfig::openai("sk-test", "gpt-4o");
        assert_eq!(config.base_url, "https://api.openai.com/v1");
        assert_eq!(config.api_key, "sk-test");
        assert_eq!(config.model, "gpt-4o");
        assert_eq!(config.timeout_secs, 120);
    }

    #[test]
    fn provider_config_ollama() {
        let config = ProviderConfig::ollama("llama3");
        assert_eq!(config.base_url, "http://localhost:11434/v1");
        assert!(config.api_key.is_empty());
        assert_eq!(config.model, "llama3");
        assert_eq!(config.timeout_secs, 300);
    }

    #[test]
    fn provider_config_lm_studio() {
        let config = ProviderConfig::lm_studio("local-model");
        assert_eq!(config.base_url, "http://localhost:1234/v1");
    }

    #[test]
    fn message_constructors() {
        let m = Message::user("hello");
        assert_eq!(m.role, "user");
        assert_eq!(m.content, "hello");

        let m = Message::assistant("hi");
        assert_eq!(m.role, "assistant");

        let m = Message::system("you are helpful");
        assert_eq!(m.role, "system");
    }

    #[test]
    fn message_serialization_roundtrip() {
        let msg = Message::user("test message");
        let json = serde_json::to_string(&msg).unwrap();
        let deserialized: Message = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.role, "user");
        assert_eq!(deserialized.content, "test message");
    }

    #[test]
    fn chat_request_serialization() {
        let req = ChatRequest {
            model: "gpt-4o".into(),
            messages: vec![Message::user("hi")],
            max_tokens: Some(100),
            temperature: Some(0.7),
            stream: false,
        };
        let json = serde_json::to_value(&req).unwrap();
        assert_eq!(json["model"], "gpt-4o");
        assert_eq!(json["stream"], false);
        assert_eq!(json["max_tokens"], 100);
        assert!(json["temperature"].is_number());
    }

    #[test]
    fn chat_response_deserialization() {
        let json = r#"{
            "choices": [{
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }"#;
        let resp: ChatResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.choices.len(), 1);
        assert_eq!(resp.choices[0].message.content, "Hello!");
        assert_eq!(resp.choices[0].finish_reason.as_deref(), Some("stop"));
        let usage = resp.usage.unwrap();
        assert_eq!(usage.total_tokens, 15);
    }

    #[test]
    fn stream_chunk_deserialization() {
        let json = r#"{
            "choices": [{
                "delta": {"content": "Hello"},
                "finish_reason": null
            }]
        }"#;
        let chunk: StreamChunk = serde_json::from_str(json).unwrap();
        assert_eq!(chunk.choices[0].delta.as_ref().unwrap().content.as_deref(), Some("Hello"));
    }

    #[test]
    fn ai_client_creation() {
        let config = ProviderConfig::ollama("test");
        let client = AiClient::new(config).unwrap();
        assert_eq!(client.config().model, "test");
    }

    #[test]
    fn chat_session_new_with_system() {
        let config = ProviderConfig::ollama("test");
        let session = ChatSession::new(config, Some("You are helpful")).unwrap();
        assert_eq!(session.history().len(), 1);
        assert_eq!(session.history()[0].role, "system");
    }

    #[test]
    fn chat_session_new_without_system() {
        let config = ProviderConfig::ollama("test");
        let session = ChatSession::new(config, None).unwrap();
        assert!(session.history().is_empty());
    }

    #[test]
    fn chat_session_clear_preserves_system() {
        let config = ProviderConfig::ollama("test");
        let mut session = ChatSession::new(config, Some("system prompt")).unwrap();
        session.clear();
        assert_eq!(session.history().len(), 1);
        assert_eq!(session.history()[0].role, "system");
    }

    #[test]
    fn chat_session_clear_empty_when_no_system() {
        let config = ProviderConfig::ollama("test");
        let mut session = ChatSession::new(config, None).unwrap();
        session.clear();
        assert!(session.history().is_empty());
    }

    // -- Session persistence tests --

    fn make_test_record(id: uuid::Uuid) -> SessionRecord {
        SessionRecord {
            id,
            created_at: chrono::Utc::now(),
            saved_at: chrono::Utc::now(),
            config: ProviderConfig::ollama("test-model"),
            system_prompt: Some("test system".into()),
            messages: vec![
                Message::system("test system"),
                Message::user("hello"),
                Message::assistant("hi there"),
            ],
        }
    }

    #[test]
    fn session_record_serialization_roundtrip() {
        let record = make_test_record(uuid::Uuid::new_v4());
        let json = serde_json::to_string(&record).unwrap();
        let deserialized: SessionRecord = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.id, record.id);
        assert_eq!(deserialized.messages.len(), 3);
        assert_eq!(deserialized.config.model, "test-model");
        assert_eq!(deserialized.system_prompt.as_deref(), Some("test system"));
    }

    #[test]
    fn save_and_load_session_roundtrip() {
        let tmp = TempDir::new().unwrap();
        let id = uuid::Uuid::new_v4();
        let record = make_test_record(id);

        let path = tmp.path().join(format!("{}.json", id));
        let json = serde_json::to_string_pretty(&record).unwrap();
        std::fs::write(&path, &json).unwrap();

        let loaded = load_session(&path).unwrap();
        assert_eq!(loaded.id, id);
        assert_eq!(loaded.messages.len(), 3);
        assert_eq!(loaded.messages[0].role, "system");
        assert_eq!(loaded.messages[1].content, "hello");
        assert_eq!(loaded.messages[2].content, "hi there");
    }

    #[test]
    fn session_from_record_reconstructs_chat_session() {
        let record = make_test_record(uuid::Uuid::new_v4());
        let session = session_from_record(&record).unwrap();
        assert_eq!(session.history().len(), 3);
        assert_eq!(session.client().config().model, "test-model");
    }

    #[test]
    fn load_last_session_returns_none_when_empty() {
        let tmp = TempDir::new().unwrap();
        let original_home = std::env::var("HOME").ok();
        let original_profile = std::env::var("USERPROFILE").ok();

        let fake_home = tmp.path().join("fakehome");
        std::fs::create_dir_all(fake_home.join(".helios").join("sessions")).unwrap();
        std::env::set_var("HOME", &fake_home);
        #[cfg(windows)]
        std::env::set_var("USERPROFILE", &fake_home);

        let result = load_last_session().unwrap();
        assert!(result.is_none(), "no sessions should return None");

        match original_home {
            Some(v) => std::env::set_var("HOME", v),
            None => std::env::remove_var("HOME"),
        }
        #[cfg(windows)]
        match original_profile {
            Some(v) => std::env::set_var("USERPROFILE", v),
            None => std::env::remove_var("USERPROFILE"),
        }
        #[cfg(not(windows))]
        if let Some(v) = original_profile {
            std::env::set_var("USERPROFILE", v);
        }
    }

    #[test]
    fn session_record_has_valid_timestamps() {
        let record = make_test_record(uuid::Uuid::new_v4());
        let now = chrono::Utc::now();
        let diff_created = (now - record.created_at).num_seconds().abs();
        let diff_saved = (now - record.saved_at).num_seconds().abs();
        assert!(diff_created < 5, "created_at should be recent: {diff_created}s ago");
        assert!(diff_saved < 5, "saved_at should be recent: {diff_saved}s ago");
    }

    // -- CostTracker tests --

    #[test]
    fn cost_tracker_new_defaults_to_zero() {
        let tracker = CostTracker::new(0.000_030, 0.000_060, 1.0);
        assert_eq!(tracker.total_cost_usd(), 0.0);
        assert!(!tracker.is_over_budget());
    }

    #[test]
    fn cost_tracker_record_accumulates() {
        let mut tracker = CostTracker::new(0.000_030, 0.000_060, 10.0);
        tracker.record_usage(1_000, 500);
        let cost = tracker.total_cost_usd();
        assert!((cost - 0.06).abs() < 1e-9, "expected ~0.06, got {cost}");

        tracker.record_usage(2_000, 1_000);
        let cost2 = tracker.total_cost_usd();
        assert!((cost2 - 0.18).abs() < 1e-9, "expected ~0.18, got {cost2}");
    }

    #[test]
    fn cost_tracker_remaining_budget() {
        let mut tracker = CostTracker::new(0.000_030, 0.000_060, 1.0);
        assert!((tracker.remaining_budget_usd() - 1.0).abs() < 1e-9);
        tracker.record_usage(10_000, 5_000);
        // cost = 10000*0.000030 + 5000*0.000060 = 0.30 + 0.30 = 0.60
        assert!((tracker.remaining_budget_usd() - 0.4).abs() < 1e-9);
    }

    #[test]
    fn cost_tracker_over_budget() {
        let mut tracker = CostTracker::new(0.000_030, 0.000_060, 0.05);
        tracker.record_usage(1_000, 500);
        assert!(tracker.is_over_budget());
    }

    #[test]
    fn cost_tracker_usage_summary_format() {
        let mut tracker = CostTracker::new(0.000_030, 0.000_060, 1.0);
        tracker.record_usage(1_000, 500);
        let summary = tracker.usage_summary();
        assert!(summary.contains("input: 1000"));
        assert!(summary.contains("output: 500"));
        assert!(summary.contains("$"));
    }

    // -- SSE parsing tests --

    #[test]
    fn parse_sse_line_done() {
        let result = parse_sse_line("data: [DONE]");
        assert!(matches!(result, Some(SseEvent::Done)));
    }

    #[test]
    fn parse_sse_line_token() {
        let json = r#"data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}"#;
        let result = parse_sse_line(json);
        assert!(matches!(result, Some(SseEvent::Token(ref t)) if t == "Hello"));
    }

    #[test]
    fn parse_sse_line_empty() {
        assert!(parse_sse_line("").is_none());
        assert!(parse_sse_line("event: ping").is_none());
    }
}
