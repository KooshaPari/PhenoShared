use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::path::{Path, PathBuf};

use acceptance_contract::{run_acceptance, ExecutionContext, ScoreCard};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DagFile {
    pub nodes: Vec<DagNode>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DagNode {
    pub id: String,
    pub contract: String,
    #[serde(default)]
    pub baseline: Option<String>,
    #[serde(default)]
    pub depends_on: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DagNodeStatus {
    NotRun,
    Success,
    HardFailed,
    RuntimeFailure,
    SkippedDependency,
}

#[derive(Debug, Clone, Serialize)]
pub struct DagNodeRun {
    pub id: String,
    pub contract: PathBuf,
    pub baseline: PathBuf,
    pub status: DagNodeStatus,
    #[serde(default)]
    pub score_card: Option<ScoreCard>,
    #[serde(default)]
    pub skipped_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DagScorecard {
    pub total_nodes: usize,
    pub executed_nodes: usize,
    pub skipped_nodes: usize,
    pub hard_failed_nodes: usize,
    pub runtime_failed_nodes: usize,
    pub hard_passed: bool,
    pub soft_score: f64,
    pub soft_score_max: f64,
    pub soft_percentage: f64,
    pub nodes: Vec<DagNodeRun>,
}

impl DagScorecard {
    fn empty(total_nodes: usize) -> Self {
        Self {
            total_nodes,
            executed_nodes: 0,
            skipped_nodes: 0,
            hard_failed_nodes: 0,
            runtime_failed_nodes: 0,
            hard_passed: true,
            soft_score: 0.0,
            soft_score_max: 0.0,
            soft_percentage: 0.0,
            nodes: Vec::new(),
        }
    }

    fn finalize(&mut self) {
        if self.soft_score_max > 0.0 {
            self.soft_percentage = (self.soft_score / self.soft_score_max) * 100.0;
        }
        self.hard_passed = self.hard_failed_nodes == 0 && self.runtime_failed_nodes == 0;
    }
}

pub struct DagContext<'a> {
    pub workspace_root: &'a Path,
    pub execution_context: ExecutionContext,
}

pub fn parse_deploy_dag(path: &Path) -> Result<DagFile> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("failed to read DAG file {}", path.display()))?;

    serde_yaml::from_str::<DagFile>(&content)
        .or_else(|_| serde_json::from_str::<DagFile>(&content).map_err(anyhow::Error::from))
        .with_context(|| format!("failed to parse DAG file {}", path.display()))
}

pub fn validate_and_sort(dag: &DagFile) -> Result<Vec<String>> {
    let mut adjacency: HashMap<String, Vec<String>> = HashMap::new();
    let mut indegree: HashMap<String, usize> = HashMap::new();
    let mut node_lookup: HashMap<String, &DagNode> = HashMap::new();

    for node in &dag.nodes {
        if node.id.trim().is_empty() {
            return Err(anyhow!("node id cannot be empty"));
        }
        if node_lookup.insert(node.id.clone(), node).is_some() {
            return Err(anyhow!("duplicate node id '{}'", node.id));
        }
        indegree.entry(node.id.clone()).or_insert(0);
        adjacency.entry(node.id.clone()).or_default();
    }

    for node in &dag.nodes {
        for dep in &node.depends_on {
            if !node_lookup.contains_key(dep) {
                return Err(anyhow!(
                    "node '{}' depends on unknown node '{}'",
                    node.id,
                    dep
                ));
            }
            adjacency
                .entry(dep.clone())
                .or_default()
                .push(node.id.clone());
            *indegree.entry(node.id.clone()).or_default() += 1;
        }
    }

    let mut queue: VecDeque<String> = indegree
        .iter()
        .filter_map(|(id, degree)| if *degree == 0 { Some(id.clone()) } else { None })
        .collect();

    let mut sorted = Vec::with_capacity(indegree.len());
    let mut current_indegree = indegree;

    while let Some(node_id) = queue.pop_front() {
        sorted.push(node_id.clone());

        for edge in adjacency.remove(&node_id).unwrap_or_default() {
            if let Some(entry) = current_indegree.get_mut(&edge) {
                if *entry > 0 {
                    *entry -= 1;
                    if *entry == 0 {
                        queue.push_back(edge);
                    }
                }
            }
        }
    }

    if sorted.len() != dag.nodes.len() {
        let unresolved: Vec<String> = current_indegree
            .into_iter()
            .filter(|(_, degree)| *degree > 0)
            .map(|(id, _)| id)
            .collect();
        return Err(anyhow!(
            "cycle detected in deploy.dag.yaml; unresolved nodes: {:?}",
            unresolved
        ));
    }

    Ok(sorted)
}

pub fn run_deploy_dag(
    dag: &DagFile,
    manifest_path: &Path,
    context: DagContext<'_>,
) -> Result<DagScorecard> {
    let run_order = validate_and_sort(dag)?;
    let base_dir = manifest_path
        .parent()
        .context("deploy.dag.yaml must have a containing directory")?;

    let mut status: HashMap<String, DagNodeStatus> = HashMap::new();
    let mut scorecard = DagScorecard::empty(dag.nodes.len());
    let mut nodes_by_id = HashMap::new();
    for node in &dag.nodes {
        nodes_by_id.insert(node.id.as_str(), node);
    }

    let baseline_for_node = |node: &DagNode| -> PathBuf {
        if let Some(path) = &node.baseline {
            base_dir.join(path)
        } else {
            let stem = Path::new(&node.contract)
                .file_stem()
                .and_then(|stem| stem.to_str())
                .unwrap_or("contract");
            base_dir.join(format!("{}.baseline.json", stem))
        }
    };

    for node_id in run_order {
        let node = nodes_by_id
            .get(node_id.as_str())
            .copied()
            .ok_or_else(|| anyhow!("missing node '{}' after topo ordering", node_id))?;

        let blocked_by_hard_failure = node.depends_on.iter().any(|dep| {
            matches!(
                status.get(dep),
                Some(DagNodeStatus::HardFailed)
                    | Some(DagNodeStatus::RuntimeFailure)
                    | Some(DagNodeStatus::SkippedDependency)
            )
        });

        let contract = base_dir.join(&node.contract);
        let baseline = baseline_for_node(node);

        if blocked_by_hard_failure {
            scorecard.skipped_nodes += 1;
            status.insert(node.id.clone(), DagNodeStatus::SkippedDependency);
            scorecard.nodes.push(DagNodeRun {
                id: node.id.clone(),
                contract,
                baseline,
                status: DagNodeStatus::SkippedDependency,
                score_card: None,
                skipped_reason: Some("skipped due to failed upstream dependency".to_string()),
            });
            continue;
        }

        match run_acceptance(
            &contract,
            &baseline,
            context.workspace_root,
            context.execution_context.clone(),
        ) {
            Ok(card) => {
                scorecard.executed_nodes += 1;
                scorecard.soft_score += card.total_soft_score;
                scorecard.soft_score_max += card.max_soft_score;
                let node_status = if card.hard_passed {
                    DagNodeStatus::Success
                } else {
                    scorecard.hard_failed_nodes += 1;
                    DagNodeStatus::HardFailed
                };
                status.insert(node.id.clone(), node_status.clone());
                scorecard.nodes.push(DagNodeRun {
                    id: node.id.clone(),
                    contract,
                    baseline,
                    status: node_status,
                    score_card: Some(card),
                    skipped_reason: None,
                });
            }
            Err(err) => {
                scorecard.runtime_failed_nodes += 1;
                status.insert(node.id.clone(), DagNodeStatus::RuntimeFailure);
                scorecard.nodes.push(DagNodeRun {
                    id: node.id.clone(),
                    contract,
                    baseline,
                    status: DagNodeStatus::RuntimeFailure,
                    score_card: None,
                    skipped_reason: Some(err.to_string()),
                });
            }
        }
    }

    scorecard.finalize();
    Ok(scorecard)
}

pub fn run_deploy_dag_file(
    path: &Path,
    workspace_root: &Path,
    execution_context: ExecutionContext,
) -> Result<DagScorecard> {
    let manifest = parse_deploy_dag(path)?;
    run_deploy_dag(
        &manifest,
        path,
        DagContext {
            workspace_root,
            execution_context,
        },
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_cycles_before_running() {
        let dag = DagFile {
            nodes: vec![
                DagNode {
                    id: "a".to_string(),
                    contract: "a.yaml".to_string(),
                    baseline: None,
                    depends_on: vec!["c".to_string()],
                },
                DagNode {
                    id: "b".to_string(),
                    contract: "b.yaml".to_string(),
                    baseline: None,
                    depends_on: vec!["a".to_string()],
                },
                DagNode {
                    id: "c".to_string(),
                    contract: "c.yaml".to_string(),
                    baseline: None,
                    depends_on: vec!["b".to_string()],
                },
            ],
        };

        let err = validate_and_sort(&dag).unwrap_err();
        let message = err.to_string();
        assert!(
            message.contains("cycle detected"),
            "expected cycle detection, got {message}"
        );
    }
}
