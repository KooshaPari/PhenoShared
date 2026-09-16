//! Topological sort algorithms for the DAG.
//!
//! Provides Kahn's algorithm (iterative, queue-based) and a DFS-based
//! variant, both producing a linear ordering.

use std::collections::{HashMap, VecDeque};
use std::hash::Hash;

use crate::dag::{Dag, DagError};

// ---------------------------------------------------------------------------
// Kahn's algorithm (BFS-based topological sort)
// ---------------------------------------------------------------------------

/// Compute a topological ordering of `dag` using Kahn's algorithm.
///
/// Returns `Ok(Vec)` where the nodes appear in topologically-sorted order
/// (parents before children). Returns `Err` if the graph contains a cycle.
pub fn kahn_sort<K>(dag: &Dag<K>) -> Result<Vec<&K>, DagError>
where
    K: Eq + Hash + Clone + std::fmt::Debug,
{
    // in-degree for every node
    let mut in_degree: HashMap<&K, usize> = dag.iter_nodes().map(|n| (n, 0)).collect();

    for node in dag.iter_nodes() {
        if let Some(children) = dag.children_of(node) {
            for child in children {
                *in_degree.entry(child).or_insert(0) += 1;
            }
        }
    }

    // seed queue with zero-in-degree nodes
    let mut queue: VecDeque<&K> = in_degree
        .iter()
        .filter(|(_, deg)| **deg == 0)
        .map(|(n, _)| *n)
        .collect();

    let mut order = Vec::with_capacity(dag.node_count());

    while let Some(node) = queue.pop_front() {
        order.push(node);

        if let Some(children) = dag.children_of(node) {
            for child in children {
                let deg = in_degree
                    .get_mut(child)
                    .ok_or_else(|| DagError::InternalInvariant(
                        format!("child `{:?}` not found in in-degree map during Kahn sort", child),
                    ))?;
                *deg -= 1;
                if *deg == 0 {
                    queue.push_back(child);
                }
            }
        }
    }

    if order.len() != dag.node_count() {
        return Err(DagError::CycleDetected(
            "graph".into(),
            "contains a cycle".into(),
        ));
    }

    Ok(order)
}

// ---------------------------------------------------------------------------
// DFS-based topological sort
// ---------------------------------------------------------------------------

/// Color state of a node during DFS traversal.
///
/// Used internally by [`dfs_sort`] to detect back-edges (cycles).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum DfsColor {
    /// Node has not been visited yet.
    White,
    /// Node is on the current DFS path (back-edge detection).
    Gray,
    /// Node has been fully processed.
    Black,
}

/// Compute a topological ordering using DFS with cycle detection.
///
/// Returns `Ok(Vec)` on success, `Err` if a cycle is detected.
pub fn dfs_sort<K>(dag: &Dag<K>) -> Result<Vec<&K>, DagError>
where
    K: Eq + Hash + Clone + std::fmt::Debug,
{
    let mut color: HashMap<&K, DfsColor> = dag.iter_nodes().map(|n| (n, DfsColor::White)).collect();
    let mut order = Vec::with_capacity(dag.node_count());

    for start in dag.iter_nodes() {
        if color[start] == DfsColor::White {
            visit(dag, start, &mut color, &mut order)?;
        }
    }

    // DFS pushes at the end; reverse to get parent-before-child ordering.
    order.reverse();
    Ok(order)
}

/// Recursively visit `node`, pushing it onto `order` after all children.
///
/// Marks nodes as [`DfsColor::Gray`] while in-progress (for cycle detection)
/// and [`DfsColor::Black`] once fully processed.
fn visit<'a, K>(
    dag: &'a Dag<K>,
    node: &'a K,
    color: &mut HashMap<&'a K, DfsColor>,
    order: &mut Vec<&'a K>,
) -> Result<(), DagError>
where
    K: Eq + Hash + Clone + std::fmt::Debug,
{
    color.insert(node, DfsColor::Gray);

    if let Some(children) = dag.children_of(node) {
        for child in children {
            match color.get(child).copied().unwrap_or(DfsColor::White) {
                DfsColor::Gray => {
                    return Err(DagError::CycleDetected(
                        format!("{:?}", node),
                        format!("{:?}", child),
                    ));
                }
                DfsColor::White => visit(dag, child, color, order)?,
                DfsColor::Black => continue,
            }
        }
    }

    color.insert(node, DfsColor::Black);
    order.push(node);
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kahn_linear_chain() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("b", "c")?;
        dag.add_edge("c", "d")?;

        let order = kahn_sort(&dag)?;
        let ids: Vec<&str> = order.into_iter().copied().collect();
        // a must be before b before c before d
        let pos = |name: &str| -> Result<usize, DagError> {
            ids.iter().position(|x| *x == name)
                .ok_or_else(|| DagError::InternalInvariant(format!("node {} not found in order", name)))
        };
        assert!(pos("a")? < pos("b")?);
        assert!(pos("b")? < pos("c")?);
        assert!(pos("c")? < pos("d")?);
        Ok(())
    }

    #[test]
    fn kahn_diamond() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "d")?;
        dag.add_edge("c", "d")?;

        let order = kahn_sort(&dag)?;
        let ids: Vec<&str> = order.into_iter().copied().collect();
        let pos = |name: &str| -> Result<usize, DagError> {
            ids.iter().position(|x| *x == name)
                .ok_or_else(|| DagError::InternalInvariant(format!("node {} not found in order", name)))
        };
        assert!(pos("a")? < pos("b")?);
        assert!(pos("a")? < pos("c")?);
        assert!(pos("b")? < pos("d")?);
        assert!(pos("c")? < pos("d")?);
        Ok(())
    }

    #[test]
    fn kahn_cycle_detection() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("b", "c")?;
        dag.add_edge("c", "a")?; // cycle

        assert!(kahn_sort(&dag).is_err());
        Ok(())
    }

    #[test]
    fn dfs_sort_matches_kahn() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d", "e", "f"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "d")?;
        dag.add_edge("c", "d")?;
        dag.add_edge("d", "e")?;
        dag.add_edge("c", "f")?;

        let kahn_order = kahn_sort(&dag)?;
        let dfs_order = dfs_sort(&dag)?;

        // Both should produce valid topological orders of the same length.
        assert_eq!(kahn_order.len(), dfs_order.len());

        // Verify DFS order respects all edges.
        for node in dag.iter_nodes() {
            if let Some(children) = dag.children_of(node) {
                let n_pos = dfs_order.iter().position(|x| *x == node)
                    .ok_or_else(|| DagError::InternalInvariant(format!("node {:?} not found in DFS order", node)))?;
                for child in children {
                    let c_pos = dfs_order.iter().position(|x| *x == child)
                        .ok_or_else(|| DagError::InternalInvariant(format!("child {:?} not found in DFS order", child)))?;
                    assert!(n_pos < c_pos, "DFS: {} should come before {}", node, child);
                }
            }
        }
        Ok(())
    }

    #[test]
    fn dfs_cycle_detection() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("b", "c")?;
        dag.add_edge("c", "a")?;
        assert!(dfs_sort(&dag).is_err());
        Ok(())
    }

    #[test]
    fn kahn_empty_dag() -> Result<(), DagError> {
        let dag: Dag<u32> = Dag::new();
        let order = kahn_sort(&dag)?;
        assert!(order.is_empty());
        Ok(())
    }

    #[test]
    fn dfs_empty_dag() -> Result<(), DagError> {
        let dag: Dag<u32> = Dag::new();
        let order = dfs_sort(&dag)?;
        assert!(order.is_empty());
        Ok(())
    }

    // ---- New tests below ----

    #[test]
    fn kahn_single_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("only")?;
        let order = kahn_sort(&dag)?;
        assert_eq!(order.len(), 1);
        assert_eq!(order[0], &"only");
        Ok(())
    }

    #[test]
    fn dfs_single_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("only")?;
        let order = dfs_sort(&dag)?;
        assert_eq!(order.len(), 1);
        assert_eq!(order[0], &"only");
        Ok(())
    }

    #[test]
    fn kahn_two_independent_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("x")?;
        dag.add_node("y")?;
        let order = kahn_sort(&dag)?;
        assert_eq!(order.len(), 2);
        // Both nodes must be present.
        let ids: Vec<&str> = order.into_iter().copied().collect();
        assert!(ids.contains(&"x"));
        assert!(ids.contains(&"y"));
        Ok(())
    }

    #[test]
    fn dfs_two_independent_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("x")?;
        dag.add_node("y")?;
        let order = dfs_sort(&dag)?;
        assert_eq!(order.len(), 2);
        let ids: Vec<&str> = order.into_iter().copied().collect();
        assert!(ids.contains(&"x"));
        assert!(ids.contains(&"y"));
        Ok(())
    }

    #[test]
    fn kahn_long_chain_5_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        let nodes = ["n1", "n2", "n3", "n4", "n5"];
        for n in &nodes {
            dag.add_node(*n)?;
        }
        for w in nodes.windows(2) {
            dag.add_edge(w[0], w[1])?;
        }
        let order = kahn_sort(&dag)?;
        let ids: Vec<&str> = order.into_iter().copied().collect();
        assert_eq!(ids, vec!["n1", "n2", "n3", "n4", "n5"]);
        Ok(())
    }

    #[test]
    fn dfs_long_chain_5_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        let nodes = ["n1", "n2", "n3", "n4", "n5"];
        for n in &nodes {
            dag.add_node(*n)?;
        }
        for w in nodes.windows(2) {
            dag.add_edge(w[0], w[1])?;
        }
        let order = dfs_sort(&dag)?;
        let ids: Vec<&str> = order.into_iter().copied().collect();
        // DFS produces reverse-postorder, reversed → parent before child.
        assert_eq!(ids, vec!["n1", "n2", "n3", "n4", "n5"]);
        Ok(())
    }

    #[test]
    fn kahn_fan_out_fan_in_ordering() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["root", "a", "b", "c", "sink"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("root", "a")?;
        dag.add_edge("root", "b")?;
        dag.add_edge("root", "c")?;
        dag.add_edge("a", "sink")?;
        dag.add_edge("b", "sink")?;
        dag.add_edge("c", "sink")?;

        let order = kahn_sort(&dag)?;
        let ids: Vec<&str> = order.into_iter().copied().collect();
        let pos = |name: &str| ids.iter().position(|x| *x == name).unwrap();
        // root must come first, sink last.
        assert_eq!(pos("root"), 0);
        assert_eq!(pos("sink"), 4);
        // a, b, c must be in positions 1, 2, 3 (order among them may vary).
        let mid: Vec<&str> = ids[1..4].to_vec();
        assert!(mid.contains(&"a"));
        assert!(mid.contains(&"b"));
        assert!(mid.contains(&"c"));
        Ok(())
    }

    #[test]
    fn kahn_and_dfs_same_length() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d", "e"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "d")?;
        dag.add_edge("c", "e")?;

        let kahn_order = kahn_sort(&dag)?;
        let dfs_order = dfs_sort(&dag)?;
        assert_eq!(kahn_order.len(), dfs_order.len());
        assert_eq!(kahn_order.len(), 5);
        Ok(())
    }

    #[test]
    fn kahn_two_node_cycle() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("u")?;
        dag.add_node("v")?;
        dag.add_edge("u", "v")?;
        dag.add_edge("v", "u")?; // 2-cycle
        assert!(kahn_sort(&dag).is_err());
        Ok(())
    }

    #[test]
    fn dfs_two_node_cycle() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("u")?;
        dag.add_node("v")?;
        dag.add_edge("u", "v")?;
        dag.add_edge("v", "u")?; // 2-cycle
        assert!(dfs_sort(&dag).is_err());
        Ok(())
    }

    #[test]
    fn kahn_disconnected_components() -> Result<(), DagError> {
        // Two disconnected subgraphs: a→b and c→d
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("c", "d")?;

        let order = kahn_sort(&dag)?;
        assert_eq!(order.len(), 4);
        let ids: Vec<&str> = order.into_iter().copied().collect();
        let pos = |name: &str| ids.iter().position(|x| *x == name).unwrap();
        assert!(pos("a") < pos("b"));
        assert!(pos("c") < pos("d"));
        Ok(())
    }

    #[test]
    fn kahn_diamond_wide() -> Result<(), DagError> {
        // root → m1, m2, m3, m4 → sink
        let mut dag = Dag::new();
        for n in &["root", "m1", "m2", "m3", "m4", "sink"] {
            dag.add_node(*n)?;
        }
        for mid in &["m1", "m2", "m3", "m4"] {
            dag.add_edge("root", *mid)?;
            dag.add_edge(*mid, "sink")?;
        }
        let order = kahn_sort(&dag)?;
        assert_eq!(order.len(), 6);
        let ids: Vec<&str> = order.into_iter().copied().collect();
        let pos = |name: &str| ids.iter().position(|x| *x == name).unwrap();
        assert_eq!(pos("root"), 0);
        assert_eq!(pos("sink"), 5);
        Ok(())
    }

    #[test]
    fn dfs_self_loop_cycle() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("self")?;
        dag.add_edge("self", "self")?; // self-loop
        assert!(dfs_sort(&dag).is_err());
        Ok(())
    }
}
