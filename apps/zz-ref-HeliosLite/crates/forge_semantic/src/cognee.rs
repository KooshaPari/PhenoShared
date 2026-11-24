//! `CogneeAdapter` — a `SemanticMemoryPort` that targets the Cognee Cloud
//! HTTP API (`https://api.cognee.ai`) or a self-hosted Cognee deployment.
//!
//! Endpoints used (per Cognee's documented v1 surface):
//! - `POST /v1/add`      — queue data for ingestion (returns a data_id)
//! - `POST /v1/cognify`  — turn queued data into a knowledge graph
//!   (returns a dataset / pipeline run id; we use it as the memory id)
//! - `POST /v1/search`   — semantic recall (returns ranked results)
//!
//! Authentication: Bearer token from `COGNEE_API_KEY`.
//!
//! The Cognee v1 surface is small enough that `add` + `cognify` together
//! implement `store` (we POST to `add`, then to `cognify`, and return
//! the cognify pipeline id). Future P-tickets can collapse this to a
//! single endpoint if Cognee ships one.

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

/// Default base URL for the Cognee Cloud API.
pub const COGNEE_DEFAULT_BASE_URL: &str = "https://api.cognee.ai";

/// Environment variable that supplies the Cognee API key.
pub const COGNEE_API_KEY_ENV: &str = "COGNEE_API_KEY";

/// Environment variable that overrides the Cognee base URL. Defaults to
/// `COGNEE_DEFAULT_BASE_URL` when unset. Used by self-hosted deployments
/// that point at a private Cognee instance.
pub const COGNEE_BASE_URL_ENV: &str = "COGNEE_API_URL";

/// Environment variable that supplies the Cognee dataset name. Defaults
/// to `cognee-default-dataset` when unset.
pub const COGNEE_DATASET_ENV: &str = "COGNEE_DATASET";

/// HTTP adapter for the Cognee semantic-memory API.
#[derive(Debug, Clone)]
pub struct CogneeAdapter {
    client: Client,
    base_url: String,
    api_key: String,
    /// Cognee dataset name to scope all writes to. We pin to a single
    /// dataset per adapter so that a workspace's memories stay isolated.
    dataset: String,
}

impl CogneeAdapter {
    /// Builds a new adapter targeting `base_url` with `api_key` as the
    /// Bearer credential and `dataset` as the Cognee dataset name.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` if `api_key` is blank, or
    /// `Unavailable` if the underlying `reqwest::Client` cannot be built.
    pub fn new(
        base_url: impl Into<String>,
        api_key: impl Into<String>,
        dataset: impl Into<String>,
    ) -> Result<Self, SemanticMemoryError> {
        let api_key = api_key.into();
        let _ = bearer_header(&api_key)?;
        let client = build_client()?;
        Ok(Self {
            client,
            base_url: base_url.into(),
            api_key,
            dataset: dataset.into(),
        })
    }

    /// Reads `COGNEE_API_KEY` from the process environment and builds an
    /// adapter targeting the default base URL. Dataset is read from
    /// `COGNEE_DATASET` if set, otherwise `cognee-default-dataset`.
    /// Base URL is read from `COGNEE_API_URL` if set, otherwise the
    /// Cognee Cloud default.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` when `COGNEE_API_KEY` is
    /// unset or blank.
    pub fn from_env() -> Result<Self, SemanticMemoryError> {
        let key = std::env::var(COGNEE_API_KEY_ENV).unwrap_or_default();
        let base_url = std::env::var(COGNEE_BASE_URL_ENV)
            .unwrap_or_else(|_| COGNEE_DEFAULT_BASE_URL.to_string());
        let dataset = std::env::var(COGNEE_DATASET_ENV)
            .unwrap_or_else(|_| "cognee-default-dataset".to_string());
        Self::new(base_url, key, dataset)
    }

    /// Returns the configured base URL.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Returns the configured Cognee dataset name.
    pub fn dataset(&self) -> &str {
        &self.dataset
    }
}

#[async_trait]
impl SemanticMemoryPort for CogneeAdapter {
    async fn store(
        &self,
        write: SemanticMemoryWrite,
    ) -> Result<SemanticMemoryIdentity, SemanticMemoryError> {
        debug!(
            provider = "cognee",
            namespace = %write.namespace().workspace_id(),
            "store: POST /v1/add + POST /v1/cognify"
        );

        let (name, value) = bearer_header(&self.api_key)?;

        // Step 1: add the raw data so Cognee can pick it up.
        let add_url = format!("{}/v1/add", self.base_url);
        let add_body = AddRequest { data: write.content(), dataset_name: self.dataset.clone() };
        let add_response = ensure_success(
            send_with_retry(
                &self.client,
                || {
                    self.client
                        .post(&add_url)
                        .header(name.clone(), value.clone())
                        .json(&add_body)
                        .build()
                        .map_err(|err| {
                            SemanticMemoryError::InvalidResponse(format!(
                                "cognee: build add request: {err}"
                            ))
                        })
                },
                "cognee: POST /v1/add",
            )
            .await?,
        )
        .await?;
        let add_body_text = read_body(add_response).await?;
        let add_parsed: AddResponse = serde_json::from_str(&add_body_text)
            .map_err(|err| SemanticMemoryError::InvalidResponse(format!("cognee add: {err}")))?;

        // Step 2: cognify the just-added data so it becomes recallable.
        let cognify_url = format!("{}/v1/cognify", self.base_url);
        let cognify_body = CognifyRequest { datasets: vec![self.dataset.clone()] };
        let cognify_response = ensure_success(
            send_with_retry(
                &self.client,
                || {
                    self.client
                        .post(&cognify_url)
                        .header(name.clone(), value.clone())
                        .json(&cognify_body)
                        .build()
                        .map_err(|err| {
                            SemanticMemoryError::InvalidResponse(format!(
                                "cognee: build cognify request: {err}"
                            ))
                        })
                },
                "cognee: POST /v1/cognify",
            )
            .await?,
        )
        .await?;
        let cognify_body_text = read_body(cognify_response).await?;
        let cognify_parsed: CognifyResponse =
            serde_json::from_str(&cognify_body_text).map_err(|err| {
                SemanticMemoryError::InvalidResponse(format!("cognee cognify: {err}"))
            })?;

        // Prefer the cognify pipeline run id; fall back to the add data id
        // when the cognify response doesn't expose one.
        let id = cognify_parsed
            .pipeline_run_id
            .or(cognify_parsed.run_id)
            .unwrap_or(add_parsed.data_id);

        SemanticMemoryIdentity::new(write.scope(), write.namespace().clone(), id)
    }

    async fn recall(
        &self,
        query: SemanticMemoryQuery,
        _budget: SemanticMemoryBudget,
    ) -> Result<Vec<SemanticMemoryRecord>, SemanticMemoryError> {
        debug!(
            provider = "cognee",
            namespace = %query.namespace().workspace_id(),
            query = query.text(),
            "recall: POST /v1/search"
        );

        let (name, value) = bearer_header(&self.api_key)?;
        let url = format!("{}/v1/search", self.base_url);
        let body = SearchRequest {
            query: query.text(),
            datasets: vec![self.dataset.clone()],
            top_k: query.limit(),
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
                                "cognee: build search request: {err}"
                            ))
                        })
                },
                "cognee: POST /v1/search",
            )
            .await?,
        )
        .await?;
        let body_text = read_body(response).await?;
        let parsed: SearchResponse = serde_json::from_str(&body_text)
            .map_err(|err| SemanticMemoryError::InvalidResponse(format!("cognee search: {err}")))?;

        let namespace = query.namespace().clone();

        // Cognee's search response is loose — accept both an envelope
        // `{ "results": [...] }` and a bare `[...]` for forward compat.
        let hits: Vec<SearchHit> = match parsed {
            SearchResponse::Envelope { results } => results,
            SearchResponse::Bare(results) => results,
        };

        let mut records = Vec::with_capacity(hits.len());
        for hit in hits {
            let score = hit.score.unwrap_or(1.0);
            if !score.is_finite() {
                return Err(SemanticMemoryError::InvalidResponse(format!(
                    "cognee: non-finite score {score}"
                )));
            }
            let id = hit.id.unwrap_or_else(|| {
                format!(
                    "cognee-{}-{}",
                    self.dataset,
                    hit.chunk_id.clone().unwrap_or_default()
                )
            });
            let identity =
                SemanticMemoryIdentity::new(SemanticMemoryScope::Episodic, namespace.clone(), &id)?;
            let conversation_id = hit
                .conversation_id
                .as_deref()
                .and_then(|c| ConversationId::parse(c).ok())
                .unwrap_or_else(ConversationId::generate);
            let provenance = SemanticMemoryProvenance::new(
                conversation_id,
                namespace.clone(),
                hit.source.unwrap_or_else(|| "cognee".to_string()),
            );
            let record = SemanticMemoryRecord::try_new(identity, hit.content, score, provenance)?;
            records.push(record);
        }
        Ok(SemanticMemoryRecord::ranked(records))
    }

    async fn forget(&self, identity: SemanticMemoryIdentity) -> Result<(), SemanticMemoryError> {
        debug!(
            provider = "cognee",
            id = identity.id(),
            "forget: DELETE /v1/datasets/{{dataset}}/data/{{id}}"
        );

        let (name, value) = bearer_header(&self.api_key)?;
        // Cognee is dataset-scoped: deletes target the data within the
        // bound dataset. 404 and 2xx both map to success at the port
        // boundary.
        let url = format!(
            "{}/v1/datasets/{}/data/{}",
            self.base_url,
            self.dataset,
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
                            "cognee: build delete request: {err}"
                        ))
                    })
            },
            "cognee: DELETE data",
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
        "cognee"
    }
}

// -- request / response shapes -------------------------------------------

#[derive(Debug, Serialize)]
struct AddRequest<'a> {
    data: &'a str,
    dataset_name: String,
}

#[derive(Debug, Deserialize)]
struct AddResponse {
    #[serde(default)]
    data_id: String,
}

#[derive(Debug, Serialize)]
struct CognifyRequest {
    datasets: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct CognifyResponse {
    #[serde(default)]
    pipeline_run_id: Option<String>,
    #[serde(default)]
    run_id: Option<String>,
}

#[derive(Debug, Serialize)]
struct SearchRequest<'a> {
    query: &'a str,
    datasets: Vec<String>,
    top_k: usize,
    min_score: Option<f32>,
}

/// Cognee's search payload is inconsistently documented; accept both an
/// envelope object and a bare array so we degrade gracefully across
/// versions of the API.
#[derive(Debug, Deserialize)]
#[serde(untagged)]
enum SearchResponse {
    Envelope {
        #[serde(default)]
        results: Vec<SearchHit>,
    },
    Bare(Vec<SearchHit>),
}

#[derive(Debug, Deserialize)]
struct SearchHit {
    #[serde(default)]
    id: Option<String>,
    #[serde(default)]
    chunk_id: Option<String>,
    content: String,
    #[serde(default)]
    score: Option<f32>,
    #[serde(default)]
    conversation_id: Option<String>,
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
        let result = CogneeAdapter::new("https://example.invalid", "", "ds-x");
        match result {
            Err(SemanticMemoryError::Backend { status: 401, .. }) => {}
            other => panic!("expected Backend(401), got {other:?}"),
        }
    }

    #[tokio::test]
    async fn recall_returns_results_from_envelope() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v1/search")
            .match_header("authorization", "Bearer sk-cognee")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"{
                    "results": [
                        {"id":"kg-1","content":"first memory","score":0.92},
                        {"id":"kg-2","content":"second memory","score":0.51}
                    ]
                }"#,
            )
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-cognee", "ds-x").expect("adapter should build");
        let ns = fixture_namespace();
        let query = SemanticMemoryQuery::new(ns.clone(), "rollback plan", 10, None)
            .expect("query should validate");
        let budget = SemanticMemoryBudget::new(4096).expect("budget should validate");

        let hits = adapter
            .recall(query, budget)
            .await
            .expect("recall should succeed");
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].identity().id(), "kg-1");
        assert_eq!(hits[1].identity().id(), "kg-2");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn recall_accepts_bare_array_response() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v1/search")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                r#"[
                    {"id":"kg-3","content":"bare-array memory","score":0.7}
                ]"#,
            )
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-cognee", "ds-x").expect("adapter should build");
        let ns = fixture_namespace();
        let query =
            SemanticMemoryQuery::new(ns, "fallback", 5, None).expect("query should validate");
        let budget = SemanticMemoryBudget::new(1024).expect("budget should validate");

        let hits = adapter
            .recall(query, budget)
            .await
            .expect("bare-array recall should succeed");
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].identity().id(), "kg-3");
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn recall_with_empty_results_returns_ok_empty() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("POST", "/v1/search")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"results":[]}"#)
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-cognee", "ds-x").expect("adapter should build");
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
            .mock("POST", "/v1/search")
            .with_status(401)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"unauthorized"}"#)
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-bad", "ds-x").expect("adapter should build");
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
    async fn forget_succeeds_on_404() {
        let mut server = Server::new_async().await;
        let mock = server
            .mock("DELETE", "/v1/datasets/ds-x/data/missing")
            .match_header("authorization", "Bearer sk-cognee")
            .with_status(404)
            .with_header("content-type", "application/json")
            .with_body(r#"{"error":"not found"}"#)
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-cognee", "ds-x").expect("adapter should build");
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
    async fn store_chains_add_then_cognify_and_returns_cognify_id() {
        let mut server = Server::new_async().await;

        let add_mock = server
            .mock("POST", "/v1/add")
            .match_header("authorization", "Bearer sk-cognee")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"data_id":"data-1"}"#)
            .create_async()
            .await;

        let cognify_mock = server
            .mock("POST", "/v1/cognify")
            .match_header("authorization", "Bearer sk-cognee")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"pipeline_run_id":"run-42"}"#)
            .create_async()
            .await;

        let adapter =
            CogneeAdapter::new(server.url(), "sk-cognee", "ds-x").expect("adapter should build");
        let ns = fixture_namespace();
        let prov = fixture_provenance(ns.clone());
        let write = SemanticMemoryWrite::new(
            SemanticMemoryScope::Episodic,
            ns.clone(),
            "store the rollback plan",
            prov,
        )
        .expect("write should validate");

        let identity = adapter.store(write).await.expect("store should succeed");
        assert_eq!(identity.id(), "run-42");
        assert_eq!(identity.namespace(), &ns);
        add_mock.assert_async().await;
        cognify_mock.assert_async().await;
    }
}
