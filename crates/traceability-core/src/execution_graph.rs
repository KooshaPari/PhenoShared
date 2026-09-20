//! Execution Graph ontology — type-safe graph model for runtime/CI/test execution:
//! the **runtime counterpart** to the [`crate::intent_graph::IntentGraph`] (PM side).
//!
//! "Two graphs, one product":
//!
//! * [`IntentGraph`] models *what should exist* — Intent, Feature, Task, Spec, PR…
//! * [`ExecutionGraph`] models *what actually ran* — Build, Test, Deploy, Job, with
//!   concrete statuses, durations, and DAG edges between them.
//!
//! Both graphs share a uniform style (`NodeType` + `Edge` + `Meta` + validate/cycle
//! detection) so consumers can apply the same traversal/diff machinery to either.
//!
//! Source of inspiration: [`AgilePlus/crates/agileplus-domain/src/intent_graph.rs`](https://example.invalid/AgilePlus/crates/agileplus-domain/src/intent_graph.rs)
//! — runtime DAG is the dual of the intent DAG.

use std::collections::{HashMap, HashSet};
use std::fmt;

use chrono::{DateTime, Utc};
use regex::Regex;
use serde::{Deserialize, Serialize};
use thiserror::Error;

/// ---------------------------------------------------------------------------
/// Execution Node Type — the kinds of runtime units we track.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub enum ExecutionNodeType {
    Build,
    Test,
    Deploy,
    Job,
}

impl fmt::Display for ExecutionNodeType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            ExecutionNodeType::Build => "Build",
            ExecutionNodeType::Test => "Test",
            ExecutionNodeType::Deploy => "Deploy",
            ExecutionNodeType::Job => "Job",
        };
        write!(f, "{s}")
    }
}

impl From<&str> for ExecutionNodeType {
    fn from(s: &str) -> Self {
        match s {
            "Build" => ExecutionNodeType::Build,
            "Test" => ExecutionNodeType::Test,
            "Deploy" => ExecutionNodeType::Deploy,
            "Job" => ExecutionNodeType::Job,
            _ => panic!("unknown ExecutionNodeType: {s}"),
        }
    }
}

impl TryFrom<String> for ExecutionNodeType {
    type Error = ExecutionValidationError;
    fn try_from(s: String) -> Result<Self, Self::Error> {
        match s.as_str() {
            "Build" => Ok(ExecutionNodeType::Build),
            "Test" => Ok(ExecutionNodeType::Test),
            "Deploy" => Ok(ExecutionNodeType::Deploy),
            "Job" => Ok(ExecutionNodeType::Job),
            _ => Err(ExecutionValidationError::UnknownNodeType(s)),
        }
    }
}

/// ---------------------------------------------------------------------------
/// Execution Status — lifecycle of a single runtime node.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExecutionStatus {
    Pending,
    Queued,
    Running,
    Passed,
    Failed,
    Skipped,
    Cancelled,
}

impl fmt::Display for ExecutionStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            ExecutionStatus::Pending => "pending",
            ExecutionStatus::Queued => "queued",
            ExecutionStatus::Running => "running",
            ExecutionStatus::Passed => "passed",
            ExecutionStatus::Failed => "failed",
            ExecutionStatus::Skipped => "skipped",
            ExecutionStatus::Cancelled => "cancelled",
        };
        write!(f, "{s}")
    }
}

impl From<&str> for ExecutionStatus {
    fn from(s: &str) -> Self {
        match s {
            "pending" => ExecutionStatus::Pending,
            "queued" => ExecutionStatus::Queued,
            "running" => ExecutionStatus::Running,
            "passed" => ExecutionStatus::Passed,
            "failed" => ExecutionStatus::Failed,
            "skipped" => ExecutionStatus::Skipped,
            "cancelled" => ExecutionStatus::Cancelled,
            _ => panic!("unknown ExecutionStatus: {s}"),
        }
    }
}

impl TryFrom<String> for ExecutionStatus {
    type Error = ExecutionValidationError;
    fn try_from(s: String) -> Result<Self, Self::Error> {
        match s.as_str() {
            "pending" => Ok(ExecutionStatus::Pending),
            "queued" => Ok(ExecutionStatus::Queued),
            "running" => Ok(ExecutionStatus::Running),
            "passed" => Ok(ExecutionStatus::Passed),
            "failed" => Ok(ExecutionStatus::Failed),
            "skipped" => Ok(ExecutionStatus::Skipped),
            "cancelled" => Ok(ExecutionStatus::Cancelled),
            _ => Err(ExecutionValidationError::UnknownStatus(s)),
        }
    }
}

/// ---------------------------------------------------------------------------
/// Execution Edge Type — runtime causality between nodes.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExecutionEdgeType {
    /// `source` must complete before `target` can start (e.g. build before test).
    Triggers,
    /// Hard ordering constraint; `target` consumes an artifact of `source`.
    DependsOn,
    /// `source` produces a deployable artifact consumed by `target`.
    Produces,
    /// `source` runs the same workload on a different shard of `target`.
    ParallelTo,
}

impl fmt::Display for ExecutionEdgeType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            ExecutionEdgeType::Triggers => "triggers",
            ExecutionEdgeType::DependsOn => "depends_on",
            ExecutionEdgeType::Produces => "produces",
            ExecutionEdgeType::ParallelTo => "parallel_to",
        };
        write!(f, "{s}")
    }
}

impl From<&str> for ExecutionEdgeType {
    fn from(s: &str) -> Self {
        match s {
            "triggers" => ExecutionEdgeType::Triggers,
            "depends_on" => ExecutionEdgeType::DependsOn,
            "produces" => ExecutionEdgeType::Produces,
            "parallel_to" => ExecutionEdgeType::ParallelTo,
            _ => panic!("unknown ExecutionEdgeType: {s}"),
        }
    }
}

impl TryFrom<String> for ExecutionEdgeType {
    type Error = ExecutionValidationError;
    fn try_from(s: String) -> Result<Self, Self::Error> {
        match s.as_str() {
            "triggers" => Ok(ExecutionEdgeType::Triggers),
            "depends_on" => Ok(ExecutionEdgeType::DependsOn),
            "produces" => Ok(ExecutionEdgeType::Produces),
            "parallel_to" => Ok(ExecutionEdgeType::ParallelTo),
            _ => Err(ExecutionValidationError::UnknownEdgeType(s)),
        }
    }
}

/// ---------------------------------------------------------------------------
/// Meta — mirrors `intent_graph::Meta` (source + agent + timestamp + confidence).
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionMeta {
    /// Confidence score from 0.0 to 1.0.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
    /// Origin of the data (e.g., "ci-runner", "github-actions", "local").
    pub source: String,
    /// ISO 8601 timestamp when this element was created or last modified.
    pub timestamp: DateTime<Utc>,
    /// Identifier of the runner or system that produced this element.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
}

/// ---------------------------------------------------------------------------
/// Execution Node — a single runtime unit.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionNode {
    /// Globally unique node ID. Format: `<Type>#<slug>`.
    pub id: String,
    pub node_type: ExecutionNodeType,
    pub title: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    pub status: ExecutionStatus,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
    pub meta: ExecutionMeta,
    /// Wall-clock duration of the run, milliseconds. None while pending/queued.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration_ms: Option<u64>,
    /// When the run started (UTC).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub started_at: Option<DateTime<Utc>>,
    /// When the run finished (UTC).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub finished_at: Option<DateTime<Utc>>,
    /// Free-form runner-specific payload (job URL, artifact refs, exit code, etc.).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub properties: Option<serde_json::Value>,
}

/// ---------------------------------------------------------------------------
/// Execution Edge — a directed runtime relationship.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionEdge {
    pub id: String,
    pub source: String,
    pub target: String,
    pub edge_type: ExecutionEdgeType,
    pub meta: ExecutionMeta,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub properties: Option<serde_json::Value>,
}

/// ---------------------------------------------------------------------------
/// Graph Metadata — parallel to `intent_graph::GraphMetadata`.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionGraphMetadata {
    pub version: String,
    pub schema_uri: String,
    pub created_at: DateTime<Utc>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub updated_at: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub node_count: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub edge_count: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dag_valid: Option<bool>,
    /// e.g. "github-actions", "buildkite", "local".
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runner: Option<String>,
    /// Human label for the run (e.g. "PR #42 / cargo-test").
    #[serde(skip_serializing_if = "Option::is_none")]
    pub run_label: Option<String>,
}

/// ---------------------------------------------------------------------------
/// Execution Graph — the runtime DAG.
/// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionGraph {
    pub nodes: Vec<ExecutionNode>,
    pub edges: Vec<ExecutionEdge>,
    pub metadata: ExecutionGraphMetadata,
}

/// ---------------------------------------------------------------------------
/// Validation Error — kept local to this module so the intent graph's
/// vocabulary (NodeType, Status) doesn't leak into runtime errors and vice-versa.
/// ---------------------------------------------------------------------------
#[derive(Debug, Error, Clone, PartialEq)]
pub enum ExecutionValidationError {
    #[error("invalid execution node ID: {0}")]
    InvalidNodeId(String),
    #[error("missing required field: {0}")]
    MissingRequiredField(String),
    #[error("unknown execution node type: {0}")]
    UnknownNodeType(String),
    #[error("unknown execution status: {0}")]
    UnknownStatus(String),
    #[error("unknown execution edge type: {0}")]
    UnknownEdgeType(String),
    #[error("invalid edge constraint: {edge} from {from} to {to}")]
    InvalidEdgeConstraint {
        edge: String,
        from: String,
        to: String,
    },
    #[error("cycle detected in execution graph")]
    CycleDetected,
    #[error("missing meta on {0}")]
    MissingMeta(String),
    #[error("duplicate node ID: {0}")]
    DuplicateNodeId(String),
    #[error("orphaned edge: {edge_id} references missing node {node_id}")]
    OrphanedEdge { edge_id: String, node_id: String },
    #[error("confidence out of range: {0}")]
    ConfidenceOutOfRange(f64),
    #[error("self-loop edge: {0}")]
    SelfLoop(String),
    #[error("duration set on non-terminal status: node {0} status {1}")]
    DurationOnNonTerminal(String, String),
}

// ---------------------------------------------------------------------------
// ID validation — mirrors intent_graph's `<Type>#<slug>` convention.
// ---------------------------------------------------------------------------
fn node_id_regex() -> &'static Regex {
    static RE: std::sync::OnceLock<Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^[A-Z][a-z]+#[a-z0-9\-]+$").unwrap())
}

fn is_valid_node_id(id: &str) -> bool {
    node_id_regex().is_match(id)
}

// ---------------------------------------------------------------------------
// Edge constraint rules — runtime causality is more permissive than intent:
// the shape that matters is "thing that runs" -> "thing that runs".
// `ParallelTo` is undirected in spirit, encoded as a directed edge for storage.
// ---------------------------------------------------------------------------
fn allowed_edge_constraints(
    edge: ExecutionEdgeType,
) -> &'static [(ExecutionNodeType, ExecutionNodeType)] {
    use ExecutionEdgeType::*;
    use ExecutionNodeType::*;
    static TRIGGERS: &[(ExecutionNodeType, ExecutionNodeType)] = &[
        (Build, Test),
        (Build, Deploy),
        (Test, Deploy),
        (Job, Build),
        (Job, Test),
        (Job, Deploy),
    ];
    static DEPENDS_ON: &[(ExecutionNodeType, ExecutionNodeType)] = &[
        (Build, Build),
        (Test, Test),
        (Deploy, Deploy),
        (Test, Build),
        (Deploy, Build),
        (Deploy, Test),
    ];
    static PRODUCES: &[(ExecutionNodeType, ExecutionNodeType)] =
        &[(Build, Deploy), (Build, Test), (Job, Build)];
    // ParallelTo: any pair allowed.
    static PARALLEL_TO: &[(ExecutionNodeType, ExecutionNodeType)] = &[];
    match edge {
        Triggers => TRIGGERS,
        DependsOn => DEPENDS_ON,
        Produces => PRODUCES,
        ParallelTo => PARALLEL_TO,
    }
}

// ---------------------------------------------------------------------------
// ExecutionGraph validation
// ---------------------------------------------------------------------------
impl ExecutionGraph {
    /// Validate the entire graph, collecting all errors.
    pub fn validate(&self) -> Result<(), Vec<ExecutionValidationError>> {
        let mut errors = Vec::new();

        // --- node-level checks ---
        let mut seen_ids = HashSet::new();
        for node in &self.nodes {
            if !is_valid_node_id(&node.id) {
                errors.push(ExecutionValidationError::InvalidNodeId(node.id.clone()));
            }
            if !seen_ids.insert(node.id.clone()) {
                errors.push(ExecutionValidationError::DuplicateNodeId(node.id.clone()));
            }
            if node.meta.source.trim().is_empty() {
                errors.push(ExecutionValidationError::MissingMeta(format!(
                    "node {}: source is empty",
                    node.id
                )));
            }
            if let Some(c) = node.meta.confidence {
                if !(0.0..=1.0).contains(&c) {
                    errors.push(ExecutionValidationError::ConfidenceOutOfRange(c));
                }
            }
            // duration must only be set on a terminal status
            if node.duration_ms.is_some()
                && !matches!(
                    node.status,
                    ExecutionStatus::Passed
                        | ExecutionStatus::Failed
                        | ExecutionStatus::Skipped
                        | ExecutionStatus::Cancelled
                )
            {
                errors.push(ExecutionValidationError::DurationOnNonTerminal(
                    node.id.clone(),
                    node.status.to_string(),
                ));
            }
        }

        // --- edge-level checks ---
        let node_map: HashMap<String, &ExecutionNode> =
            self.nodes.iter().map(|n| (n.id.clone(), n)).collect();
        for edge in &self.edges {
            if let Some(e) = Self::check_edge_against_node_map(edge, &node_map) {
                errors.push(e);
            }
        }

        // --- DAG checks ---
        if let Err(e) = self.check_dag() {
            errors.push(e);
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    /// Check that the graph is acyclic.
    pub fn check_dag(&self) -> Result<(), ExecutionValidationError> {
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();
        for edge in &self.edges {
            adj.entry(edge.source.clone())
                .or_default()
                .push(edge.target.clone());
        }

        #[derive(Clone, Copy)]
        enum Color {
            White,
            Gray,
            Black,
        }
        let mut colors: HashMap<String, Color> = self
            .nodes
            .iter()
            .map(|n| (n.id.clone(), Color::White))
            .collect();

        fn dfs(
            node_id: &str,
            adj: &HashMap<String, Vec<String>>,
            colors: &mut HashMap<String, Color>,
        ) -> Result<(), ExecutionValidationError> {
            colors.insert(node_id.to_string(), Color::Gray);
            if let Some(neighbors) = adj.get(node_id) {
                for neighbor in neighbors {
                    match colors.get(neighbor).copied().unwrap_or(Color::White) {
                        Color::White => dfs(neighbor, adj, colors)?,
                        Color::Gray => return Err(ExecutionValidationError::CycleDetected),
                        Color::Black => {}
                    }
                }
            }
            colors.insert(node_id.to_string(), Color::Black);
            Ok(())
        }

        let node_ids: Vec<String> = self.nodes.iter().map(|n| n.id.clone()).collect();
        for node_id in &node_ids {
            if matches!(colors.get(node_id), Some(Color::White)) {
                dfs(node_id, &adj, &mut colors)?;
            }
        }
        Ok(())
    }

    /// Check edge constraints against the runtime ontology rules.
    pub fn check_edge_constraints(&self) -> Result<(), ExecutionValidationError> {
        let node_map: HashMap<String, &ExecutionNode> =
            self.nodes.iter().map(|n| (n.id.clone(), n)).collect();
        for edge in &self.edges {
            if let Some(e) = Self::check_edge_against_node_map(edge, &node_map) {
                return Err(e);
            }
        }
        Ok(())
    }

    fn check_edge_against_node_map(
        edge: &ExecutionEdge,
        node_map: &HashMap<String, &ExecutionNode>,
    ) -> Option<ExecutionValidationError> {
        let source_node = node_map.get(&edge.source)?;
        let target_node = node_map.get(&edge.target)?;

        // self-loop guard
        if edge.source == edge.target {
            return Some(ExecutionValidationError::SelfLoop(edge.id.clone()));
        }

        // meta source must be non-empty
        if edge.meta.source.trim().is_empty() {
            return Some(ExecutionValidationError::MissingMeta(format!(
                "edge {}: source is empty",
                edge.id
            )));
        }

        // confidence range
        if let Some(c) = edge.meta.confidence {
            if !(0.0..=1.0).contains(&c) {
                return Some(ExecutionValidationError::ConfidenceOutOfRange(c));
            }
        }

        // edge constraints (ParallelTo is wildcard)
        let allowed = allowed_edge_constraints(edge.edge_type);
        if edge.edge_type != ExecutionEdgeType::ParallelTo {
            let pair = (source_node.node_type, target_node.node_type);
            if !allowed.contains(&pair) {
                return Some(ExecutionValidationError::InvalidEdgeConstraint {
                    edge: edge.edge_type.to_string(),
                    from: source_node.node_type.to_string(),
                    to: target_node.node_type.to_string(),
                });
            }
        }

        None
    }

    /// Convenience: nodes with a terminal failure status.
    pub fn failed_nodes(&self) -> Vec<&ExecutionNode> {
        self.nodes
            .iter()
            .filter(|n| n.status == ExecutionStatus::Failed)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_meta() -> ExecutionMeta {
        ExecutionMeta {
            confidence: Some(0.9),
            source: "ci-runner".to_string(),
            timestamp: Utc::now(),
            agent_id: None,
        }
    }

    fn sample_node(
        id: &str,
        node_type: ExecutionNodeType,
        status: ExecutionStatus,
    ) -> ExecutionNode {
        ExecutionNode {
            id: id.to_string(),
            node_type,
            title: "Test".to_string(),
            description: None,
            status,
            tags: vec![],
            meta: sample_meta(),
            duration_ms: None,
            started_at: None,
            finished_at: None,
            properties: None,
        }
    }

    fn sample_edge(
        id: &str,
        source: &str,
        target: &str,
        edge_type: ExecutionEdgeType,
    ) -> ExecutionEdge {
        ExecutionEdge {
            id: id.to_string(),
            source: source.to_string(),
            target: target.to_string(),
            edge_type,
            meta: sample_meta(),
            properties: None,
        }
    }

    fn empty_metadata() -> ExecutionGraphMetadata {
        ExecutionGraphMetadata {
            version: "1.0.0".to_string(),
            schema_uri: "https://phenotype.dev/schemas/execution-ontology/v1.json".to_string(),
            created_at: Utc::now(),
            updated_at: None,
            node_count: None,
            edge_count: None,
            dag_valid: None,
            runner: None,
            run_label: None,
        }
    }

    #[test]
    fn execution_node_type_display_and_parse() {
        assert_eq!(ExecutionNodeType::Build.to_string(), "Build");
        assert_eq!(ExecutionNodeType::from("Test"), ExecutionNodeType::Test);
        assert_eq!(
            ExecutionNodeType::try_from("Deploy".to_string()).unwrap(),
            ExecutionNodeType::Deploy
        );
        assert!(ExecutionNodeType::try_from("Nope".to_string()).is_err());
    }

    #[test]
    fn execution_status_display_and_parse() {
        assert_eq!(ExecutionStatus::Running.to_string(), "running");
        assert_eq!(ExecutionStatus::from("passed"), ExecutionStatus::Passed);
        assert_eq!(
            ExecutionStatus::try_from("failed".to_string()).unwrap(),
            ExecutionStatus::Failed
        );
        assert!(ExecutionStatus::try_from("exploded".to_string()).is_err());
    }

    #[test]
    fn valid_node_id_passes() {
        assert!(is_valid_node_id("Build#cargo-build"));
        assert!(is_valid_node_id("Test#unit-auth"));
        assert!(is_valid_node_id("Job#ci-test-1"));
        assert!(is_valid_node_id("Deploy#prod-1"));
    }

    #[test]
    fn invalid_node_id_fails() {
        assert!(!is_valid_node_id("build#x"));
        assert!(!is_valid_node_id("Build#"));
        assert!(!is_valid_node_id("Build_x"));
        assert!(!is_valid_node_id("B#x"));
    }

    #[test]
    fn validate_ok_for_minimal_pipeline() {
        // Build -> Test -> Deploy
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node(
                    "Build#cargo",
                    ExecutionNodeType::Build,
                    ExecutionStatus::Passed,
                ),
                sample_node(
                    "Test#unit",
                    ExecutionNodeType::Test,
                    ExecutionStatus::Passed,
                ),
                sample_node(
                    "Deploy#prod",
                    ExecutionNodeType::Deploy,
                    ExecutionStatus::Pending,
                ),
            ],
            edges: vec![
                sample_edge(
                    "e1",
                    "Build#cargo",
                    "Test#unit",
                    ExecutionEdgeType::Triggers,
                ),
                sample_edge(
                    "e2",
                    "Test#unit",
                    "Deploy#prod",
                    ExecutionEdgeType::Triggers,
                ),
            ],
            metadata: empty_metadata(),
        };
        assert!(graph.validate().is_ok());
    }

    #[test]
    fn dag_detects_cycle() {
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node("Build#a", ExecutionNodeType::Build, ExecutionStatus::Passed),
                sample_node("Test#b", ExecutionNodeType::Test, ExecutionStatus::Passed),
            ],
            edges: vec![
                sample_edge("e1", "Build#a", "Test#b", ExecutionEdgeType::Triggers),
                sample_edge("e2", "Test#b", "Build#a", ExecutionEdgeType::DependsOn),
            ],
            metadata: empty_metadata(),
        };
        let err = graph.check_dag().unwrap_err();
        assert!(matches!(err, ExecutionValidationError::CycleDetected));
    }

    #[test]
    fn edge_constraint_rejects_invalid_pair() {
        // Test -> Test via Triggers is not allowed (Test->Build only via DependsOn)
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node("Test#a", ExecutionNodeType::Test, ExecutionStatus::Passed),
                sample_node("Test#b", ExecutionNodeType::Test, ExecutionStatus::Passed),
            ],
            edges: vec![sample_edge(
                "e1",
                "Test#a",
                "Test#b",
                ExecutionEdgeType::Triggers,
            )],
            metadata: empty_metadata(),
        };
        let err = graph.check_edge_constraints().unwrap_err();
        assert!(matches!(
            err,
            ExecutionValidationError::InvalidEdgeConstraint { .. }
        ));
    }

    #[test]
    fn parallel_to_allows_any_pair() {
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node("Test#a", ExecutionNodeType::Test, ExecutionStatus::Passed),
                sample_node("Test#b", ExecutionNodeType::Test, ExecutionStatus::Passed),
            ],
            edges: vec![sample_edge(
                "e1",
                "Test#a",
                "Test#b",
                ExecutionEdgeType::ParallelTo,
            )],
            metadata: empty_metadata(),
        };
        assert!(graph.check_edge_constraints().is_ok());
    }

    #[test]
    fn duration_on_non_terminal_status_rejected() {
        let mut graph = ExecutionGraph {
            nodes: vec![sample_node(
                "Test#a",
                ExecutionNodeType::Test,
                ExecutionStatus::Running,
            )],
            edges: vec![],
            metadata: empty_metadata(),
        };
        graph.nodes[0].duration_ms = Some(1200);
        let err = graph.validate().unwrap_err();
        assert!(err
            .iter()
            .any(|e| matches!(e, ExecutionValidationError::DurationOnNonTerminal(_, _))));
    }

    #[test]
    fn self_loop_edge_rejected() {
        let graph = ExecutionGraph {
            nodes: vec![sample_node(
                "Build#a",
                ExecutionNodeType::Build,
                ExecutionStatus::Passed,
            )],
            edges: vec![sample_edge(
                "e1",
                "Build#a",
                "Build#a",
                ExecutionEdgeType::DependsOn,
            )],
            metadata: empty_metadata(),
        };
        let err = graph.validate().unwrap_err();
        assert!(err
            .iter()
            .any(|e| matches!(e, ExecutionValidationError::SelfLoop(_))));
    }

    #[test]
    fn failed_nodes_filter() {
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node("Build#a", ExecutionNodeType::Build, ExecutionStatus::Passed),
                sample_node("Test#a", ExecutionNodeType::Test, ExecutionStatus::Failed),
                sample_node("Test#b", ExecutionNodeType::Test, ExecutionStatus::Failed),
                sample_node(
                    "Deploy#a",
                    ExecutionNodeType::Deploy,
                    ExecutionStatus::Skipped,
                ),
            ],
            edges: vec![],
            metadata: empty_metadata(),
        };
        let failed = graph.failed_nodes();
        assert_eq!(failed.len(), 2);
        assert!(failed.iter().all(|n| n.status == ExecutionStatus::Failed));
    }

    #[test]
    fn validate_rejects_duplicate_node_id() {
        let graph = ExecutionGraph {
            nodes: vec![
                sample_node("Build#a", ExecutionNodeType::Build, ExecutionStatus::Passed),
                sample_node("Build#a", ExecutionNodeType::Build, ExecutionStatus::Passed),
            ],
            edges: vec![],
            metadata: empty_metadata(),
        };
        let err = graph.validate().unwrap_err();
        assert!(err
            .iter()
            .any(|e| matches!(e, ExecutionValidationError::DuplicateNodeId(_))));
    }

    #[test]
    fn validate_rejects_invalid_node_id() {
        let graph = ExecutionGraph {
            nodes: vec![sample_node(
                "build#bad",
                ExecutionNodeType::Build,
                ExecutionStatus::Passed,
            )],
            edges: vec![],
            metadata: empty_metadata(),
        };
        let err = graph.validate().unwrap_err();
        assert!(err
            .iter()
            .any(|e| matches!(e, ExecutionValidationError::InvalidNodeId(_))));
    }
}
