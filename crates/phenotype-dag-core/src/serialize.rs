//! # DAG schema serialization (YAML / JSON)
//!
//! Round-trip serialization for [`DagSchema`](crate::schema::DagSchema).
//!
//! Renamed 2026-09-01: this module was previously exposed under
//! `pheno_dag::serialize::*`. The rename is path-breaking for downstream
//! consumers but is necessary to break the name collision with the
//! absorbed Go source `KooshaPari/phenodag`. See
//! `ADR-dag-collision-phenodag-phenodag-2026-09-01.md` for rationale.
//!
//! Provides a portable [`DagSchema`] that uses the enriched [`SchemaNode`]
//! and [`SchemaEdge`] types with prerequisites, acceptance criteria, and
//! audit hooks, defined in [`crate::schema`].
//!
//! # Example
//!
//! ```rust
//! use phenotype_dag_core::dag::Dag;
//! use phenotype_dag_core::serialize::DagSchema;
//!
//! let mut dag: Dag<String> = Dag::new();
//! dag.add_node("build".into()).unwrap();
//! dag.add_node("test".into()).unwrap();
//! dag.add_node("deploy".into()).unwrap();
//! dag.add_edge("build".into(), "test".into()).unwrap();
//! dag.add_edge("test".into(), "deploy".into()).unwrap();
//!
//! let schema = DagSchema::from_dag(&dag, "2.0.0");
//! let yaml = schema.to_yaml().unwrap();
//! let round: DagSchema = DagSchema::from_yaml(&yaml).unwrap();
//! assert_eq!(schema, round);
//! ```

use std::collections::BTreeSet;

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::dag::Dag;
use crate::schema::{SchemaEdge, SchemaNode};

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during DAG serialization / deserialization.
#[derive(Debug, Error)]
pub enum DagSerError {
    /// A YAML serialization or deserialization error occurred.
    #[error("YAML error: {0}")]
    Yaml(#[from] serde_yaml::Error),
    /// A JSON serialization or deserialization error occurred.
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// DagSchema — portable, serde-friendly, enriched DAG representation
// ---------------------------------------------------------------------------

/// Portable, serializable, enriched DAG representation.
///
/// Extends the basic node/edge structure with prerequisites, acceptance
/// criteria, audit hooks, and metadata.
///
/// This type is the **only** entry point for YAML / JSON serialization
/// of the enriched schema.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DagSchema {
    /// Schema version (e.g. "2.0.0").
    pub version: String,
    /// DAG name (optional).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    /// Nodes in the graph.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub nodes: Vec<SchemaNode>,
    /// Directed edges.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub edges: Vec<SchemaEdge>,
}

/// Construction and serialization methods for [`DagSchema`].
impl DagSchema {
    /// Build a `DagSchema` from an internal `Dag` keyed by `String`.
    ///
    /// `version` is a free-form version string (e.g. `"2.0.0"`).
    ///
    /// The enriched fields (prerequisites, acceptance, audit hooks) are
    /// left empty in the auto-generated nodes; consumers should populate
    /// them on the returned schema before serializing.
    pub fn from_dag(dag: &Dag<String>, version: impl Into<String>) -> Self {
        let nodes: Vec<SchemaNode> = dag
            .iter_nodes()
            .map(|id| SchemaNode {
                id: id.clone(),
                label: None,
                description: None,
                prerequisites: Vec::new(),
                acceptance: Vec::new(),
                audit_hooks: Vec::new(),
                metadata: None,
            })
            .collect();

        // Collect deduplicated edges.
        let mut edges_set: BTreeSet<(String, String)> = BTreeSet::new();
        for node in dag.iter_nodes() {
            if let Some(children) = dag.children_of(node) {
                for child in children {
                    edges_set.insert((node.clone(), child.clone()));
                }
            }
        }
        let edges: Vec<SchemaEdge> = edges_set
            .into_iter()
            .map(|(from, to)| SchemaEdge {
                from,
                to,
                label: None,
                condition: None,
            })
            .collect();

        Self {
            version: version.into(),
            name: None,
            nodes,
            edges,
        }
    }

    /// Set an optional name on the schema.
    pub fn with_name(mut self, name: impl Into<String>) -> Self {
        self.name = Some(name.into());
        self
    }

    /// Reconstruct an internal `Dag<String>` from this schema.
    ///
    /// Returns an error if a duplicate node is encountered.
    pub fn into_dag(self) -> Result<Dag<String>, crate::dag::DagError> {
        let mut dag = Dag::new();
        for node in &self.nodes {
            dag.add_node(node.id.clone())?;
        }
        for edge in &self.edges {
            dag.add_edge(edge.from.clone(), edge.to.clone())?;
        }
        Ok(dag)
    }

    // -----------------------------------------------------------------------
    // YAML
    // -----------------------------------------------------------------------

    /// Serialize to a YAML string.
    pub fn to_yaml(&self) -> Result<String, DagSerError> {
        Ok(serde_yaml::to_string(self)?)
    }

    /// Deserialize from a YAML string.
    pub fn from_yaml(yaml: &str) -> Result<Self, DagSerError> {
        Ok(serde_yaml::from_str(yaml)?)
    }

    // -----------------------------------------------------------------------
    // JSON
    // -----------------------------------------------------------------------

    /// Serialize to a compact JSON string.
    pub fn to_json(&self) -> Result<String, DagSerError> {
        Ok(serde_json::to_string(self)?)
    }

    /// Serialize to a pretty-printed JSON string.
    pub fn to_json_pretty(&self) -> Result<String, DagSerError> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    /// Deserialize from a JSON string.
    pub fn from_json(json: &str) -> Result<Self, DagSerError> {
        Ok(serde_json::from_str(json)?)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::schema::*;

    fn sample_dag() -> Result<Dag<String>, crate::dag::DagError> {
        let mut dag = Dag::new();
        for n in ["checkout", "build", "test", "deploy"] {
            dag.add_node(n.to_string())?;
        }
        dag.add_edge("checkout".into(), "build".into())?;
        dag.add_edge("build".into(), "test".into())?;
        dag.add_edge("test".into(), "deploy".into())?;
        Ok(dag)
    }

    fn enriched_schema() -> Result<DagSchema, crate::dag::DagError> {
        let dag = sample_dag()?;
        let mut schema = DagSchema::from_dag(&dag, "2.0.0").with_name("ci-pipeline");

        for node in &mut schema.nodes {
            if node.id == "build" {
                node.description = Some("Compile the application".into());
                node.prerequisites = vec![
                    Prerequisite::FileExists {
                        path: "./Cargo.toml".into(),
                    },
                    Prerequisite::EnvironmentVariable {
                        variable: "RUSTFLAGS".into(),
                    },
                ];
                node.acceptance = vec![
                    AcceptanceCriterion::ExitCode { code: 0 },
                    AcceptanceCriterion::OutputContains {
                        pattern: "Compiling".into(),
                        regex: false,
                    },
                ];
                node.audit_hooks = vec![AuditHook::MetricEmit {
                    name: "build_duration_ms".into(),
                    value: 0.0,
                    unit: Some("ms".into()),
                    timing: HookTiming::Post,
                }];
            }
            if node.id == "deploy" {
                node.prerequisites = vec![Prerequisite::ImageReady {
                    image: "myapp:latest".into(),
                }];
                node.acceptance = vec![AcceptanceCriterion::HttpOk {
                    url: "https://staging.example.com/health".into(),
                    expected_status: Some(200),
                }];
                node.audit_hooks = vec![AuditHook::Notify {
                    channel: "slack".into(),
                    message: "Deploy completed".into(),
                    timing: HookTiming::OnSuccess,
                }];
            }
        }

        Ok(schema)
    }

    #[test]
    fn yaml_round_trip_basic() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "2.0.0").with_name("pipeline");
        let yaml = schema.to_yaml()?;
        let restored = DagSchema::from_yaml(&yaml)?;
        assert_eq!(schema, restored, "YAML round-trip must be lossless");
        Ok(())
    }

    #[test]
    fn json_round_trip_basic() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "2.0.0");
        let json = schema.to_json()?;
        let restored = DagSchema::from_json(&json)?;
        assert_eq!(schema, restored, "JSON round-trip must be lossless");
        Ok(())
    }

    #[test]
    fn yaml_round_trip_enriched() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let yaml = schema
            .to_yaml()?;
        let restored = DagSchema::from_yaml(&yaml)?;
        assert_eq!(
            schema, restored,
            "Enriched YAML round-trip must be lossless"
        );
        Ok(())
    }

    #[test]
    fn json_round_trip_enriched() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let json = schema
            .to_json_pretty()?;
        let restored = DagSchema::from_json(&json)?;
        assert_eq!(
            schema, restored,
            "Enriched JSON round-trip must be lossless"
        );
        Ok(())
    }

    #[test]
    fn cross_format_consistency() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let yaml = schema.to_yaml()?;
        let from_yaml = DagSchema::from_yaml(&yaml)?;
        let json = from_yaml.to_json()?;
        let from_json = DagSchema::from_json(&json)?;
        assert_eq!(
            schema, from_json,
            "YAML → JSON cross-format must be consistent"
        );
        Ok(())
    }
    #[test]
    fn schema_to_dag_and_back() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "2.0.0");
        let reconstructed = schema.into_dag()?;
        assert_eq!(dag.node_count(), reconstructed.node_count());
        assert_eq!(dag.edge_count(), reconstructed.edge_count());
        for n in dag.iter_nodes() {
            assert!(reconstructed.contains(n), "node {n} should exist");
        }
        Ok(())
    }

    #[test]
    fn empty_dag_round_trips() -> Result<(), Box<dyn std::error::Error>> {
        let dag: Dag<String> = Dag::new();
        let schema = DagSchema::from_dag(&dag, "0.1.0");
        let yaml = schema.to_yaml()?;
        let back = DagSchema::from_yaml(&yaml)?;
        assert_eq!(schema, back);
        Ok(())
    }

    #[test]
    fn yaml_content_is_readable() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let yaml = schema.to_yaml()?;
        assert!(yaml.contains("version:"));
        assert!(yaml.contains("ci-pipeline"));
        assert!(yaml.contains("checkout"));
        assert!(yaml.contains("deploy"));
        assert!(yaml.contains("prerequisites"));
        assert!(yaml.contains("acceptance"));
        assert!(yaml.contains("audit_hooks"));
        Ok(())
    }

    #[test]
    fn json_content_is_readable() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let json = schema.to_json_pretty()?;
        assert!(json.contains("\"version\""));
        assert!(json.contains("\"checkout\""));
        assert!(json.contains("\"deploy\""));
        assert!(json.contains("\"prerequisites\""));
        Ok(())
    }

    #[test]
    fn diamond_graph_round_trip() -> Result<(), Box<dyn std::error::Error>> {
        let mut dag = Dag::new();
        for n in ["a", "b", "c", "d"] {
            dag.add_node(n.to_string())?;
        }
        dag.add_edge("a".into(), "b".into())?;
        dag.add_edge("a".into(), "c".into())?;
        dag.add_edge("b".into(), "d".into())?;
        dag.add_edge("c".into(), "d".into())?;

        let schema = DagSchema::from_dag(&dag, "1.0.0");
        let json = schema.to_json()?;
        let back = DagSchema::from_json(&json)?;
        assert_eq!(schema, back);
        assert_eq!(back.edges.len(), 4);
        Ok(())
    }

    #[test]
    fn enriched_schema_has_correct_prereqs() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let build_node = schema.nodes.iter().find(|n| n.id == "build").ok_or("build node not found")?;
        assert_eq!(build_node.prerequisites.len(), 2);
        assert_eq!(build_node.acceptance.len(), 2);
        assert_eq!(build_node.audit_hooks.len(), 1);

        let deploy_node = schema.nodes.iter().find(|n| n.id == "deploy").ok_or("deploy node not found")?;
        assert_eq!(deploy_node.prerequisites.len(), 1);
        assert_eq!(deploy_node.acceptance.len(), 1);
        assert_eq!(deploy_node.audit_hooks.len(), 1);
        Ok(())
    }

    // ---- New tests below ----

    #[test]
    fn into_dag_preserves_edges() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        let reconstructed = schema.into_dag()?;
        assert_eq!(reconstructed.edge_count(), 3);
        assert_eq!(reconstructed.children_of(&"build".to_string()), Some(&["test".to_string()][..]));
        assert_eq!(reconstructed.children_of(&"test".to_string()), Some(&["deploy".to_string()][..]));
        Ok(())
    }

    #[test]
    fn version_is_preserved() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "3.14.159");
        let json = schema.to_json()?;
        let restored = DagSchema::from_json(&json)?;
        assert_eq!(restored.version, "3.14.159");
        Ok(())
    }

    #[test]
    fn name_is_set_via_builder() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "1.0.0").with_name("my-pipeline");
        assert_eq!(schema.name.as_deref(), Some("my-pipeline"));
        let yaml = schema.to_yaml()?;
        assert!(yaml.contains("my-pipeline"));
        Ok(())
    }

    #[test]
    fn name_absent_by_default() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        assert!(schema.name.is_none());
        let yaml = schema.to_yaml()?;
        // Name should not appear when None.
        assert!(!yaml.contains("name:"));
        Ok(())
    }

    #[test]
    fn duplicate_edges_deduplicated_in_schema() -> Result<(), Box<dyn std::error::Error>> {
        let mut dag = Dag::new();
        dag.add_node("a".to_string())?;
        dag.add_node("b".to_string())?;
        // Add the same edge twice (Dag allows it in the adjacency list).
        dag.add_edge("a".into(), "b".into())?;
        dag.add_edge("a".into(), "b".into())?;
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        // BTreeSet dedup should ensure only one edge a→b.
        let a_to_b: Vec<_> = schema.edges.iter().filter(|e| e.from == "a" && e.to == "b").collect();
        assert_eq!(a_to_b.len(), 1, "duplicate edges should be deduplicated");
        Ok(())
    }

    #[test]
    fn from_json_invalid_input() {
        let result = DagSchema::from_json("not valid json {{{");
        assert!(result.is_err());
    }

    #[test]
    fn from_yaml_invalid_input() {
        let result = DagSchema::from_yaml(":::invalid yaml: [");
        assert!(result.is_err());
    }

    #[test]
    fn json_pretty_is_multiline() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        let pretty = schema.to_json_pretty()?;
        // Pretty-printed JSON should have newlines.
        assert!(pretty.contains('\n'));
        let compact = schema.to_json()?;
        assert!(!compact.contains('\n'), "compact JSON should be single line");
        Ok(())
    }

    #[test]
    fn schema_nodes_sorted_deterministically() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        // Nodes come from a HashSet so order isn't guaranteed, but we can verify
        // all nodes are present.
        let ids: Vec<&str> = schema.nodes.iter().map(|n| n.id.as_str()).collect();
        assert_eq!(ids.len(), 4);
        assert!(ids.contains(&"checkout"));
        assert!(ids.contains(&"build"));
        assert!(ids.contains(&"test"));
        assert!(ids.contains(&"deploy"));
        Ok(())
    }

    #[test]
    fn into_dag_round_trip_preserves_node_count() -> Result<(), Box<dyn std::error::Error>> {
        let dag = sample_dag()?;
        let count = dag.node_count();
        let schema = DagSchema::from_dag(&dag, "1.0.0");
        let reconstructed = schema.into_dag()?;
        assert_eq!(reconstructed.node_count(), count);
        Ok(())
    }

    #[test]
    fn enriched_round_trip_preserves_all_metadata() -> Result<(), Box<dyn std::error::Error>> {
        let schema = enriched_schema()?;
        let json = schema.to_json()?;
        let restored = DagSchema::from_json(&json)?;
        // Verify metadata survives round-trip.
        let build = restored.nodes.iter().find(|n| n.id == "build").unwrap();
        assert_eq!(build.description.as_deref(), Some("Compile the application"));
        assert_eq!(build.prerequisites.len(), 2);
        Ok(())
    }
}
