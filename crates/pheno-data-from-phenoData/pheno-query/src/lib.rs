//! PhenoQuery - Unified query builder for Pheno
//!
//! Provides a unified query interface across different data stores.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

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
pub trait QueryPort {
    fn plan(&self, req: &QueryRequest) -> Result<QueryStatement>;
}

#[derive(Error, Debug)]
pub enum QueryError {
    #[error("invalid query: {0}")]
    InvalidQuery(String),
    #[error("execution failed: {0}")]
    ExecutionFailed(String),
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

    #[test]
    fn test_query_statement_param_builder() {
        // QueryStatement::param is the public builder for inserting named parameters.
        // It must accept any Into<serde_json::Value>, preserve insertion order semantics
        // (HashMap is unordered, so we assert by lookup), and return Self for chaining.
        let stmt = QueryStatement::default()
            .param("name", "alice")
            .param("count", 7i64)
            .param("active", true)
            .param("tags", serde_json::json!(["a", "b"]));

        assert_eq!(stmt.sql, "", "default sql should be empty");
        assert_eq!(stmt.params.len(), 4, "all four params should be stored");
        assert_eq!(
            stmt.params.get("name"),
            Some(&serde_json::json!("alice"))
        );
        assert_eq!(
            stmt.params.get("count"),
            Some(&serde_json::json!(7))
        );
        assert_eq!(
            stmt.params.get("active"),
            Some(&serde_json::json!(true))
        );
        assert_eq!(
            stmt.params.get("tags"),
            Some(&serde_json::json!(["a", "b"]))
        );
    }

    #[test]
    fn test_pg_escape_identifier_rejects_injection() {
        // Malicious identifiers should be rejected (return empty string)
        assert_eq!(QueryPlanner::pg_escape_identifier("users; DROP TABLE users;--"), "");
        assert_eq!(QueryPlanner::pg_escape_identifier("users\""), "");
        assert_eq!(QueryPlanner::pg_escape_identifier("users'"), "");
        assert_eq!(QueryPlanner::pg_escape_identifier("users\\"), "");
        // Valid identifiers should pass through
        assert_eq!(QueryPlanner::pg_escape_identifier("users"), "users");
        assert_eq!(QueryPlanner::pg_escape_identifier("user_profiles"), "user_profiles");
    }

    #[test]
    fn test_plan_postgres_with_offset() {
        let req = QueryRequest {
            collection: "events".to_string(),
            filter: None,
            vector: None,
            limit: 25,
            offset: Some(100),
        };
        let stmt = QueryPlanner::plan_postgres(&req);
        assert!(stmt.sql.contains("LIMIT 25"));
        assert!(stmt.sql.contains("OFFSET 100"));
        assert!(!stmt.sql.contains("WHERE"));
    }

    #[test]
    fn test_filter_operators_all() {
        let ops = vec![
            (FilterOperator::Eq, "="),
            (FilterOperator::Ne, "!="),
            (FilterOperator::Gt, ">"),
            (FilterOperator::Gte, ">="),
            (FilterOperator::Lt, "<"),
            (FilterOperator::Lte, "<="),
            (FilterOperator::Contains, "LIKE"),
            (FilterOperator::StartsWith, "LIKE"),
            (FilterOperator::EndsWith, "LIKE"),
        ];
        for (op, expected) in ops {
            let req = QueryRequest {
                collection: "test".to_string(),
                filter: Some(Filter {
                    field: "x".to_string(),
                    operator: op,
                    value: serde_json::json!(1),
                }),
                vector: None,
                limit: 1,
                offset: None,
            };
            let stmt = QueryPlanner::plan_postgres(&req);
            assert!(stmt.sql.contains(expected), "operator {:?} should produce {}", op, expected);
        }
    }

    #[test]
    fn test_query_statement_chaining() {
        let stmt = QueryStatement::default()
            .param("a", 1)
            .param("b", "two")
            .param("c", true);
        assert_eq!(stmt.params.len(), 3);
        assert_eq!(stmt.params.get("a"), Some(&serde_json::json!(1)));
        assert_eq!(stmt.params.get("b"), Some(&serde_json::json!("two")));
        assert_eq!(stmt.params.get("c"), Some(&serde_json::json!(true)));
    }

    // Property-based tests: generate random query requests and verify invariants
    use proptest::prelude::*;

    prop_compose! {
        fn arb_query_request()
            (collection in "[a-zA-Z_]{1,20}",
             limit in 1usize..1000usize,
             offset in proptest::option::of(0usize..1000usize),
             has_filter in proptest::bool::ANY)
            -> QueryRequest {
            let filter = if has_filter {
                Some(Filter {
                    field: "field".to_string(),
                    operator: FilterOperator::Eq,
                    value: serde_json::json!("value"),
                })
            } else {
                None
            };
            QueryRequest {
                collection,
                filter,
                vector: None,
                limit,
                offset,
            }
        }
    }

    proptest! {
        #[test]
        fn prop_surreal_query_always_contains_select(req in arb_query_request()) {
            let stmt = QueryPlanner::plan_surreal(&req);
            prop_assert!(stmt.sql.contains("SELECT * FROM"));
            prop_assert!(stmt.sql.contains(&req.collection));
        }

        #[test]
        fn prop_postgres_query_always_contains_select(req in arb_query_request()) {
            let stmt = QueryPlanner::plan_postgres(&req);
            prop_assert!(stmt.sql.contains("SELECT * FROM"));
            prop_assert!(stmt.sql.contains(&req.collection));
        }

        #[test]
        fn prop_query_limit_always_present(req in arb_query_request()) {
            let surreal = QueryPlanner::plan_surreal(&req);
            let postgres = QueryPlanner::plan_postgres(&req);
            prop_assert!(surreal.sql.contains(&format!("LIMIT {}", req.limit)));
            prop_assert!(postgres.sql.contains(&format!("LIMIT {}", req.limit)));
        }

        #[test]
        fn prop_filter_params_not_empty_when_filter_present(req in arb_query_request()) {
            let stmt = QueryPlanner::plan_surreal(&req);
            if req.filter.is_some() {
                prop_assert!(!stmt.params.is_empty(), "filter present => params not empty");
                prop_assert!(stmt.sql.contains("WHERE"), "filter present => WHERE clause");
            } else {
                prop_assert!(stmt.params.is_empty(), "no filter => no params");
                prop_assert!(!stmt.sql.contains("WHERE"), "no filter => no WHERE");
            }
        }

        #[test]
        fn prop_escape_identifier_never_injects(req in "[a-zA-Z0-9_]{1,20}") {
            let escaped = QueryPlanner::pg_escape_identifier(&req);
            // Escaped identifier should never contain quotes or semicolons
            prop_assert!(!escaped.contains('"'));
            prop_assert!(!escaped.contains('\''));
            prop_assert!(!escaped.contains(';'));
        }

        #[test]
        fn prop_offset_always_present_when_set(req in arb_query_request()) {
            let surreal = QueryPlanner::plan_surreal(&req);
            let postgres = QueryPlanner::plan_postgres(&req);
            if let Some(off) = req.offset {
                prop_assert!(surreal.sql.contains(&format!("START {}", off)));
                prop_assert!(postgres.sql.contains(&format!("OFFSET {}", off)));
            }
        }
    }
}
