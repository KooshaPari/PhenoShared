//! `SupermemoryAdapter` — a `SemanticMemoryPort` that targets the
//! Supermemory Cloud HTTP API (`https://api.supermemory.ai`).
//!
//! Endpoints used:
//! - `POST   /v3/search`     — semantic recall (returns scored results)
//! - `POST   /v3/memories`   — store one Episodic memory (returns id)
//! - `DELETE /v3/memories/{id}` — forget a stored memory by id
//!
//! Authentication: Bearer token from `SUPERMEMORY_API_KEY`. The token is
//! read at adapter construction time, never at request time, so a missing
//! key fails fast at startup instead of on the first user-facing recall.
//!
//! The adapter is parameterised over a `base_url` so tests can target a
//! `mockito` server while production callers leave it at the default.

use async_trait::async_trait;
use forge_domain::{
    ConversationId, SemanticMemoryBudget, SemanticMemoryError, SemanticMemoryIdentity,
    SemanticMemoryPort, SemanticMemoryProvenance, SemanticMemoryQuery, SemanticMemoryRecord,
    SemanticMemoryScope, SemanticMemoryWrite,
};
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use tracing::debug;

use crate::http::{
    bearer_header, build_client, ensure_success, map_request_error, read_body, send_with_retry,
};

/// Default base URL for the Supermemory Cloud API.
pub const SUPERMEMORY_DEFAULT_BASE_URL: &str = "https://api.supermemory.ai";

/// Environment variable that supplies the Supermemory API key.
pub const SUPERMEMORY_API_KEY_ENV: &str = "SUPERMEMORY_API_KEY";

/// Environment variable that overrides the Supermemory base URL. Defaults
/// to `SUPERMEMORY_DEFAULT_BASE_URL` when unset. Used by self-hosted
/// deployments or staging proxies.
pub const SUPERMEMORY_BASE_URL_ENV: &str = "SUPERMEMORY_BASE_URL";

/// HTTP adapter for the Supermemory Cloud semantic-memory API.
#[derive(Debug, Clone)]
pub struct SupermemoryAdapter {
    client: Client,
    base_url: String,
    api_key: String,
}

impl SupermemoryAdapter {
    /// Builds a new adapter targeting `base_url` with `api_key` as the
    /// Bearer credential. Use [`from_env`](Self::from_env) to read the key
    /// from `SUPERMEMORY_API_KEY` automatically.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` if `api_key` is blank, or
    /// `Unavailable` if the underlying `reqwest::Client` cannot be built.
    pub fn new(
        base_url: impl Into<String>,
        api_key: impl Into<String>,
    ) -> Result<Self, SemanticMemoryError> {
        let api_key = api_key.into();
        // Validate the bearer header eagerly so missing keys surface as
        // Backend(401) — the same observable error the live provider returns.
        let _ = bearer_header(&api_key)?;
        let client = build_client()?;
        Ok(Self { client, base_url: base_url.into(), api_key })
    }

    /// Reads `SUPERMEMORY_API_KEY` from the process environment and builds
    /// an adapter targeting the default base URL. The base URL can be
    /// overridden via `SUPERMEMORY_BASE_URL`.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` when the env var is unset or
    /// blank. Callers wanting a self-hosted deployment should construct
    /// with [`new`](Self::new) directly.
    pub fn from_env() -> Result<Self, SemanticMemoryError> {
        let key = std::env::var(SUPERMEMORY_API_KEY_ENV).unwrap_or_default();
        let base_url = std::env::var(SUPERMEMORY_BASE_URL_ENV)
            .unwrap_or_else(|_| SUPERMEMORY_DEFAULT_BASE_URL.to_string());
        Self::new(base_url, key)
    }

    /// Returns the configured base URL.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }
}

#[async_trait]
impl SemanticMemoryPort for SupermemoryAdapter {
    async fn store(
        &self,
        write: SemanticMemoryWrite,
    ) -> Result<SemanticMemoryIdentity, SemanticMemoryError> {
        debug!(
            provider = "supermemory",
            namespace = %write.namespace().workspace_id(),
            "store: POST /v3/memories"
        );

        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v3/memories", self.base_url);
        let body = StoreRequest {
            content: write.content(),
            container_tag: write.namespace().workspace_id().to_string(),
            source: write.provenance().source_key(),
            metadata: StoreMetadata {
                conversation_id: write.provenance().conversation_id().into_string(),
                scope: write.scope(),
            },
        };

        // `build_request` is invoked once per attempt by `send_with_retry`
        // so a transient 503 / 429 gets a fresh request on the retry.
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
                                "supermemory: build store request: {err}"
                            ))
                        })
                },
                "supermemory: POST /v3/memories",
            )
            .await?,
        )
        .await?;

        let parsed: StoreResponse = response
            .json()
            .await
            .map_err(|err| map_request_error("supermemory: parse store response", err))?;

        SemanticMemoryIdentity::new(write.scope(), write.namespace().clone(), parsed.id)
    }

    async fn recall(
        &self,
        query: SemanticMemoryQuery,
        _budget: SemanticMemoryBudget,
    ) -> Result<Vec<SemanticMemoryRecord>, SemanticMemoryError> {
        debug!(
            provider = "supermemory",
            namespace = %query.namespace().workspace_id(),
            query = query.text(),
            "recall: POST /v3/search"
        );

        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v3/search", self.base_url);
        let body = SearchRequest {
            q: query.text(),
            container_tag: query.namespace().workspace_id().to_string(),
            limit: query.limit(),
            min_score: query.min_score(),
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
                                "supermemory: build search request: {err}"
                            ))
                        })
                },
                "supermemory: POST /v3/search",
            )
            .await?,
        )
        .await?;
        let body_text = read_body(response).await?;
        let parsed: SearchResponse = serde_json::from_str(&body_text)
            .map_err(|err| SemanticMemoryError::InvalidResponse(format!("parse search: {err}")))?;

        let namespace = query.namespace().clone();
        let mut records = Vec::with_capacity(parsed.results.len());
        for hit in parsed.results {
            if !hit.score.is_finite() {
                return Err(SemanticMemoryError::InvalidResponse(format!(
                    "supermemory: non-finite score {}",
                    hit.score
                )));
            }
            let identity = SemanticMemoryIdentity::new(
                SemanticMemoryScope::Episodic,
                namespace.clone(),
                &hit.id,
            )?;
            // ConversationId::parse fails on a non-UUID; fall back to a
            // generated placeholder so the call site still receives a
            // valid record and provenance is preserved (best-effort).
            let conversation_id = ConversationId::parse(&hit.conversation_id)
                .unwrap_or_else(|_| ConversationId::generate());
            let provenance = SemanticMemoryProvenance::new(
                conversation_id,
                namespace.clone(),
                hit.source.unwrap_or_else(|| "supermemory".to_string()),
            );
            let record =
                SemanticMemoryRecord::try_new(identity, hit.content, hit.score, provenance)?;
            records.push(record);
        }
        Ok(SemanticMemoryRecord::ranked(records))
    }

    async fn forget(&self, identity: SemanticMemoryIdentity) -> Result<(), SemanticMemoryError> {
        debug!(
            provider = "supermemory",
            id = identity.id(),
            "forget: DELETE /v3/memories/{{id}}"
        );

        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v3/memories/{}", self.base_url, identity.id());

        // `forget` semantics: 404 maps to success at the port boundary.
        // The retry helper will retry on 5xx/429; a 404 short-circuits
        // to success without retry because `send_with_retry` treats a
        // non-retryable status as a terminal response.
        let response = send_with_retry(
            &self.client,
            || {
                self.client
                    .delete(&url)
                    .header(name.clone(), value.clone())
                    .build()
                    .map_err(|err| {
                        SemanticMemoryError::InvalidResponse(format!(
                            "supermemory: build forget request: {err}"
                        ))
                    })
            },
            "supermemory: DELETE /v3/memories",
        )
        .await?;

        let status = response.status();
        if status == StatusCode::NOT_FOUND || status.is_success() {
            // Per the trait contract, "Missing identities must be treated as
            // success" — both 404 and 2xx are therefore successful forgets.
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
        "supermemory"
    }
}

// -- request / response shapes -------------------------------------------

#[derive(Debug, Serialize)]
struct StoreRequest<'a> {
    content: &'a str,
    container_tag: String,
    source: &'a str,
    metadata: StoreMetadata,
}

#[derive(Debug, Serialize)]
struct StoreMetadata {
    conversation_id: String,
    scope: SemanticMemoryScope,
}

#[derive(Debug, Deserialize)]
struct StoreResponse {
    id: String,
}

#[derive(Debug, Serialize)]
struct SearchRequest<'a> {
    q: &'a str,
    container_tag: String,
    limit: usize,
    min_score: Option<f32>,
}

#[derive(Debug, Deserialize)]
struct SearchResponse {
    #[serde(default)]
    results: Vec<SearchHit>,
}

#[derive(Debug, Deserialize)]
struct SearchHit {
    id: String,
    content: String,
    score: f32,
    #[serde(default)]
    conversation_id: String,
    #[serde(default)]
    source: Option<String>,
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
        let result = SupermemoryAdapter::new("https://example.invalid", "");
        match result {
            Err(SemanticMemoryError::Backend { status: 401, .. }) => {}
            other => panic!("expected Backend(401), got {other:?}"),
        }
    }

    #[tokio::test]
    async fn search_returns_ranked_records() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v3/search")
            .match_header("authorization", "Bearer sk-test")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                    "results": [
                        {
                            "id": "mem-1",
                            "content": "first result",
                            "score": 0.9,
                            "conversation_id": "conv-1",
                            "source": "supermemory"
                        },
                        {
                            "id": "mem-2",
                            "content": "second result",
                            "score": 0.5,
                            "conversation_id": "conv-2",
                            "source": "supermemory"
                        }
                    ]
                }"#,
            )
            .create_async()
            .await;

        let adapter =
            SupermemoryAdapter::new(server.url(), "sk-test").expect("adapter should build");
        let ns = fixture_namespace();
        let query = SemanticMemoryQuery::new(ns.clone(), "rollback plan", 10, None)
            .expect("query should validate");
        let budget = SemanticMemoryBudget::new(4096).expect("budget should validate");

        let hits = adapter
            .recall(query, budget)
            .await
            .expect("recall should succeed");
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].identity().id(), "mem-1");
        assert_eq!(hits[1].identity().id(), "mem-2");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn search_with_empty_results_returns_ok_empty() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v3/search")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"results": []}"#)
            .create_async()
            .await;

        let adapter =
            SupermemoryAdapter::new(server.url(), "sk-test").expect("adapter should build");
        let ns = fixture_namespace();
        let query = SemanticMemoryQuery::new(ns, "nothing matches", 5, None)
            .expect("query should validate");
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
            .mock("POST", "/v3/search")
            .with_status(401)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"unauthorized"}"#)
            .create_async()
            .await;

        let adapter =
            SupermemoryAdapter::new(server.url(), "sk-bad").expect("adapter should build");
        let ns = fixture_namespace();
        let query =
            SemanticMemoryQuery::new(ns, "anything", 1, None).expect("query should validate");
        let budget = SemanticMemoryBudget::new(1024).expect("budget should validate");

        let err = adapter
            .recall(query, budget)
            .await
            .expect_err("401 should error");
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 401);
                assert!(body.contains("unauthorized"));
            }
            other => panic!("expected Backend, got {other:?}"),
        }
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn forget_succeeds_on_404_for_missing_identity() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("DELETE", "/v3/memories/missing-id")
            .match_header("authorization", "Bearer sk-test")
            .with_status(404)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"not found"}"#)
            .create_async()
            .await;

        let adapter =
            SupermemoryAdapter::new(server.url(), "sk-test").expect("adapter should build");
        let ns = fixture_namespace();
        let identity = SemanticMemoryIdentity::new(SemanticMemoryScope::Episodic, ns, "missing-id")
            .expect("identity should validate");

        adapter
            .forget(identity)
            .await
            .expect("forget must treat 404 as success");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn store_returns_provider_assigned_id() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v3/memories")
            .match_header("authorization", "Bearer sk-test")
            .with_status(201)
            .with_header("content-type", "application/json")
            .with_body(r#"{"id":"supermem-abc-123"}"#)
            .create_async()
            .await;

        let adapter =
            SupermemoryAdapter::new(server.url(), "sk-test").expect("adapter should build");
        let ns = fixture_namespace();
        let prov = fixture_provenance(ns.clone());
        let write = SemanticMemoryWrite::new(
            SemanticMemoryScope::Episodic,
            ns.clone(),
            "deploy the rollback",
            prov,
        )
        .expect("write should validate");

        let identity = adapter.store(write).await.expect("store should succeed");
        assert_eq!(identity.id(), "supermem-abc-123");
        assert_eq!(identity.namespace(), &ns);
        mock.assert_async().await;
    }
}
