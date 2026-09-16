//! Parallel-bucket scheduler for DAG execution.
//!
//! Given a DAG, the scheduler groups nodes into "buckets" such that all
//! nodes within a bucket can execute in parallel, and buckets are ordered
//! so that bucket *i* must complete before bucket *i+1* begins.
//!
//! # Algorithm
//!
//! 1. Compute a topological order via Kahn's algorithm.
//! 2. Assign each node a **rank** = max(parent ranks) + 1 (source nodes get
//!    rank 0).
//! 3. Group nodes by rank → each rank is a parallel bucket.
//! 4. Return the list of buckets.

use std::collections::HashMap;
use std::hash::Hash;

use crate::dag::{Dag, DagError};
use crate::topo;

/// A wall of parallel-execution buckets produced by the scheduler.
///
/// Buckets are ordered: bucket[0] must finish before bucket[1] starts, etc.
/// Within a bucket all nodes are independent and can be scheduled in parallel.
pub struct Schedule<K> {
    /// Ordered list of buckets. Each bucket is a set of node references.
    pub buckets: Vec<Vec<K>>,
    /// Maximum concurrency (size of the largest bucket).
    pub max_concurrency: usize,
}

/// Compute a parallel-bucket schedule from the given DAG.
///
/// Returns an error if the DAG contains a cycle.
pub fn schedule<K>(dag: &Dag<K>) -> Result<Schedule<K>, DagError>
where
    K: Eq + Hash + Clone + std::fmt::Debug,
{
    // 1. Topological order (validates acyclicity).
    let topo_order = topo::kahn_sort(dag)?;

    // 2. Assign ranks.
    let mut rank: HashMap<&K, usize> = HashMap::with_capacity(dag.node_count());

    for node in &topo_order {
        let parent_rank = dag
            .parents_of(node)
            .unwrap_or(&[])
            .iter()
            .filter_map(|p| rank.get(p))
            .max()
            .copied()
            .unwrap_or(0);

        rank.insert(node, parent_rank + 1);
    }

    // 3. Group by rank into buckets.
    let max_rank = rank.values().copied().max().unwrap_or(0);
    let mut buckets: Vec<Vec<K>> = vec![Vec::new(); max_rank];

    for (node, r) in &rank {
        // r is 1-based; bucket index = r - 1
        buckets[*r - 1].push((*node).clone());
    }

    let max_concurrency = buckets.iter().map(|b| b.len()).max().unwrap_or(0);

    Ok(Schedule {
        buckets,
        max_concurrency,
    })
}

/// Print a human-readable schedule summary.
///
/// Only available when `std`/default formatting is sufficient.
pub fn format_schedule<K>(schedule: &Schedule<K>) -> String
where
    K: std::fmt::Debug,
{
    let mut out = String::new();
    out.push_str(&format!(
        "Schedule ({} buckets, max concurrency = {})\n",
        schedule.buckets.len(),
        schedule.max_concurrency
    ));
    for (i, bucket) in schedule.buckets.iter().enumerate() {
        out.push_str(&format!("  Bucket {}: {:?}\n", i, bucket));
    }
    out
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn build_linear_dag() -> Result<Dag<&'static str>, DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("b", "c")?;
        Ok(dag)
    }

    #[test]
    fn linear_schedule() -> Result<(), DagError> {
        let dag = build_linear_dag()?;
        let sched = schedule(&dag)?;
        // 3 nodes, no parallelism → one bucket per node
        assert_eq!(sched.buckets.len(), 3);
        assert_eq!(sched.max_concurrency, 1);
        assert_eq!(sched.buckets[0], vec!["a"]);
        assert_eq!(sched.buckets[1], vec!["b"]);
        assert_eq!(sched.buckets[2], vec!["c"]);
        Ok(())
    }

    #[test]
    fn diamond_parallelism() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        dag.add_edge("b", "d")?;
        dag.add_edge("c", "d")?;

        let sched = schedule(&dag)?;
        // Buckets: [a], [b, c], [d]
        assert_eq!(sched.buckets.len(), 3);
        assert_eq!(sched.max_concurrency, 2);

        let b0: std::collections::BTreeSet<_> = sched.buckets[0].iter().collect();
        let b1: std::collections::BTreeSet<_> = sched.buckets[1].iter().collect();
        let b2: std::collections::BTreeSet<_> = sched.buckets[2].iter().collect();

        assert_eq!(b0, std::collections::BTreeSet::from([&"a"]));
        assert_eq!(b1, std::collections::BTreeSet::from([&"b", &"c"]));
        assert_eq!(b2, std::collections::BTreeSet::from([&"d"]));
        Ok(())
    }

    #[test]
    fn fan_out_fan_in() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["root", "a1", "a2", "a3", "leaf"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("root", "a1")?;
        dag.add_edge("root", "a2")?;
        dag.add_edge("root", "a3")?;
        dag.add_edge("a1", "leaf")?;
        dag.add_edge("a2", "leaf")?;
        dag.add_edge("a3", "leaf")?;

        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 3);
        assert_eq!(sched.max_concurrency, 3); // a1, a2, a3 in parallel

        let b1: std::collections::BTreeSet<_> = sched.buckets[1].iter().collect();
        assert_eq!(b1, std::collections::BTreeSet::from([&"a1", &"a2", &"a3"]));
        Ok(())
    }

    #[test]
    fn empty_schedule() -> Result<(), DagError> {
        let dag: Dag<u32> = Dag::new();
        let sched = schedule(&dag)?;
        assert!(sched.buckets.is_empty());
        assert_eq!(sched.max_concurrency, 0);
        Ok(())
    }

    #[test]
    fn single_node() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("only")?;
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 1);
        assert_eq!(sched.buckets[0], vec!["only"]);
        assert_eq!(sched.max_concurrency, 1);
        Ok(())
    }

    #[test]
    fn cycle_returns_error() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["x", "y", "z"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("x", "y")?;
        dag.add_edge("y", "z")?;
        dag.add_edge("z", "x")?;
        assert!(schedule(&dag).is_err());
        Ok(())
    }

    #[test]
    fn multi_source_dag() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["s1", "s2", "mid", "t"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("s1", "mid")?;
        dag.add_edge("s2", "mid")?;
        dag.add_edge("mid", "t")?;

        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 3);
        // Bucket 0: all sources
        let b0: std::collections::BTreeSet<_> = sched.buckets[0].iter().collect();
        assert_eq!(b0, std::collections::BTreeSet::from([&"s1", &"s2"]));
        assert_eq!(sched.max_concurrency, 2);
        Ok(())
    }

    #[test]
    fn format_output() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["a", "b", "c"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("a", "c")?;
        let sched = schedule(&dag)?;
        let formatted = format_schedule(&sched);
        assert!(formatted.contains("2 buckets"));
        assert!(formatted.contains("max concurrency = 2"));
        Ok(())
    }

    // ---- New tests below ----

    #[test]
    fn schedule_chain_of_length_2() -> Result<(), DagError> {
        let mut dag = Dag::new();
        dag.add_node("start")?;
        dag.add_node("end")?;
        dag.add_edge("start", "end")?;
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 2);
        assert_eq!(sched.max_concurrency, 1);
        assert_eq!(sched.buckets[0], vec!["start"]);
        assert_eq!(sched.buckets[1], vec!["end"]);
        Ok(())
    }

    #[test]
    fn schedule_chain_5_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        let nodes = ["s1", "s2", "s3", "s4", "s5"];
        for n in &nodes {
            dag.add_node(*n)?;
        }
        for w in nodes.windows(2) {
            dag.add_edge(w[0], w[1])?;
        }
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 5);
        assert_eq!(sched.max_concurrency, 1);
        // Each bucket should have exactly one node.
        for bucket in &sched.buckets {
            assert_eq!(bucket.len(), 1);
        }
        Ok(())
    }

    #[test]
    fn schedule_all_nodes_present() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["x", "y", "z"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("x", "y")?;
        dag.add_edge("x", "z")?;
        let sched = schedule(&dag)?;
        let all: Vec<&str> = sched.buckets.iter().flat_map(|b| b.iter().copied()).collect();
        assert_eq!(all.len(), 3);
        assert!(all.contains(&"x"));
        assert!(all.contains(&"y"));
        assert!(all.contains(&"z"));
        Ok(())
    }

    #[test]
    fn schedule_two_sources_converge() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["src1", "src2", "target"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("src1", "target")?;
        dag.add_edge("src2", "target")?;
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 2);
        assert_eq!(sched.max_concurrency, 2); // src1 + src2 in bucket 0
        let b0: std::collections::BTreeSet<_> = sched.buckets[0].iter().collect();
        assert_eq!(b0, std::collections::BTreeSet::from([&"src1", &"src2"]));
        Ok(())
    }

    #[test]
    fn schedule_three_level_wide_diamond() -> Result<(), DagError> {
        // root → [a, b, c, d] → sink
        let mut dag = Dag::new();
        for n in &["root", "a", "b", "c", "d", "sink"] {
            dag.add_node(*n)?;
        }
        for mid in &["a", "b", "c", "d"] {
            dag.add_edge("root", *mid)?;
            dag.add_edge(*mid, "sink")?;
        }
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 3);
        assert_eq!(sched.max_concurrency, 4); // four nodes in middle bucket
        Ok(())
    }

    #[test]
    fn schedule_format_output_contains_bucket_header() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for n in &["x", "y"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("x", "y")?;
        let sched = schedule(&dag)?;
        let output = format_schedule(&sched);
        assert!(output.contains("Bucket 0:"));
        assert!(output.contains("Bucket 1:"));
        Ok(())
    }

    #[test]
    fn schedule_two_parallel_independent_pairs() -> Result<(), DagError> {
        // Two independent chains: a→b and c→d
        let mut dag = Dag::new();
        for n in &["a", "b", "c", "d"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("a", "b")?;
        dag.add_edge("c", "d")?;
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 2);
        assert_eq!(sched.max_concurrency, 2);
        let b0: std::collections::BTreeSet<_> = sched.buckets[0].iter().collect();
        assert_eq!(b0, std::collections::BTreeSet::from([&"a", &"c"]));
        let b1: std::collections::BTreeSet<_> = sched.buckets[1].iter().collect();
        assert_eq!(b1, std::collections::BTreeSet::from([&"b", &"d"]));
        Ok(())
    }

    #[test]
    fn schedule_chain_10_nodes() -> Result<(), DagError> {
        let mut dag = Dag::new();
        for i in 0..10 {
            dag.add_node(i)?;
        }
        for i in 0..9 {
            dag.add_edge(i, i + 1)?;
        }
        let sched = schedule(&dag)?;
        assert_eq!(sched.buckets.len(), 10);
        assert_eq!(sched.max_concurrency, 1);
        Ok(())
    }

    #[test]
    fn schedule_max_concurrency准确性() -> Result<(), DagError> {
        // Test that max_concurrency is accurate for various DAG shapes.
        let mut dag = Dag::new();
        for n in &["r", "a", "b", "c", "d", "e", "sink"] {
            dag.add_node(*n)?;
        }
        dag.add_edge("r", "a")?;
        dag.add_edge("r", "b")?;
        dag.add_edge("r", "c")?;
        dag.add_edge("a", "d")?;
        dag.add_edge("b", "e")?;
        dag.add_edge("c", "sink")?;
        dag.add_edge("d", "sink")?;
        dag.add_edge("e", "sink")?;
        let sched = schedule(&dag)?;
        // Verify max_concurrency equals the largest bucket.
        let actual_max = sched.buckets.iter().map(|b| b.len()).max().unwrap_or(0);
        assert_eq!(sched.max_concurrency, actual_max);
        Ok(())
    }
}
