//! phenoData smoke tests
//!
//! Integration tests covering the public APIs of workspace crates.
//!
//! Run with: cargo test --workspace

use pheno_query::{Filter, FilterOperator, QueryPlanner, QueryRequest};

/// Verifies the query planner generates a basic SurrealDB SELECT statement.
#[test]
fn test_query_planner_surreal_basic() {
    let req = QueryRequest {
        collection: "skills".to_string(),
        filter: None,
        vector: None,
        limit: 10,
        offset: None,
    };
    let query = QueryPlanner::plan_surreal(&req);
    assert!(
        query.sql.contains("SELECT * FROM skills"),
        "query: {query:?}"
    );
    assert!(query.sql.contains("LIMIT 10"), "query: {query:?}");
}

/// Verifies the query planner applies a WHERE filter condition.
#[test]
fn test_query_planner_with_filter() {
    let req = QueryRequest {
        collection: "documents".to_string(),
        filter: Some(Filter {
            field: "author".to_string(),
            operator: FilterOperator::Eq,
            value: serde_json::json!("Alice"),
        }),
        vector: None,
        limit: 5,
        offset: Some(10),
    };
    let query = QueryPlanner::plan_surreal(&req);
    assert!(query.sql.contains("WHERE author ="), "query: {query:?}");
    assert!(
        query.params.get("p0") == Some(&serde_json::json!("Alice")),
        "params: {:?}",
        query.params
    );
    assert!(query.sql.contains("LIMIT 5"), "query: {query:?}");
    assert!(query.sql.contains("START 10"), "query: {query:?}");
}

/// Verifies the PostgreSQL planner generates LIMIT/OFFSET correctly.
#[test]
fn test_query_planner_postgres_pagination() {
    let req = QueryRequest {
        collection: "events".to_string(),
        filter: None,
        vector: None,
        limit: 25,
        offset: Some(100),
    };
    let query = QueryPlanner::plan_postgres(&req);
    assert!(
        query.sql.contains("LIMIT 25 OFFSET 100"),
        "query: {query:?}"
    );
}

/// Verifies the workspace packages are publicly accessible from integration tests.
#[test]
fn test_crates_are_public() {
    let _req = QueryRequest {
        collection: "test".to_string(),
        filter: None,
        vector: None,
        limit: 1,
        offset: None,
    };
    let _filter = Filter {
        field: "x".to_string(),
        operator: FilterOperator::Eq,
        value: serde_json::json!(true),
    };
    let _planner = QueryPlanner;
}
