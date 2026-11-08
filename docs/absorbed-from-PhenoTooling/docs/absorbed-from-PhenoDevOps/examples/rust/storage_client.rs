//! Storage client examples for PhenoPolyglot
//!
//! Demonstrates connecting to Dragonfly, QuestDB, Qdrant, and Meilisearch

use pheno_dragonfly::{DragonflyClient, Session};
use pheno_questdb::QuestDBClient;
use pheno_qdrant::{QdrantClient, Point};
use pheno_meilisearch::MeilisearchClient;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("=== PhenoPolyglot Storage Client Examples ===\n");

    // 1. Dragonfly (Sessions/Cache)
    println!("1. Dragonfly (Redis-compatible cache)");
    let dragonfly = DragonflyClient::new("redis://localhost:6379").await?;
    println!("   ✅ Connected to Dragonfly");

    let session = Session {
        id: "user-123".to_string(),
        user_id: Some("user-456".to_string()),
        created_at: chrono::Utc::now(),
        last_accessed: chrono::Utc::now(),
        data: std::collections::HashMap::new(),
        ttl_seconds: 3600,
    };
    dragonfly.set_session(&session).await?;
    println!("   ✅ Session stored");

    // 2. QuestDB (Time-Series)
    println!("\n2. QuestDB (Time-series metrics)");
    let questdb = QuestDBClient::new("http://localhost:9000");
    println!("   ✅ Connected to QuestDB");

    // 3. Qdrant (Vector Search)
    println!("\n3. Qdrant (Vector search)");
    let qdrant = QdrantClient::new("http://localhost:6333");
    
    // Create collection for embeddings
    qdrant.create_collection("tools", 1536).await?;
    println!("   ✅ Connected to Qdrant");

    // 4. Meilisearch (Full-Text)
    println!("\n4. Meilisearch (Full-text search)");
    let meilisearch = MeilisearchClient::new("http://localhost:7700", Some("devmasterkey123"));
    
    meilisearch.create_index("tools", "id").await?;
    println!("   ✅ Connected to Meilisearch");

    println!("\n=== All storage backends connected! ===");
    Ok(())
}
