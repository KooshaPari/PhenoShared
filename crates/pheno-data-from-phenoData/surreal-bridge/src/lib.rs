//! SurrealDB Bridge - SurrealDB embedded with Pheno extensions
//!
//! Provides embedded SurrealDB with MCP protocol adapter and skill storage.
//!
//! ## SurrealDB v3 compatibility
//! In v3, internal SQL types are fully opaque. All record and content
//! operations use `serde_json::Value`. Raw SQL via `db.query()` is the
//! primary API for anything beyond simple select/insert.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use surrealdb::Surreal;
use surrealdb::engine::local::Db;

#[cfg(windows)]
use surrealdb::engine::local::Mem;
#[cfg(not(windows))]
use surrealdb::engine::local::RocksDb;

pub type RecordId = String;

/// PhenoSurreal - SurrealDB with extensions
pub struct PhenoSurreal {
    db: Surreal<Db>,
}

impl PhenoSurreal {
    /// Create new embedded SurrealDB
    pub async fn new(path: impl Into<String>) -> Result<Self> {
        let db = open_local_db(path).await?;
        db.use_ns("pheno").use_db("main").await?;
        Ok(Self { db })
    }

    /// Store a skill with versioning via raw SQL
    pub async fn store_skill(&self, skill: Skill) -> Result<RecordId> {
        let data = serde_json::to_value(&skill)?;
        let response: Option<serde_json::Value> = self
            .db
            .query("CREATE skill CONTENT $data RETURN id")
            .bind(("data", data))
            .await?
            .take(0)?;

        match response {
            Some(v) => {
                // v is {"id": {"tb": "skill", "id": "..."}} or {"id": "skill:..."}
                let id = extract_record_id(&v)?;
                Ok(id)
            }
            None => Err(anyhow::anyhow!("Failed to create skill")),
        }
    }

    /// Query all skills
    pub async fn query_skills(&self) -> Result<Vec<Skill>> {
        let records: Vec<serde_json::Value> = self.db.select("skill").await?;
        let skills: Vec<Skill> = records
            .into_iter()
            .filter_map(|r| serde_json::from_value(r).ok())
            .collect();
        Ok(skills)
    }

    /// Store a vector embedding via raw SQL
    pub async fn store_embedding(&self, embedding: Embedding) -> Result<RecordId> {
        let data = serde_json::to_value(&embedding)?;
        let response: Option<serde_json::Value> = self
            .db
            .query("CREATE embedding CONTENT $data RETURN id")
            .bind(("data", data))
            .await?
            .take(0)?;

        match response {
            Some(v) => {
                let id = extract_record_id(&v)?;
                Ok(id)
            }
            None => Err(anyhow::anyhow!("Failed to create embedding")),
        }
    }

    /// Search similar embeddings using cosine distance
    pub async fn search_similar(
        &self,
        query: &[f32],
        limit: usize,
    ) -> Result<Vec<ScoredEmbedding>> {
        let results: Vec<serde_json::Value> = self
            .db
            .query(
                "SELECT *, vector::distance::cosine(embedding, $query) AS score \
                 FROM embedding ORDER BY score ASC LIMIT $limit",
            )
            .bind(("query", serde_json::json!(query)))
            .bind(("limit", limit))
            .await?
            .take(0)?;

        let scored: Vec<ScoredEmbedding> = results
            .into_iter()
            .filter_map(|r| serde_json::from_value(r).ok())
            .collect();
        Ok(scored)
    }
}

async fn open_local_db(path: impl Into<String>) -> Result<Surreal<Db>> {
    #[cfg(not(windows))]
    {
        Ok(Surreal::new::<RocksDb>(path.into()).await?)
    }
    #[cfg(windows)]
    {
        let _ = path.into();
        Ok(Surreal::new::<Mem>(()).await?)
    }
}

/// Extract a `RecordId` string from a `{"id": ...}` JSON value.
/// Handles both `{"id": "table:id"}` string form and `{"id": {"tb": "table", "id": "..."}}` object form.
fn extract_record_id(v: &serde_json::Value) -> Result<RecordId> {
    let id_val = v
        .get("id")
        .ok_or_else(|| anyhow::anyhow!("no 'id' field"))?;

    match id_val {
        serde_json::Value::String(s) => Ok(s.clone()),
        serde_json::Value::Object(o) => {
            let tb = o
                .get("tb")
                .and_then(|v| v.as_str())
                .ok_or_else(|| anyhow::anyhow!("id object missing 'tb'"))?;
            let id = o
                .get("id")
                .and_then(|v| v.as_str().map(str::to_string))
                .or_else(|| o.get("id").and_then(|v| v.as_i64().map(|i| i.to_string())))
                .ok_or_else(|| anyhow::anyhow!("id object missing 'id'"))?;
            Ok(format!("{}:{}", tb, id))
        }
        _ => Err(anyhow::anyhow!("id field has unexpected type")),
    }
}

/// Skill record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    #[serde(rename = "id", skip_serializing_if = "Option::is_none")]
    pub id: Option<RecordId>,
    pub name: String,
    pub version: String,
    pub code: String,
    pub runtime: String,
    pub metadata: serde_json::Value,
}

impl Skill {
    pub fn new(name: String, version: String, code: String, runtime: String) -> Self {
        Self {
            id: None,
            name,
            version,
            code,
            runtime,
            metadata: serde_json::json!({}),
        }
    }
}

/// Embedding record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    #[serde(rename = "id", skip_serializing_if = "Option::is_none")]
    pub id: Option<RecordId>,
    pub vector: Vec<f32>,
    pub metadata: serde_json::Value,
}

/// Scored embedding result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredEmbedding {
    pub id: RecordId,
    pub embedding: Vec<f32>,
    pub metadata: serde_json::Value,
    pub score: f32,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_create_skill() -> Result<()> {
        let dir = tempdir()?;
        let db =
            PhenoSurreal::new(dir.path().join("test.db").to_string_lossy().into_owned()).await?;

        let skill = Skill::new(
            "test-skill".to_string(),
            "1.0.0".to_string(),
            "fn main() {}".to_string(),
            "wasm".to_string(),
        );

        let id = db.store_skill(skill).await?;
        assert!(id.starts_with("skill:"));
        Ok(())
    }
}
