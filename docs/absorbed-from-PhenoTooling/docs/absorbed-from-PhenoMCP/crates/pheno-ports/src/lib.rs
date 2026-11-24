// SPDX-License-Identifier: MIT OR Apache-2.0

//! Hexagonal port traits for PhenoMCP infrastructure.
//!
//! This crate defines the abstract ports (interfaces) that allow MCPServer
//! to consume search and skill-storage adapters polymorphically.
//!
//! Ports:
//! - [`SearchPort`] — index / search / delete (backed by Meilisearch)
//! - [`SkillStoragePort`] — get / put / list skills (backed by SurrealDB or in-memory)
//!
//! In-memory test doubles live in [`doubles`].

pub mod doubles;

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ── Shared domain types ────────────────────────────────────────────────────

/// A document that can be stored in and retrieved from the search index.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchDocument {
    pub id: String,
    #[serde(flatten)]
    pub fields: serde_json::Value,
}

/// Results returned by a search query.
#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct SearchResults {
    pub hits: Vec<serde_json::Value>,
    pub estimated_total_hits: u64,
    pub processing_time_ms: u64,
    pub query: String,
}

/// A skill record persisted in skill storage.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SkillEntry {
    pub id: String,
    pub name: String,
    pub version: String,
    pub code: String,
    pub runtime: String,
    pub metadata: serde_json::Value,
}

// ── Port errors ────────────────────────────────────────────────────────────

/// Errors that any [`SearchPort`] implementation may return.
#[derive(Error, Debug)]
pub enum SearchPortError {
    #[error("index error: {0}")]
    Index(String),
    #[error("search error: {0}")]
    Search(String),
    #[error("delete error: {0}")]
    Delete(String),
    #[error("transport error: {0}")]
    Transport(String),
}

/// Errors that any [`SkillStoragePort`] implementation may return.
#[derive(Error, Debug)]
pub enum StoragePortError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("serialisation error: {0}")]
    Serialise(String),
    #[error("backend error: {0}")]
    Backend(String),
}

// ── Port trait: SearchPort ─────────────────────────────────────────────────

/// Abstract search port.
///
/// Implementations must be object-safe (`Box<dyn SearchPort>`).
#[async_trait]
pub trait SearchPort: Send + Sync {
    /// Ensure the named index exists with the given primary key field.
    async fn ensure_index(
        &self,
        index: &str,
        primary_key: &str,
    ) -> Result<(), SearchPortError>;

    /// Add or replace documents in the index.
    async fn index_documents(
        &self,
        index: &str,
        documents: Vec<SearchDocument>,
    ) -> Result<(), SearchPortError>;

    /// Run a full-text search query against the index.
    async fn search(
        &self,
        index: &str,
        query: &str,
    ) -> Result<SearchResults, SearchPortError>;

    /// Remove a single document by its id.
    async fn delete_document(
        &self,
        index: &str,
        id: &str,
    ) -> Result<(), SearchPortError>;
}

// ── Port trait: SkillStoragePort ───────────────────────────────────────────

/// Abstract skill-storage port.
///
/// Implementations must be object-safe (`Box<dyn SkillStoragePort>`).
#[async_trait]
pub trait SkillStoragePort: Send + Sync {
    /// Persist or replace a skill entry. Returns the stored record.
    async fn put(&self, entry: SkillEntry) -> Result<SkillEntry, StoragePortError>;

    /// Retrieve a skill entry by id.
    async fn get(&self, id: &str) -> Result<SkillEntry, StoragePortError>;

    /// List all stored skill entries.
    async fn list(&self) -> Result<Vec<SkillEntry>, StoragePortError>;

    /// Remove a skill entry by id.
    async fn delete(&self, id: &str) -> Result<(), StoragePortError>;
}
