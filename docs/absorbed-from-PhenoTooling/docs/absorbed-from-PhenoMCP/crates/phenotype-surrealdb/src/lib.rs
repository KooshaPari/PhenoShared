// SPDX-License-Identifier: MIT OR Apache-2.0

//! PhenotypeSurrealDB — SurrealDB-backed skill storage for Pheno.
//!
//! # Current state
//!
//! This crate **explicitly implements [`pheno_ports::SkillStoragePort`]** with
//! an **in-memory backing** so that the workspace can compile and unit-tests
//! pass without a running SurrealDB instance.
//!
//! TODO(surreal): replace `InMemorySkillStore` delegation with a real
//! `surrealdb::Surreal<surrealdb::engine::remote::ws::Client>` call-through
//! once a persistent backend is required.  The `surrealdb` crate dependency
//! is already declared; only this file needs to change.
//!
//! # Existing surface
//!
//! The original `store_skill` / `query_skills` / `store_embedding` helpers are
//! preserved as-is so that existing callers keep compiling.

use anyhow::Result;
use async_trait::async_trait;
use pheno_ports::{
    doubles::InMemorySkillStore, SkillEntry, SkillStoragePort, StoragePortError,
};
use serde::{Deserialize, Serialize};

// ── Legacy domain types (unchanged) ───────────────────────────────────────

/// Skill definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub id: Option<String>,
    pub name: String,
    pub version: String,
    pub code: String,
    pub runtime: String,
    pub metadata: serde_json::Value,
}

/// Stored skill record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillRecord {
    pub id: String,
    pub name: String,
    pub version: String,
    pub code: String,
    pub runtime: String,
    pub metadata: serde_json::Value,
}

/// Embedding definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    pub id: Option<String>,
    pub vector: Vec<f32>,
    pub metadata: serde_json::Value,
}

/// Stored embedding record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingRecord {
    pub id: String,
    pub vector: Vec<f32>,
    pub metadata: serde_json::Value,
}

// ── PhenoSurreal ───────────────────────────────────────────────────────────

/// PhenoSurreal — SurrealDB wrapper with Pheno extensions.
///
/// Internally delegates to [`InMemorySkillStore`] until the real SurrealDB
/// driver is wired up (see TODO(surreal) above).
pub struct PhenoSurreal {
    #[allow(dead_code)]
    path: String,
    // TODO(surreal): replace with `surrealdb::Surreal<…>` when going live.
    store: InMemorySkillStore,
}

impl PhenoSurreal {
    /// Create a new PhenoSurreal instance.
    ///
    /// `path` is the intended SurrealDB endpoint / file path; it is stored for
    /// forward-compatibility but not yet used.
    pub async fn new(path: impl Into<String>) -> Result<Self> {
        Ok(Self {
            path: path.into(),
            store: InMemorySkillStore::new(),
        })
    }

    // ── Legacy surface (preserved) ─────────────────────────────────────────

    /// Store a skill (legacy helper — delegates to [`SkillStoragePort::put`]).
    pub async fn store_skill(&self, skill: Skill) -> Result<SkillRecord> {
        let id = format!("skill:{}", skill.name);
        let entry = SkillEntry {
            id: id.clone(),
            name: skill.name.clone(),
            version: skill.version.clone(),
            code: skill.code.clone(),
            runtime: skill.runtime.clone(),
            metadata: skill.metadata.clone(),
        };
        let stored = self
            .store
            .put(entry)
            .await
            .map_err(|e| anyhow::anyhow!("{}", e))?;
        Ok(SkillRecord {
            id: stored.id,
            name: stored.name,
            version: stored.version,
            code: stored.code,
            runtime: stored.runtime,
            metadata: stored.metadata,
        })
    }

    /// Query all skills (legacy helper — delegates to [`SkillStoragePort::list`]).
    pub async fn query_skills(&self) -> Result<Vec<SkillRecord>> {
        let entries = self
            .store
            .list()
            .await
            .map_err(|e| anyhow::anyhow!("{}", e))?;
        Ok(entries
            .into_iter()
            .map(|e| SkillRecord {
                id: e.id,
                name: e.name,
                version: e.version,
                code: e.code,
                runtime: e.runtime,
                metadata: e.metadata,
            })
            .collect())
    }

    /// Store a vector embedding (legacy helper — in-memory stub).
    ///
    /// TODO(surreal): persist embeddings via SurrealDB vector index.
    pub async fn store_embedding(&self, embedding: Embedding) -> Result<EmbeddingRecord> {
        Ok(EmbeddingRecord {
            id: format!("embedding:{}", embedding.id.unwrap_or_default()),
            vector: embedding.vector,
            metadata: embedding.metadata,
        })
    }
}

// ── SkillStoragePort implementation ───────────────────────────────────────

#[async_trait]
impl SkillStoragePort for PhenoSurreal {
    async fn put(&self, entry: SkillEntry) -> Result<SkillEntry, StoragePortError> {
        self.store.put(entry).await
    }

    async fn get(&self, id: &str) -> Result<SkillEntry, StoragePortError> {
        self.store.get(id).await
    }

    async fn list(&self) -> Result<Vec<SkillEntry>, StoragePortError> {
        self.store.list().await
    }

    async fn delete(&self, id: &str) -> Result<(), StoragePortError> {
        self.store.delete(id).await
    }
}

// ── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    async fn make_db() -> PhenoSurreal {
        PhenoSurreal::new("/tmp/test.db").await.unwrap()
    }

    // ── Legacy surface ─────────────────────────────────────────────────────

    #[tokio::test]
    async fn test_skill_storage_legacy() -> Result<()> {
        let db = make_db().await;
        let skill = Skill {
            id: None,
            name: "test-skill".to_string(),
            version: "1.0.0".to_string(),
            code: "fn main() {}".to_string(),
            runtime: "wasm".to_string(),
            metadata: json!({}),
        };
        let result = db.store_skill(skill).await?;
        assert_eq!(result.name, "test-skill");
        Ok(())
    }

    #[tokio::test]
    async fn test_query_skills_legacy() -> Result<()> {
        let db = make_db().await;
        let skill = Skill {
            id: None,
            name: "listed-skill".to_string(),
            version: "0.1.0".to_string(),
            code: "".to_string(),
            runtime: "native".to_string(),
            metadata: json!({}),
        };
        db.store_skill(skill).await?;
        let skills = db.query_skills().await?;
        assert_eq!(skills.len(), 1);
        assert_eq!(skills[0].name, "listed-skill");
        Ok(())
    }

    // ── SkillStoragePort surface ───────────────────────────────────────────

    #[tokio::test]
    async fn test_port_put_get_round_trip() {
        let db = make_db().await;
        let entry = SkillEntry {
            id: "skill:hello".to_string(),
            name: "hello".to_string(),
            version: "1.0.0".to_string(),
            code: "fn main() {}".to_string(),
            runtime: "wasm".to_string(),
            metadata: json!({}),
        };
        db.put(entry.clone()).await.unwrap();
        let fetched = db.get("skill:hello").await.unwrap();
        assert_eq!(fetched, entry);
    }

    #[tokio::test]
    async fn test_port_delete() {
        let db = make_db().await;
        let entry = SkillEntry {
            id: "skill:bye".to_string(),
            name: "bye".to_string(),
            version: "1.0.0".to_string(),
            code: "".to_string(),
            runtime: "native".to_string(),
            metadata: json!({}),
        };
        db.put(entry).await.unwrap();
        db.delete("skill:bye").await.unwrap();
        let err = db.get("skill:bye").await.unwrap_err();
        assert!(matches!(err, StoragePortError::NotFound(_)));
    }

    /// Object-safety smoke test.
    #[tokio::test]
    async fn test_pheno_surreal_is_skill_storage_port() {
        let db = make_db().await;
        let _: Box<dyn SkillStoragePort> = Box::new(db);
    }
}
