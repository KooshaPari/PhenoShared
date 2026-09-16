use acceptance_contract::{run_acceptance, ExecutionContext, ScoreCard as AcceptanceScoreCard};
use anyhow::{Context, Result};
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Parser, Debug)]
#[command(name = "dag-scheduler")]
#[command(about = "Run acceptance-contract nodes using a dependency DAG")]
struct Cli {
    #[arg(long, default_value = "deploy.dag.yaml")]
    dag_file: PathBuf,

    #[arg(long, default_value = ".")]
    workspace_root: PathBuf,

    #[arg(long)]
    json: bool,
}

#[derive(Debug, Deserialize)]
struct DagFile {
    #[serde(default)]
    nodes: Vec<DagNode>,
}

#[derive(Debug, Deserialize, Clone)]
struct DagNode {
    id: String,
    #[serde(default)]
    depends_on: Vec<String>,
    contract: ContractDescriptor,
}

#[derive(Debug, Deserialize, Clone)]
#[serde(untagged)]
enum ContractDescriptor {
    Path(String),
    Config(ContractConfig),
}

#[derive(Debug, Deserialize, Clone)]
struct ContractConfig {
    path: PathBuf,
    #[serde(default)]
    baseline_path: Option<PathBuf>,
    #[serde(default)]
    workspace: Option<PathBuf>,
    #[serde(default)]
    skip_delegation: bool,
    #[serde(default)]
    update_baseline: bool,
}

#[derive(Debug, Serialize)]
struct NodeRun {
    id: String,
    status: NodeStatus,
    skipped_due_to: Option<String>,
    duration_ms: u128,
    acceptance: Option<AcceptanceNodeResult>,
}

#[derive(Debug, Serialize)]
enum NodeStatus {
    Success,
    HardFailure,
    SoftFailure,
    Skipped,
}

#[derive(Debug, Serialize)]
struct AcceptanceNodeResult {
    contract_path: PathBuf,
    hard_passed: bool,
    soft_percentage: f64,
    hard_requirement_count: usize,
    soft_requirement_count: usize,
}

#[derive(Debug, Serialize)]
struct DagScorecard {
    nodes: Vec<NodeRun>,
    total: usize,
    success: usize,
    hard_failures: usize,
    soft_failures: usize,
    skipped: usize,
    execution_order: Vec<String>,
    cycle_detected: bool,
    total_duration_ms: u128,
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let scorecard = run_dag(&cli)?;
    if cli.json {
        println!("{}", serde_json::to_string_pretty(&scorecard)?);
    } else {
        println!("DAG scorecard:");
        for node in &scorecard.nodes {
            println!("{} -> {:?} ({}ms)", node.id, node.status, node.duration_ms);
            if let Some(reason) = &node.skipped_due_to {
                println!("  skipped: {}", reason);
            }
            if let Some(card) = &node.acceptance {
                println!(
                    "  hard_passed={} soft_score={:.1}% hard_reqs={} soft_reqs={}",
                    card.hard_passed,
                    card.soft_percentage,
                    card.hard_requirement_count,
                    card.soft_requirement_count
                );
            }
        }
        println!(
            "Summary: total={} success={} hard_failures={} soft_failures={} skipped={}",
            scorecard.total,
            scorecard.success,
            scorecard.hard_failures,
            scorecard.soft_failures,
            scorecard.skipped
        );
        println!(
            "Topological order: {}",
            scorecard.execution_order.join(", ")
        );
    }

    let has_hard_failures = scorecard
        .nodes
        .iter()
        .any(|node| matches!(node.status, NodeStatus::HardFailure));
    if has_hard_failures {
        std::process::exit(1);
    }

    Ok(())
}

fn run_dag(cli: &Cli) -> Result<DagScorecard> {
    let content = std::fs::read_to_string(&cli.dag_file).with_context(|| {
        format!(
            "failed to read DAG file at {}",
            cli.dag_file.to_string_lossy()
        )
    })?;
    let dag: DagFile = serde_yaml::from_str(&content)
        .with_context(|| "failed to parse deploy.dag.yaml as YAML".to_string())?;

    let run_start = Instant::now();
    let run_order = topological_sort(&dag.nodes)?;
    let mut reverse_graph: HashMap<String, Vec<String>> = HashMap::new();
    for node in &dag.nodes {
        for dep in &node.depends_on {
            reverse_graph
                .entry(dep.clone())
                .or_default()
                .push(node.id.clone());
        }
    }

    let mut node_map: HashMap<&str, &DagNode> = HashMap::new();
    for node in &dag.nodes {
        node_map.insert(node.id.as_str(), node);
    }

    let mut blocked: HashSet<String> = HashSet::new();
    let mut hard_failures: HashSet<String> = HashSet::new();
    let mut results: Vec<NodeRun> = Vec::with_capacity(dag.nodes.len());

    for node_id in &run_order {
        let node = node_map
            .get(node_id.as_str())
            .copied()
            .ok_or_else(|| anyhow::anyhow!("missing node '{}'", node_id))?;

        if blocked.contains(&node.id) || hard_failures.contains(&node.id) {
            results.push(NodeRun {
                id: node.id.clone(),
                status: NodeStatus::Skipped,
                skipped_due_to: Some("blocked by upstream HARD failure".to_string()),
                duration_ms: 0,
                acceptance: None,
            });
            continue;
        }

        let node_start = Instant::now();
        let (status, acceptance) = execute_node(node, &cli.workspace_root)?;
        let duration_ms = node_start.elapsed().as_millis();

        if let NodeStatus::HardFailure = status {
            hard_failures.insert(node.id.clone());
            if let Some(children) = reverse_graph.get(&node.id) {
                for child in children {
                    block_downstream(child, &reverse_graph, &mut blocked);
                }
            }
        }

        results.push(NodeRun {
            id: node.id.clone(),
            status,
            skipped_due_to: None,
            duration_ms,
            acceptance: acceptance.map(into_acceptance_summary),
        });
    }

    let total = results.len();
    let success = results
        .iter()
        .filter(|result| matches!(result.status, NodeStatus::Success))
        .count();
    let hard_count = results
        .iter()
        .filter(|result| matches!(result.status, NodeStatus::HardFailure))
        .count();
    let soft_count = results
        .iter()
        .filter(|result| matches!(result.status, NodeStatus::SoftFailure))
        .count();
    let skipped = results
        .iter()
        .filter(|result| matches!(result.status, NodeStatus::Skipped))
        .count();

    Ok(DagScorecard {
        nodes: results,
        total,
        success,
        hard_failures: hard_count,
        soft_failures: soft_count,
        skipped,
        execution_order: run_order,
        cycle_detected: false,
        total_duration_ms: run_start.elapsed().as_millis(),
    })
}

fn block_downstream(
    node_id: &String,
    reverse_graph: &HashMap<String, Vec<String>>,
    blocked: &mut HashSet<String>,
) {
    if blocked.contains(node_id) {
        return;
    }

    blocked.insert(node_id.clone());
    if let Some(children) = reverse_graph.get(node_id) {
        for child_id in children {
            block_downstream(child_id, reverse_graph, blocked);
        }
    }
}

fn execute_node(
    node: &DagNode,
    cli_workspace_root: &Path,
) -> Result<(NodeStatus, Option<AcceptanceScoreCard>)> {
    let config = node_contract_config(node);
    let workspace = config
        .workspace
        .unwrap_or_else(|| cli_workspace_root.to_path_buf());
    let baseline = config
        .baseline_path
        .unwrap_or_else(|| workspace.join("acceptance-baselines.json"));

    let card = run_acceptance(
        &config.path,
        &baseline,
        &workspace,
        ExecutionContext {
            skip_delegation: config.skip_delegation,
            update_baseline: config.update_baseline,
        },
    )?;

    let status = match card.hard_passed {
        true if card.max_soft_score == 0.0 => NodeStatus::Success,
        true if card.max_soft_score > 0.0 && card.soft_percentage < 100.0 => {
            NodeStatus::SoftFailure
        }
        true => NodeStatus::Success,
        false => NodeStatus::HardFailure,
    };

    Ok((status, Some(card)))
}

fn node_contract_config(node: &DagNode) -> ContractConfig {
    match &node.contract {
        ContractDescriptor::Path(path) => ContractConfig {
            path: PathBuf::from(path),
            baseline_path: None,
            workspace: None,
            skip_delegation: false,
            update_baseline: false,
        },
        ContractDescriptor::Config(config) => config.clone(),
    }
}

fn topological_sort(nodes: &[DagNode]) -> Result<Vec<String>> {
    let mut indegree: HashMap<String, usize> = HashMap::new();
    let mut adjacency: HashMap<String, Vec<String>> = HashMap::new();
    let mut node_ids: HashSet<&str> = HashSet::new();

    for node in nodes {
        if node_ids.contains(node.id.as_str()) {
            return Err(anyhow::anyhow!("duplicate node id '{}'", node.id));
        }
        node_ids.insert(&node.id);
        indegree.insert(node.id.clone(), 0);
    }

    for node in nodes {
        for dep in &node.depends_on {
            if !node_ids.contains(dep.as_str()) {
                return Err(anyhow::anyhow!(
                    "node '{}' depends on missing node '{}'",
                    node.id,
                    dep
                ));
            }
            *indegree.entry(node.id.clone()).or_insert(0) += 1;
            adjacency
                .entry(dep.clone())
                .or_default()
                .push(node.id.clone());
        }
    }

    let mut queue = VecDeque::new();
    for (id, deg) in &indegree {
        if *deg == 0 {
            queue.push_back(id.clone());
        }
    }

    let mut ordered = Vec::with_capacity(nodes.len());
    while let Some(id) = queue.pop_front() {
        ordered.push(id.clone());
        if let Some(children) = adjacency.get(&id) {
            for child in children {
                let entry = indegree
                    .get_mut(child)
                    .ok_or_else(|| anyhow::anyhow!("invalid DAG edge '{}'", child))?;
                if *entry > 0 {
                    *entry -= 1;
                    if *entry == 0 {
                        queue.push_back(child.clone());
                    }
                }
            }
        }
    }

    if ordered.len() != nodes.len() {
        let circular = indegree
            .into_iter()
            .filter(|(_, degree)| *degree > 0)
            .map(|(id, _)| id)
            .collect::<Vec<_>>()
            .join(", ");
        return Err(anyhow::anyhow!(
            "cycle detected before execution; unresolved nodes: {}",
            circular
        ));
    }

    Ok(ordered)
}

fn into_acceptance_summary(card: AcceptanceScoreCard) -> AcceptanceNodeResult {
    AcceptanceNodeResult {
        contract_path: card.contract_path,
        hard_passed: card.hard_passed,
        soft_percentage: card.soft_percentage,
        hard_requirement_count: card.hard_requirements.len(),
        soft_requirement_count: card.soft_requirements.len(),
    }
}
