//! PhenoQuery - Unified query builder for Pheno
//!
//! Provides a unified query interface across different data stores.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use tracing::instrument;

/// Parameterized query statement
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct QueryStatement {
    pub sql: String,
    pub params: HashMap<String, serde_json::Value>,
}

impl QueryStatement {
    /// Add a positional parameter
    pub fn param(mut self, key: &str, value: impl Into<serde_json::Value>) -> Self {
        self.params.insert(key.to_string(), value.into());
        self
    }
}

/// Query port for hexagonal architecture
///
/// This is the **port** in the hexagonal/ports-and-adapters pattern:
/// adapters (`PgBridge`, `SurrealBridge`) implement this trait; the domain
/// code (callers in `pheno-query` and beyond) only ever depends on the
/// `QueryPort` interface — never on a concrete adapter.
pub trait QueryPort {
    /// Plan a `QueryRequest` into a `QueryStatement` (port-side contract).
    /// Concrete adapters may also execute the planned statement in their
    /// own `impl` block; this trait only requires planning so the port
    /// stays sync.
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement>;
}

#[derive(Error, Debug)]
pub enum QueryError {
    #[error("invalid query: {0}")]
    InvalidQuery(String),
    #[error("execution failed: {0}")]
    ExecutionFailed(String),
    #[error("unsupported dataset backend: {0}")]
    UnsupportedBackend(String),
}

/// Unified query request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRequest {
    pub collection: String,
    pub filter: Option<Filter>,
    pub vector: Option<Vec<f32>>,
    pub limit: usize,
    pub offset: Option<usize>,
}

/// Filter conditions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Filter {
    pub field: String,
    pub operator: FilterOperator,
    pub value: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum FilterOperator {
    Eq,
    Ne,
    Gt,
    Gte,
    Lt,
    Lte,
    Contains,
    StartsWith,
    EndsWith,
}

/// Unified query response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse<T> {
    pub items: Vec<T>,
    pub total: usize,
    pub offset: usize,
    pub limit: usize,
}

/// Query builder trait
pub trait QueryBuilder {
    fn build(&self) -> Result<QueryStatement>;
}

/// Query planner with parameterized query support
pub struct QueryPlanner;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Surreal,
    Postgres,
}

/// Load backend from a source string.
///
/// Returns `QueryError::UnsupportedBackend` for unrecognised URI schemes.
#[instrument(skip(source), fields(source))]
pub fn load(source: &str) -> std::result::Result<Backend, QueryError> {
    if source.starts_with("surreal://") {
        tracing::debug!(backend = "Surreal", "resolved backend");
        return Ok(Backend::Surreal);
    }

    if source.starts_with("postgres://") || source.starts_with("postgresql://") {
        tracing::debug!(backend = "Postgres", "resolved backend");
        return Ok(Backend::Postgres);
    }

    Err(QueryError::UnsupportedBackend(source.to_string()))
}

impl QueryPlanner {
    /// Plan query for SurrealDB (parameterized)
    pub fn plan_surreal(req: &QueryRequest) -> QueryStatement {
        let mut query = format!("SELECT * FROM {}", req.collection);
        let mut params = HashMap::new();

        if let Some(ref filter) = req.filter {
            let param_key = "p0".to_string();
            params.insert(param_key.clone(), filter.value.clone());
            query.push_str(&format!(
                " WHERE {} {} $[\"{}\"]",
                filter.field,
                Self::op_to_string(&filter.operator),
                param_key
            ));
        }

        query.push_str(&format!(" LIMIT {}", req.limit));

        if let Some(offset) = req.offset {
            query.push_str(&format!(" START {}", offset));
        }

        QueryStatement { sql: query, params }
    }

    /// Plan query for PostgreSQL (parameterized)
    pub fn plan_postgres(req: &QueryRequest) -> QueryStatement {
        let mut query = format!("SELECT * FROM {}", req.collection);
        let mut params = HashMap::new();

        if let Some(ref filter) = req.filter {
            let param_key = "$1".to_string();
            params.insert(param_key.clone(), filter.value.clone());
            query.push_str(&format!(
                " WHERE {} {} {}",
                Self::pg_escape_identifier(&filter.field),
                Self::op_to_string(&filter.operator),
                param_key
            ));
        }

        query.push_str(&format!(" LIMIT {}", req.limit));
        if let Some(offset) = req.offset {
            query.push_str(&format!(" OFFSET {}", offset));
        }

        QueryStatement { sql: query, params }
    }

    fn pg_escape_identifier(ident: &str) -> String {
        // Only allow alphanumeric and underscore to prevent injection
        if ident.chars().all(|c| c.is_alphanumeric() || c == '_') {
            ident.to_string()
        } else {
            // Reject invalid identifiers
            String::new()
        }
    }

    fn op_to_string(op: &FilterOperator) -> &'static str {
        match op {
            FilterOperator::Eq => "=",
            FilterOperator::Ne => "!=",
            FilterOperator::Gt => ">",
            FilterOperator::Gte => ">=",
            FilterOperator::Lt => "<",
            FilterOperator::Lte => "<=",
            FilterOperator::Contains => "LIKE",
            FilterOperator::StartsWith => "LIKE",
            FilterOperator::EndsWith => "LIKE",
        }
    }
}

// ---------------------------------------------------------------------------
// Hexagonal port impls: thin newtype adapters that satisfy `QueryPort`
// by delegating to the static `QueryPlanner::plan_*` methods.
//
// This is the **D19** wiring that makes `phenoData` truly hexagonal:
// the domain (callers) depend on the `QueryPort` trait, not on
// `QueryPlanner`'s free functions. Adapters (`pg-bridge`,
// `surreal-bridge`) implement `QueryPort` for their bridge types.
// ---------------------------------------------------------------------------

/// SurrealDB-flavoured `QueryPort` adapter.
#[derive(Debug, Default, Clone, Copy)]
pub struct SurrealQueryPlanner;

impl QueryPort for SurrealQueryPlanner {
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement> {
        Ok(QueryPlanner::plan_surreal(req))
    }
}

/// PostgreSQL-flavoured `QueryPort` adapter.
#[derive(Debug, Default, Clone, Copy)]
pub struct PostgresQueryPlanner;

impl QueryPort for PostgresQueryPlanner {
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement> {
        Ok(QueryPlanner::plan_postgres(req))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plan_surreal() {
        let req = QueryRequest {
            collection: "skills".to_string(),
            filter: Some(Filter {
                field: "name".to_string(),
                operator: FilterOperator::Eq,
                value: serde_json::json!("test"),
            }),
            vector: None,
            limit: 10,
            offset: None,
        };

        let stmt = QueryPlanner::plan_surreal(&req);
        assert!(stmt.sql.contains("WHERE name = $[\"p0\"]"));
        assert!(stmt.sql.contains("LIMIT 10"));
        assert_eq!(stmt.params.get("p0"), Some(&serde_json::json!("test")));
    }

    #[test]
    fn test_plan_postgres() {
        let req = QueryRequest {
            collection: "skills".to_string(),
            filter: Some(Filter {
                field: "name".to_string(),
                operator: FilterOperator::Eq,
                value: serde_json::json!("test"),
            }),
            vector: None,
            limit: 10,
            offset: Some(5),
        };

        let stmt = QueryPlanner::plan_postgres(&req);
        assert!(stmt.sql.contains("WHERE name = $1"));
        assert!(stmt.sql.contains("LIMIT 10"));
        assert!(stmt.sql.contains("OFFSET 5"));
        assert_eq!(stmt.params.get("$1"), Some(&serde_json::json!("test")));
    }

    #[test]
    fn test_plan_no_filter() {
        let req = QueryRequest {
            collection: "skills".to_string(),
            filter: None,
            vector: None,
            limit: 10,
            offset: None,
        };

        let stmt = QueryPlanner::plan_surreal(&req);
        assert!(!stmt.sql.contains("WHERE"));
        assert!(stmt.sql.contains("LIMIT 10"));
    }

    // -----------------------------------------------------------------------
    // D19 hexagonal port tests
    // -----------------------------------------------------------------------

    /// Verify that a `QueryPort` trait object can dispatch to either
    /// backend (Surreal or Postgres) polymorphically. This is the
    /// hexagonal contract: callers depend on the trait, not on a
    /// concrete planner.
    #[test]
    fn test_query_port_dispatch_polymorphism() {
        let req = QueryRequest {
            collection: "skills".to_string(),
            filter: Some(Filter {
                field: "name".to_string(),
                operator: FilterOperator::Eq,
                value: serde_json::json!("test"),
            }),
            vector: None,
            limit: 10,
            offset: None,
        };

        let planners: Vec<Box<dyn QueryPort>> = vec![
            Box::new(SurrealQueryPlanner),
            Box::new(PostgresQueryPlanner),
        ];

        let stmts: Vec<QueryStatement> = planners.iter().map(|p| p.plan(&req).unwrap()).collect();
        // Surreal uses $[\"p0\"], Postgres uses $1
        assert!(stmts[0].sql.contains("WHERE name = $[\"p0\"]"));
        assert!(stmts[1].sql.contains("WHERE name = $1"));
        // Both have the param bound
        assert!(stmts[0].params.contains_key("p0"));
        assert!(stmts[1].params.contains_key("$1"));
    }

    /// Verify the planner newtypes are zero-sized / `Copy` so they can
    /// be passed around freely (e.g. embedded in adapter `new` calls).
    #[test]
    fn test_planner_newtypes_are_copy() {
        let s1 = SurrealQueryPlanner;
        let s2 = s1; // Copy
        let _ = s1; // s1 still usable after copy

        let p1 = PostgresQueryPlanner;
        let p2 = p1;
        let _ = p1;

        // Smoke: both still plan.
        let req = QueryRequest {
            collection: "t".to_string(),
            filter: None,
            vector: None,
            limit: 1,
            offset: None,
        };
        assert!(s2.plan(&req).is_ok());
        assert!(p2.plan(&req).is_ok());
    }

    #[test]
    fn test_load_returns_typed_error() {
        let result = load("sqlite:///tmp/db");
        match result {
            Err(QueryError::UnsupportedBackend(msg)) => {
                assert!(msg.contains("sqlite"));
            }
            _ => panic!("expected UnsupportedBackend error"),
        }
    }

    #[test]
    fn test_load_surreal_ok() {
        assert_eq!(load("surreal://embedded/pheno").unwrap(), Backend::Surreal);
    }

    #[test]
    fn test_load_postgres_ok() {
        assert_eq!(load("postgres://localhost/db").unwrap(), Backend::Postgres);
        assert_eq!(
            load("postgresql://localhost/db").unwrap(),
            Backend::Postgres
        );
    }
}
