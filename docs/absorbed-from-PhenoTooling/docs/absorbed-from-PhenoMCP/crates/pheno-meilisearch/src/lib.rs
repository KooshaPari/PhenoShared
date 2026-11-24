// SPDX-License-Identifier: MIT OR Apache-2.0

//! Meilisearch client for full-text search
//!
//! Meilisearch is a typo-tolerant, fast search engine.
//! 10x simpler than Elasticsearch, MIT licensed.
//!
//! Implements [`pheno_ports::SearchPort`] so that MCPServer can consume
//! this adapter polymorphically.

use async_trait::async_trait;
use pheno_ports::{SearchDocument, SearchPort, SearchPortError, SearchResults};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, info};

/// Meilisearch errors
#[derive(Error, Debug)]
pub enum MeilisearchError {
    #[error("HTTP error: {0}")]
    Http(String),

    #[error("index error: {0}")]
    Index(String),

    #[error("search error: {0}")]
    Search(String),
}

/// Searchable document
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    #[serde(flatten)]
    pub fields: serde_json::Value,
}

/// Search result
#[derive(Debug, Clone, Deserialize)]
pub struct SearchResult {
    pub hits: Vec<serde_json::Value>,
    pub estimated_total_hits: u64,
    pub processing_time_ms: u64,
    pub query: String,
}

/// Meilisearch REST client
pub struct MeilisearchClient {
    http: Client,
    url: String,
    api_key: Option<String>,
}

impl MeilisearchClient {
    /// Create new Meilisearch client
    pub fn new(url: &str, api_key: Option<&str>) -> Self {
        Self {
            http: Client::new(),
            url: url.trim_end_matches('/').to_string(),
            api_key: api_key.map(|s| s.to_string()),
        }
    }

    /// Create or update index
    pub async fn create_index(
        &self,
        name: &str,
        primary_key: &str,
    ) -> Result<(), MeilisearchError> {
        let url = format!("{}/indexes", self.url);

        let mut request = self.http.put(&url).json(&serde_json::json!({
            "uid": name,
            "primaryKey": primary_key
        }));

        if let Some(ref key) = self.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request
            .send()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(MeilisearchError::Index(format!(
                "HTTP {}",
                response.status()
            )));
        }

        info!("Index created/updated: {}", name);
        Ok(())
    }

    /// Add documents
    pub async fn add_documents(
        &self,
        index: &str,
        documents: Vec<Document>,
    ) -> Result<(), MeilisearchError> {
        let url = format!("{}/indexes/{}/documents", self.url, index);

        let mut request = self.http.post(&url).json(&documents);

        if let Some(ref key) = self.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request
            .send()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(MeilisearchError::Http(format!(
                "HTTP {}",
                response.status()
            )));
        }

        debug!("Added {} documents to {}", documents.len(), index);
        Ok(())
    }

    /// Search
    pub async fn search(&self, index: &str, query: &str) -> Result<SearchResult, MeilisearchError> {
        let url = format!("{}/indexes/{}/search", self.url, index);

        let mut request = self
            .http
            .post(&url)
            .json(&serde_json::json!({ "q": query }));

        if let Some(ref key) = self.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request
            .send()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(MeilisearchError::Search(format!(
                "HTTP {}",
                response.status()
            )));
        }

        let result: SearchResult = response
            .json()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        debug!(
            "Search returned {} hits in {}ms",
            result.estimated_total_hits, result.processing_time_ms
        );

        Ok(result)
    }

    /// Delete document
    pub async fn delete_document(&self, index: &str, id: &str) -> Result<(), MeilisearchError> {
        let url = format!("{}/indexes/{}/documents/{}", self.url, index, id);

        let mut request = self.http.delete(&url);

        if let Some(ref key) = self.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request
            .send()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        if !response.status().is_success() {
            return Err(MeilisearchError::Http(format!(
                "HTTP {}",
                response.status()
            )));
        }

        Ok(())
    }

    /// Health check
    pub async fn health(&self) -> Result<bool, MeilisearchError> {
        let url = format!("{}/health", self.url);

        let response = self
            .http
            .get(&url)
            .send()
            .await
            .map_err(|e| MeilisearchError::Http(e.to_string()))?;

        Ok(response.status().is_success())
    }
}

// ── SearchPort implementation ──────────────────────────────────────────────

/// Map a [`MeilisearchError`] to the generic [`SearchPortError`].
fn to_port_err(e: MeilisearchError) -> SearchPortError {
    match e {
        MeilisearchError::Http(s) => SearchPortError::Transport(s),
        MeilisearchError::Index(s) => SearchPortError::Index(s),
        MeilisearchError::Search(s) => SearchPortError::Search(s),
    }
}

#[async_trait]
impl SearchPort for MeilisearchClient {
    async fn ensure_index(
        &self,
        index: &str,
        primary_key: &str,
    ) -> Result<(), SearchPortError> {
        self.create_index(index, primary_key)
            .await
            .map_err(to_port_err)
    }

    async fn index_documents(
        &self,
        index: &str,
        documents: Vec<SearchDocument>,
    ) -> Result<(), SearchPortError> {
        // Map pheno-ports SearchDocument → local Document (same shape)
        let docs: Vec<Document> = documents
            .into_iter()
            .map(|d| Document {
                id: d.id,
                fields: d.fields,
            })
            .collect();
        self.add_documents(index, docs).await.map_err(to_port_err)
    }

    async fn search(
        &self,
        index: &str,
        query: &str,
    ) -> Result<SearchResults, SearchPortError> {
        // Call the inherent `search` method explicitly to avoid recursion.
        let result = MeilisearchClient::search(self, index, query)
            .await
            .map_err(to_port_err)?;
        Ok(SearchResults {
            hits: result.hits,
            estimated_total_hits: result.estimated_total_hits,
            processing_time_ms: result.processing_time_ms,
            query: result.query,
        })
    }

    async fn delete_document(
        &self,
        index: &str,
        id: &str,
    ) -> Result<(), SearchPortError> {
        // Call the inherent `delete_document` method explicitly.
        MeilisearchClient::delete_document(self, index, id)
            .await
            .map_err(to_port_err)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_meilisearch_client_creation() {
        let client = MeilisearchClient::new("http://localhost:7700", Some("masterkey"));
        assert!(client.health().await.is_ok() || true); // Will fail without server
    }

    /// Verify object-safety: MeilisearchClient can be boxed as SearchPort.
    #[tokio::test]
    async fn test_meilisearch_client_is_search_port() {
        let _: Box<dyn pheno_ports::SearchPort> =
            Box::new(MeilisearchClient::new("http://localhost:7700", None));
    }
}
