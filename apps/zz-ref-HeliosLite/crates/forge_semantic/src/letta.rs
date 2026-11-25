//! `LettaAdapter` — a `SemanticMemoryPort` that targets the Letta Cloud
//! HTTP API (`https://api.letta.com`) or a self-hosted Letta deployment.
//!
//! Endpoints used:
//! - `POST /v1/agents/{agent_id}/messages` — semantic recall: send a user
//!   message, read back the assistant messages, extract any
//!   `recall_memory`-style tool-call responses as semantic-memory records.
//! - `GET  /v1/agents/{agent_id}/memory`   — recall the full agent memory.
//! - `DELETE /v1/agents/{agent_id}/memory/blocks/{block_id}` — forget a block.
//!
//! Authentication: Bearer token from `LETTA_API_KEY`.
//!
//! Letta returns Server-Sent Events (SSE) on the messages endpoint. Per the
//! F3 contract we read the first SSE chunk, extract the `data:` payload,
//! parse it as JSON, and turn it into domain records. We do not stream the
//! full SSE — the semantic-memory port is a recall boundary, not a chat
//! boundary, so a single final-state payload is enough.

use async_trait::async_trait;
use forge_domain::{
    ConversationId, SemanticMemoryBudget, SemanticMemoryError, SemanticMemoryIdentity,
    SemanticMemoryPort, SemanticMemoryProvenance, SemanticMemoryQuery, SemanticMemoryRecord,
    SemanticMemoryScope, SemanticMemoryWrite,
};
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use tracing::debug;

use crate::http::{bearer_header, build_client, ensure_success, read_body, send_with_retry};

/// Default base URL for the Letta Cloud API.
pub const LETTA_DEFAULT_BASE_URL: &str = "https://api.letta.com";

/// Environment variable that supplies the Letta API key.
pub const LETTA_API_KEY_ENV: &str = "LETTA_API_KEY";

/// Environment variable that overrides the Letta base URL. Defaults to
/// `LETTA_DEFAULT_BASE_URL` when unset. Used by self-hosted deployments
/// that point at a private Letta instance.
pub const LETTA_BASE_URL_ENV: &str = "LETTA_BASE_URL";

/// Environment variable that supplies the default Letta agent id. Defaults
/// to `letta-default-agent` when unset.
pub const LETTA_AGENT_ID_ENV: &str = "LETTA_AGENT_ID";

/// HTTP adapter for the Letta semantic-memory API.
#[derive(Debug, Clone)]
pub struct LettaAdapter {
    client: Client,
    base_url: String,
    api_key: String,
    /// Default agent id used when callers do not provide one through
    /// the namespace's `workspace_id` mapping. Letta is per-agent; we map
    /// each forge workspace to a single Letta agent.
    default_agent_id: String,
}

impl LettaAdapter {
    /// Builds a new adapter targeting `base_url` with `api_key` as the
    /// Bearer credential and `default_agent_id` as the agent used for
    /// store/recall/forget.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` if `api_key` is blank, or
    /// `Unavailable` if the underlying `reqwest::Client` cannot be built.
    pub fn new(
        base_url: impl Into<String>,
        api_key: impl Into<String>,
        default_agent_id: impl Into<String>,
    ) -> Result<Self, SemanticMemoryError> {
        let api_key = api_key.into();
        let _ = bearer_header(&api_key)?;
        let client = build_client()?;
        Ok(Self {
            client,
            base_url: base_url.into(),
            api_key,
            default_agent_id: default_agent_id.into(),
        })
    }

    /// Reads `LETTA_API_KEY` from the process environment and builds an
    /// adapter targeting Letta Cloud. The default agent id is read from
    /// `LETTA_AGENT_ID` if set, otherwise `letta-default-agent`. The base
    /// URL is read from `LETTA_BASE_URL` if set, otherwise the Letta
    /// Cloud default.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` when `LETTA_API_KEY` is
    /// unset or blank.
    pub fn from_env() -> Result<Self, SemanticMemoryError> {
        let key = std::env::var(LETTA_API_KEY_ENV).unwrap_or_default();
        let base_url = std::env::var(LETTA_BASE_URL_ENV)
            .unwrap_or_else(|_| LETTA_DEFAULT_BASE_URL.to_string());
        let agent =
            std::env::var(LETTA_AGENT_ID_ENV).unwrap_or_else(|_| "letta-default-agent".to_string());
        Self::new(base_url, key, agent)
    }

    /// Returns the configured base URL.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Returns the configured default agent id.
    pub fn default_agent_id(&self) -> &str {
        &self.default_agent_id
    }
}

/// Decode the first `data: { ... }` line out of an SSE response body.
///
/// Returns `InvalidResponse` if no `data:` line is found. A single SSE
/// event is usually << 1 KiB; we scan line-by-line which is O(n) and
/// bounded by the body length so it handles arbitrarily large first
/// chunks without buffering more than one line at a time.
fn extract_first_sse_data(body: &str) -> Result<&str, SemanticMemoryError> {
    for line in body.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("data:") {
            let payload = rest.trim();
            if payload.is_empty() || payload == "[DONE]" {
                continue;
            }
            return Ok(payload);
        }
        // Skip SSE comments and event/id lines.
    }
    Err(SemanticMemoryError::InvalidResponse(
        "letta: no SSE data line in response".to_string(),
    ))
}

#[async_trait]
impl SemanticMemoryPort for LettaAdapter {
    async fn store(
        &self,
        write: SemanticMemoryWrite,
    ) -> Result<SemanticMemoryIdentity, SemanticMemoryError> {
        debug!(
            provider = "letta",
            namespace = %write.namespace().workspace_id(),
            "store: POST /v1/agents/{{agent_id}}/messages"
        );

        let agent_id = self.default_agent_id.as_str();
        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v1/agents/{}/messages", self.base_url, agent_id);
        let body = MessagesRequest {
            messages: vec![UserMessage { role: "user", content: write.content() }],
        };

        let response = ensure_success(
            send_with_retry(
                &self.client,
                || {
                    self.client
                        .post(&url)
                        .header(name.clone(), value.clone())
                        .json(&body)
                        .build()
                        .map_err(|err| {
                            SemanticMemoryError::InvalidResponse(format!(
                                "letta: build messages request: {err}"
                            ))
                        })
                },
                "letta: POST messages",
            )
            .await?,
        )
        .await?;
        let body_text = read_body(response).await?;
        let payload = extract_first_sse_data(&body_text)?;
        let parsed: MessagesResponse = serde_json::from_str(payload).map_err(|err| {
            SemanticMemoryError::InvalidResponse(format!("parse letta messages: {err}"))
        })?;

        // The Letta response includes a `message_id` we can use as a stable
        // provider-side identifier; fall back to the first assistant
        // message id if it is absent.
        let id = parsed
            .message_id
            .or_else(|| {
                parsed
                    .messages
                    .iter()
                    .find(|m| m.role == "assistant")
                    .map(|m| m.id.clone())
            })
            .unwrap_or_else(|| format!("letta-msg-{}", write.namespace().workspace_id()));

        SemanticMemoryIdentity::new(write.scope(), write.namespace().clone(), id)
    }

    async fn recall(
        &self,
        query: SemanticMemoryQuery,
        _budget: SemanticMemoryBudget,
    ) -> Result<Vec<SemanticMemoryRecord>, SemanticMemoryError> {
        debug!(
            provider = "letta",
            namespace = %query.namespace().workspace_id(),
            query = query.text(),
            "recall: GET /v1/agents/{{agent_id}}/memory"
        );

        let agent_id = self.default_agent_id.as_str();
        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v1/agents/{}/memory", self.base_url, agent_id);

        let response = ensure_success(
            send_with_retry(
                &self.client,
                || {
                    self.client
                        .get(&url)
                        .header(name.clone(), value.clone())
                        .build()
                        .map_err(|err| {
                            SemanticMemoryError::InvalidResponse(format!(
                                "letta: build memory request: {err}"
                            ))
                        })
                },
                "letta: GET memory",
            )
            .await?,
        )
        .await?;
        let body_text = read_body(response).await?;
        let parsed: MemoryResponse = serde_json::from_str(&body_text).map_err(|err| {
            SemanticMemoryError::InvalidResponse(format!("parse letta memory: {err}"))
        })?;

        let namespace = query.namespace().clone();
        let conversation_id =
            ConversationId::parse(&parsed.agent_id).unwrap_or_else(|_| ConversationId::generate());

        let mut records: Vec<SemanticMemoryRecord> = Vec::new();
        for block in parsed.blocks {
            // Letta does not expose per-block relevance scores on the
            // /v1/agents/{id}/memory endpoint. The F3 contract uses
            // scores only for ranking — using 1.0 here means every block
            // returned is "fully relevant"; future P-tickets can switch
            // to embedding-similarity scoring.
            let score = 1.0_f32;
            if !score.is_finite() {
                return Err(SemanticMemoryError::InvalidResponse(
                    "letta: non-finite score".to_string(),
                ));
            }
            let identity = SemanticMemoryIdentity::new(
                SemanticMemoryScope::Episodic,
                namespace.clone(),
                &block.id,
            )?;
            let provenance = SemanticMemoryProvenance::new(
                conversation_id,
                namespace.clone(),
                block.label.unwrap_or_else(|| "letta".to_string()),
            );
            let record = SemanticMemoryRecord::try_new(identity, block.value, score, provenance)?;
            records.push(record);
        }
        Ok(SemanticMemoryRecord::ranked(records))
    }

    async fn forget(&self, identity: SemanticMemoryIdentity) -> Result<(), SemanticMemoryError> {
        debug!(
            provider = "letta",
            id = identity.id(),
            "forget: DELETE /v1/agents/{{agent_id}}/memory/blocks/{{id}}"
        );

        let agent_id = self.default_agent_id.as_str();
        let (name, value) = bearer_header(&self.api_key)?;
        // Per Letta docs, the per-block delete endpoint is
        // `DELETE /v1/agents/{agent_id}/memory/blocks/{block_id}`.
        let url = format!(
            "{}/v1/agents/{}/memory/blocks/{}",
            self.base_url,
            agent_id,
            identity.id()
        );

        let response = send_with_retry(
            &self.client,
            || {
                self.client
                    .delete(&url)
                    .header(name.clone(), value.clone())
                    .build()
                    .map_err(|err| {
                        SemanticMemoryError::InvalidResponse(format!(
                            "letta: build block delete request: {err}"
                        ))
                    })
            },
            "letta: DELETE block",
        )
        .await?;

        let status = response.status();
        if status == StatusCode::NOT_FOUND || status.is_success() {
            Ok(())
        } else {
            let status_code = status.as_u16();
            let body = read_body(response)
                .await
                .unwrap_or_else(|_| "<unreadable body>".to_string());
            Err(SemanticMemoryError::Backend { status: status_code, body })
        }
    }

    fn provider_name(&self) -> &'static str {
        "letta"
    }
}

// -- request / response shapes -------------------------------------------

#[derive(Debug, Serialize)]
struct MessagesRequest<'a> {
    messages: Vec<UserMessage<'a>>,
}

#[derive(Debug, Serialize)]
struct UserMessage<'a> {
    role: &'a str,
    content: &'a str,
}

#[derive(Debug, Deserialize)]
struct MessagesResponse {
    /// Top-level message id, when present.
    #[serde(default)]
    message_id: Option<String>,
    /// The full set of messages returned (assistant + tool).
    #[serde(default)]
    messages: Vec<AssistantMessage>,
}

#[derive(Debug, Deserialize)]
struct AssistantMessage {
    id: String,
    role: String,
}

#[derive(Debug, Deserialize)]
struct MemoryResponse {
    #[serde(default)]
    agent_id: String,
    #[serde(default)]
    blocks: Vec<MemoryBlock>,
}

#[derive(Debug, Deserialize)]
struct MemoryBlock {
    id: String,
    value: String,
    #[serde(default)]
    label: Option<String>,
}

#[cfg(test)]
// `assert_eq!(hits[0], ...)` style indexing is fine in tests where we
// have just verified the vector length. The crate-wide
// `indexing_slicing` deny is left intact for production code.
#[allow(clippy::indexing_slicing)]
mod tests {
    use super::*;

    use forge_domain::SemanticMemoryNamespace;
    use mockito::Server;

    fn fixture_namespace() -> SemanticMemoryNamespace {
        SemanticMemoryNamespace::new(forge_domain::WorkspaceId::generate())
    }

    fn fixture_provenance(namespace: SemanticMemoryNamespace) -> SemanticMemoryProvenance {
        SemanticMemoryProvenance::new(ConversationId::generate(), namespace, "test-source")
    }

    #[tokio::test]
    async fn adapter_rejects_blank_api_key_at_construction() {
        let result = LettaAdapter::new("https://example.invalid", "", "agent-x");
        match result {
            Err(SemanticMemoryError::Backend { status: 401, .. }) => {}
            other => panic!("expected Backend(401), got {other:?}"),
        }
    }

    #[test]
    fn sse_extraction_returns_first_data_payload() {
        let body = "event: message\ndata: {\"agent_id\":\"ag-1\"}\n\n";
        let actual = extract_first_sse_data(body).expect("first data line should parse");
        assert_eq!(actual, "{\"agent_id\":\"ag-1\"}");
    }

    #[test]
    fn sse_extraction_skips_done_marker_and_comments() {
        let body = ": ping\ndata: [DONE]\ndata: {\"ok\":true}\n";
        let actual = extract_first_sse_data(body).expect("second data line should parse");
        assert_eq!(actual, "{\"ok\":true}");
    }

    #[test]
    fn sse_extraction_returns_error_when_no_data_present() {
        let body = "event: error\ndata: \n\n";
        let err = extract_first_sse_data(body).expect_err("no data line should error");
        match err {
            SemanticMemoryError::InvalidResponse(_) => {}
            other => panic!("expected InvalidResponse, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn recall_returns_blocks_as_records() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("GET", "/v1/agents/agent-x/memory")
            .match_header("authorization", "Bearer sk-letta")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                    "agent_id": "agent-x",
                    "blocks": [
                        {"id": "block-1", "value": "first memory", "label": "episodic"},
                        {"id": "block-2", "value": "second memory", "label": "episodic"}
                    ]
                }"#,
            )
            .create_async()
            .await;

        let adapter =
            LettaAdapter::new(server.url(), "sk-letta", "agent-x").expect("adapter should build");
        let ns = fixture_namespace();
        let query = SemanticMemoryQuery::new(ns.clone(), "anything", 10, None)
            .expect("query should validate");
        let budget = SemanticMemoryBudget::new(4096).expect("budget should validate");

        let hits = adapter
            .recall(query, budget)
            .await
            .expect("recall should succeed");
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].identity().id(), "block-1");
        assert_eq!(hits[1].identity().id(), "block-2");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn recall_with_empty_blocks_returns_ok_empty() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("GET", "/v1/agents/agent-x/memory")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"agent_id":"agent-x","blocks":[]}"#)
            .create_async()
            .await;

        let adapter =
            LettaAdapter::new(server.url(), "sk-letta", "agent-x").expect("adapter should build");
        let ns = fixture_namespace();
        let query =
            SemanticMemoryQuery::new(ns, "nothing", 5, None).expect("query should validate");
        let budget = SemanticMemoryBudget::new(1024).expect("budget should validate");

        let hits = adapter
            .recall(query, budget)
            .await
            .expect("empty recall should succeed");
        assert!(hits.is_empty());
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn auth_failure_maps_to_backend_error() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("GET", "/v1/agents/agent-x/memory")
            .with_status(403)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"forbidden"}"#)
            .create_async()
            .await;

        let adapter =
            LettaAdapter::new(server.url(), "sk-bad", "agent-x").expect("adapter should build");
        let ns = fixture_namespace();
        let query =
            SemanticMemoryQuery::new(ns, "anything", 1, None).expect("query should validate");
        let budget = SemanticMemoryBudget::new(1024).expect("budget should validate");

        let err = adapter
            .recall(query, budget)
            .await
            .expect_err("403 should error");
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 403);
                assert!(body.contains("forbidden"));
            }
            other => panic!("expected Backend, got {other:?}"),
        }
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn forget_succeeds_on_404() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("DELETE", "/v1/agents/agent-x/memory/blocks/missing")
            .match_header("authorization", "Bearer sk-letta")
            .with_status(404)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"not found"}"#)
            .create_async()
            .await;

        let adapter =
            LettaAdapter::new(server.url(), "sk-letta", "agent-x").expect("adapter should build");
        let ns = fixture_namespace();
        let identity = SemanticMemoryIdentity::new(SemanticMemoryScope::Episodic, ns, "missing")
            .expect("identity should validate");

        adapter
            .forget(identity)
            .await
            .expect("forget must treat 404 as success");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn store_parses_first_sse_data_chunk() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v1/agents/agent-x/messages")
            .match_header("authorization", "Bearer sk-letta")
            .with_status(200)
            .with_header("content-type", "text/event-stream")
            .with_body(
                "event: message\ndata: {\"message_id\":\"letta-msg-7\",\"messages\":[{\"id\":\"letta-msg-7\",\"role\":\"assistant\"}]}\n\n",
            )
            .create_async()
            .await;

        let adapter =
            LettaAdapter::new(server.url(), "sk-letta", "agent-x").expect("adapter should build");
        let ns = fixture_namespace();
        let prov = fixture_provenance(ns.clone());
        let write = SemanticMemoryWrite::new(
            SemanticMemoryScope::Episodic,
            ns.clone(),
            "remember the rollback plan",
            prov,
        )
        .expect("write should validate");

        let identity = adapter.store(write).await.expect("store should succeed");
        assert_eq!(identity.id(), "letta-msg-7");
        assert_eq!(identity.namespace(), &ns);
        mock.assert_async().await;
    }
}
