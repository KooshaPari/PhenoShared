//! # phenotype-dag-core
//!
//! DAG foundation for Phenotype compute/infra automation (epic F).
//!
//! This crate was extracted from BytePort's `byteport-dag` crate as part
//! of the foundation automation effort. It provides a generic directed
//! acyclic graph, topological sort (Kahn + DFS), parallel-bucket scheduling,
//! enriched node/edge schema (prerequisites, acceptance criteria, audit
//! hooks), and YAML/JSON serialization.
//!
//! Renamed 2026-09-01 from `pheno-dag` to `phenotype-dag-core` to break
//! the name collision with the absorbed Go source `KooshaPari/phenodag`
//! (now deleted; absorbed into Tracera spec 008 + 11 queue files +
//! AgilePlus mirror).
//!
//! ## Modules
//!
//! | Module        | Description                                                |
//! |---------------|------------------------------------------------------------|
//! | [`dag`]       | Generic directed-acyclic-graph data structure               |
//! | [`topo`]      | Topological sort (Kahn's algorithm + DFS variant)          |
//! | [`scheduler`] | Parallel-bucket scheduler built on topological order        |
//! | [`schema`]    | Enriched node/edge schema: prereqs, acceptance, audit hooks |
//! | [`serialize`] | YAML/JSON round-trip serialization for the enriched schema |
//!
//! ## Example
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

/// Core DAG data structure with generic node identifiers.
///
/// Provides [`Dag<K>`] — a generic directed acyclic graph backed by an
/// adjacency list with O(1) edge queries in both directions.
pub mod dag;

/// Parallel-bucket scheduler for DAG execution.
///
/// Groups independent nodes into parallel execution buckets using
/// topological ranking (Kahn's algorithm → rank assignment → bucket grouping).
pub mod scheduler;

/// Enriched DAG schema types for compute/infra automation.
///
/// Defines node and edge metadata including prerequisites, acceptance
/// criteria, and audit hooks — the domain layer on top of [`dag::Dag`].
pub mod schema;

/// YAML/JSON serialization for the enriched DAG schema.
///
/// Provides [`serialize::DagSchema`] — a portable, serde-friendly
/// representation of the enriched graph with round-trip fidelity.
pub mod serialize;

/// Topological sort algorithms (Kahn's BFS + DFS variant).
///
/// Both algorithms detect cycles and return [`dag::DagError::CycleDetected`]
/// on cyclic input.
pub mod topo;
