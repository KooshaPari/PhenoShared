//! Core DAG data structure.
//!
//! A generic directed acyclic graph backed by an adjacency list.

use std::collections::{HashMap, HashSet};
use std::hash::Hash;

/// Error types for DAG operations.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum DagError {
    /// The node already exists in the graph.
    #[error("node `{0:?}` already exists")]
    NodeAlreadyExists(String),

    /// The referenced node does not exist in the graph.
    #[error("node `{0:?}` not found")]
    NodeNotFound(String),

    /// Adding the edge would create a cycle in the graph.
    #[error("edge from `{0:?}` to `{1:?}` would create a cycle")]
    CycleDetected(String, String),

    /// An internal invariant was violated (indicates a bug in the DAG).
    #[error("internal invariant violation: {0}")]
    InternalInvariant(String),
}

/// A generic directed acyclic graph over node identifiers of type `K`.
#[derive(Debug, Clone)]
pub struct Dag<K> {
    /// All known nodes.
    nodes: HashSet<K>,
    /// Adjacency list: parent -> children (forward edges).
    children: HashMap<K, Vec<K>>,
    /// Reverse adjacency list: child -> parents (back edges).
    parents: HashMap<K, Vec<K>>,
}

// ---------------------------------------------------------------------------
// Construction
// ---------------------------------------------------------------------------

/// Returns an empty DAG.
impl<K> Default for Dag<K> {
    fn default() -> Self {
        Self {
            nodes: HashSet::new(),
            children: HashMap::new(),
            parents: HashMap::new(),
        }
    }
}

/// Core graph operations: node/edge manipulation and queries.
impl<K> Dag<K>
where
    K: Eq + Hash + Clone + std::fmt::Debug,
{
    /// Create an empty DAG.
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert a new node. Returns an error if the node already exists.
    pub fn add_node(&mut self, node: K) -> Result<(), DagError> {
        if self.nodes.contains(&node) {
            return Err(DagError::NodeAlreadyExists(format!("{:?}", node)));
        }
        self.nodes.insert(node.clone());
        self.children.entry(node.clone()).or_default();
        self.parents.entry(node).or_default();
        Ok(())
    }

    /// Insert a directed edge `from -> to`.
    ///
    /// Both endpoints must already exist.
    pub fn add_edge(&mut self, from: K, to: K) -> Result<(), DagError> {
        if !self.nodes.contains(&from) {
            return Err(DagError::NodeNotFound(format!("{:?}", from)));
        }
        if !self.nodes.contains(&to) {
            return Err(DagError::NodeNotFound(format!("{:?}", to)));
        }
        self.children
            .entry(from.clone())
            .or_default()
            .push(to.clone());
        self.parents.entry(to).or_default().push(from);
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Accessors
    // -----------------------------------------------------------------------

    /// Return the set of all node identifiers.
    pub fn nodes(&self) -> &HashSet<K> {
        &self.nodes
    }

    /// Return the number of nodes.
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Return the number of edges.
    pub fn edge_count(&self) -> usize {
        self.children.values().map(|v| v.len()).sum()
    }

    /// Return the children (direct successors) of `node`.
    pub fn children_of(&self, node: &K) -> Option<&[K]> {
        self.children.get(node).map(|v| v.as_slice())
    }

    /// Return the parents (direct predecessors) of `node`.
    pub fn parents_of(&self, node: &K) -> Option<&[K]> {
        self.parents.get(node).map(|v| v.as_slice())
    }

    /// Return `true` if the graph contains `node`.
    pub fn contains(&self, node: &K) -> bool {
        self.nodes.contains(node)
    }

    /// Iterate over all nodes.
    pub fn iter_nodes(&self) -> impl Iterator<Item = &K> {
        self.nodes.iter()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_dag() {
        let dag: Dag<u32> = Dag::new();
        assert_eq!(dag.node_count(), 0);
        assert_eq!(dag.edge_count(), 0);
    }

    #[test]
    fn add_and_query_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node(1)?;
        dag.add_node(2)?;
        assert_eq!(dag.node_count(), 2);
        assert!(dag.contains(&1));
        assert!(dag.contains(&2));
        Ok(())
    }

    #[test]
    fn duplicate_node_error() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("a")?;
        assert!(dag.add_node("a").is_err());
        Ok(())
    }

    #[test]
    fn add_edge_missing_source() -> Result<(), DagError> {
        let mut dag = Dag::<&str>::new();
        dag.add_node("b")?;
        assert!(dag.add_edge("a", "b").is_err());
        Ok(())
    }

    #[test]
    fn add_edge_missing_target() -> Result<(), DagError> {
        let mut dag = Dag::<&str>::new();
        dag.add_node("a")?;
        assert!(dag.add_edge("a", "b").is_err());
        Ok(())
    }

    #[test]
    fn simple_edge() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("a")?;
        dag.add_node("b")?;
        dag.add_edge("a", "b")?;
        assert_eq!(dag.edge_count(), 1);
        assert_eq!(dag.children_of(&"a"), Some(&["b"][..]));
        assert_eq!(dag.parents_of(&"b"), Some(&["a"][..]));
        Ok(())
    }

    #[test]
    fn diamond_graph() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in ["a", "b", "c", "d"] {
            dag.add_node(n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "d")?;
        dag.add_edge("c", "d")?;
        assert_eq!(dag.node_count(), 4);
        assert_eq!(dag.edge_count(), 4);
        Ok(())
    }

    // ---- New tests below ----

    #[test]
    fn iter_nodes_returns_all() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in 1..=5 {
            dag.add_node(n)?;
        }
        let collected: Vec<&i32> = dag.iter_nodes().collect();
        assert_eq!(collected.len(), 5);
        Ok(())
    }

    #[test]
    fn children_of_leaf_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("leaf")?;
        dag.add_node("root")?;
        dag.add_edge("root", "leaf")?;
        assert_eq!(dag.children_of(&"leaf"), Some(&[][..]));
        Ok(())
    }

    #[test]
    fn parents_of_root_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("root")?;
        dag.add_node("child")?;
        dag.add_edge("root", "child")?;
        assert_eq!(dag.parents_of(&"root"), Some(&[][..]));
        Ok(())
    }

    #[test]
    fn children_of_unknown_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("a")?;
        assert_eq!(dag.children_of(&"x"), None);
        Ok(())
    }

    #[test]
    fn parents_of_unknown_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("a")?;
        assert_eq!(dag.parents_of(&"x"), None);
        Ok(())
    }

    #[test]
    fn contains_after_add_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        assert!(!dag.contains(&"x"));
        dag.add_node("x")?;
        assert!(dag.contains(&"x"));
        assert!(!dag.contains(&"y"));
        Ok(())
    }

    #[test]
    fn edge_count_multiple_edges() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in ["a", "b", "c"] {
            dag.add_node(n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "c")?;
        assert_eq!(dag.edge_count(), 3);
        Ok(())
    }

    #[test]
    fn parents_of_node_with_multiple_parents() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in ["p1", "p2", "child"] {
            dag.add_node(n)?;
        }
        dag.add_edge("p1", "child")?;
        dag.add_edge("p2", "child")?;
        let parents = dag.parents_of(&"child").unwrap();
        assert!(parents.contains(&"p1"));
        assert!(parents.contains(&"p2"));
        assert_eq!(parents.len(), 2);
        Ok(())
    }

    #[test]
    fn children_of_node_with_multiple_children() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in ["parent", "c1", "c2", "c3"] {
            dag.add_node(n)?;
        }
        dag.add_edge("parent", "c1")?;
        dag.add_edge("parent", "c2")?;
        dag.add_edge("parent", "c3")?;
        let children = dag.children_of(&"parent").unwrap();
        assert_eq!(children.len(), 3);
        assert!(children.contains(&"c1"));
        assert!(children.contains(&"c2"));
        assert!(children.contains(&"c3"));
        Ok(())
    }

    #[test]
    fn error_node_already_exists_message() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("foo")?;
        let err = dag.add_node("foo").unwrap_err();
        let msg = format!("{}", err);
        assert!(msg.contains("foo"), "error should mention the node name");
        Ok(())
    }

    #[test]
    fn error_node_not_found_message() -> Result<(), DagError> {
        let mut dag = Dag::<&str>::new();
        let err = dag.add_edge("missing", "also_missing").unwrap_err();
        let msg = format!("{}", err);
        assert!(msg.contains("missing"));
        Ok(())
    }

    #[test]
    fn single_node_no_edges() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("alone")?;
        assert_eq!(dag.node_count(), 1);
        assert_eq!(dag.edge_count(), 0);
        assert_eq!(dag.children_of(&"alone"), Some(&[][..]));
        assert_eq!(dag.parents_of(&"alone"), Some(&[][..]));
        Ok(())
    }

    #[test]
    fn many_nodes_no_edges() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for i in 0..100 {
            dag.add_node(i)?;
        }
        assert_eq!(dag.node_count(), 100);
        assert_eq!(dag.edge_count(), 0);
        Ok(())
    }

    #[test]
    fn default_dag_is_empty() {
        let dag: Dag<String> = Dag::default();
        assert_eq!(dag.node_count(), 0);
        assert_eq!(dag.edge_count(), 0);
    }

    #[test]
    fn add_node_returns_ok_first_time() -> Result<(), DagError> {
        let mut dag = Dag::new();
        assert!(dag.add_node(42).is_ok());
        Ok(())
    }

    #[test]
    fn clone_dag_preserves_structure() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("a")?;
        dag.add_node("b")?;
        dag.add_edge("a", "b")?;
        let cloned = dag.clone();
        assert_eq!(cloned.node_count(), 2);
        assert_eq!(cloned.edge_count(), 1);
        assert!(cloned.contains(&"a"));
        assert!(cloned.contains(&"b"));
        Ok(())
    }

    #[test]
    fn two_node_graph() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("x")?;
        dag.add_node("y")?;
        dag.add_edge("x", "y")?;
        assert_eq!(dag.children_of(&"x"), Some(&["y"][..]));
        assert_eq!(dag.parents_of(&"y"), Some(&["x"][..]));
        assert_eq!(dag.children_of(&"y"), Some(&[][..]));
        assert_eq!(dag.parents_of(&"x"), Some(&[][..]));
        Ok(())
    }
}
