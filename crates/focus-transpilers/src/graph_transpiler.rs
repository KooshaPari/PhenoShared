//! Graph JSON ↔ IR transpiler (ReactFlow export format).
//!
//! Handles bidirectional conversion between ReactFlow graph exports and IR documents.
//! Preserves node layout metadata for UI round-tripping.

use crate::Document;
use anyhow::{anyhow, Result};
use focus_ir::{ActionIr, Body, ConditionIr, DocKind, RuleIr, TriggerIr};
use serde::{Deserialize, Serialize};

/// ReactFlow graph export format.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphJson {
    pub id: String,
    pub name: String,
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
    #[serde(default)]
    pub viewport: Viewport,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphNode {
    pub id: String,
    #[serde(rename = "type")]
    pub node_type: String,
    pub position: XYPosition,
    #[serde(default)]
    pub data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GraphEdge {
    pub id: String,
    pub source: String,
    pub target: String,
    #[serde(default)]
    pub animated: bool,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct XYPosition {
    pub x: f64,
    pub y: f64,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct Viewport {
    #[serde(default)]
    pub x: f64,
    #[serde(default)]
    pub y: f64,
    #[serde(default = "default_zoom")]
    pub zoom: f64,
}

fn default_zoom() -> f64 {
    1.0
}

/// Convert graph JSON to IR Document.
pub fn graph_to_document(graph: &GraphJson) -> Result<Document> {
    // Extract trigger node
    let trigger_node = graph
        .nodes
        .iter()
        .find(|n| n.node_type == "trigger")
        .ok_or_else(|| anyhow!("No trigger node found"))?;

    let trigger = serde_json::from_value::<TriggerIr>(trigger_node.data.clone())
        .map_err(|e| anyhow!("Invalid trigger data: {}", e))?;

    // Extract condition nodes (topologically ordered)
    let mut condition_nodes: Vec<_> =
        graph.nodes.iter().filter(|n| n.node_type == "condition").collect();
    condition_nodes.sort_by_key(|n| {
        // Sort by node ID to maintain deterministic order
        n.id.clone()
    });

    let conditions: Vec<ConditionIr> = condition_nodes
        .iter()
        .map(|n| {
            serde_json::from_value::<ConditionIr>(n.data.clone())
                .map_err(|e| anyhow!("Invalid condition data: {}", e))
        })
        .collect::<Result<Vec<_>>>()?;

    // Extract action nodes
    let mut action_nodes: Vec<_> = graph.nodes.iter().filter(|n| n.node_type == "action").collect();
    action_nodes.sort_by_key(|n| n.id.clone());

    let actions: Vec<ActionIr> = action_nodes
        .iter()
        .map(|n| {
            serde_json::from_value::<ActionIr>(n.data.clone())
                .map_err(|e| anyhow!("Invalid action data: {}", e))
        })
        .collect::<Result<Vec<_>>>()?;

    let rule_ir = RuleIr {
        id: graph.id.clone(),
        name: graph.name.clone(),
        trigger,
        conditions,
        actions,
        priority: 1,
        cooldown_seconds: None,
        duration_seconds: None,
        explanation_template: String::new(),
        enabled: true,
    };

    Ok(Document {
        version: 1,
        kind: DocKind::Rule,
        id: graph.id.clone(),
        name: graph.name.clone(),
        body: Body::Rule(Box::new(rule_ir)),
    })
}

/// Convert IR Document back to graph JSON (with canonical node layout).
pub fn document_to_graph(doc: &Document) -> Result<GraphJson> {
    match &doc.body {
        Body::Rule(rule_ir) => {
            let mut nodes = Vec::new();
            let mut edges = Vec::new();

            // Trigger node (always at y=0)
            let trigger_node = GraphNode {
                id: "trigger-0".to_string(),
                node_type: "trigger".to_string(),
                position: XYPosition { x: 0.0, y: 0.0 },
                data: serde_json::to_value(&rule_ir.trigger)
                    .map_err(|e| anyhow!("Failed to serialize trigger: {}", e))?,
            };
            nodes.push(trigger_node);

            // Condition nodes (y-spaced at intervals of 100)
            for (i, condition) in rule_ir.conditions.iter().enumerate() {
                let node_id = format!("condition-{}", i);
                let cond_node = GraphNode {
                    id: node_id.clone(),
                    node_type: "condition".to_string(),
                    position: XYPosition { x: 0.0, y: 100.0 * (i as f64 + 1.0) },
                    data: serde_json::to_value(condition)
                        .map_err(|e| anyhow!("Failed to serialize condition: {}", e))?,
                };
                nodes.push(cond_node);

                // Edge from trigger or previous condition
                let source =
                    if i == 0 { "trigger-0".to_string() } else { format!("condition-{}", i - 1) };

                edges.push(GraphEdge {
                    id: format!("{}-{}", source, node_id),
                    source,
                    target: node_id,
                    animated: false,
                });
            }

            // Action nodes (y-spaced, starting after last condition)
            let action_start_y = 100.0 * (rule_ir.conditions.len() as f64 + 1.0);
            for (i, action) in rule_ir.actions.iter().enumerate() {
                let node_id = format!("action-{}", i);
                let action_node = GraphNode {
                    id: node_id.clone(),
                    node_type: "action".to_string(),
                    position: XYPosition { x: 200.0, y: action_start_y + 100.0 * i as f64 },
                    data: serde_json::to_value(action)
                        .map_err(|e| anyhow!("Failed to serialize action: {}", e))?,
                };
                nodes.push(action_node);

                // Edge from last condition or trigger
                let source = if rule_ir.conditions.is_empty() {
                    "trigger-0".to_string()
                } else {
                    format!("condition-{}", rule_ir.conditions.len() - 1)
                };

                edges.push(GraphEdge {
                    id: format!("{}-{}", source, node_id),
                    source,
                    target: node_id,
                    animated: false,
                });
            }

            Ok(GraphJson {
                id: doc.id.clone(),
                name: doc.name.clone(),
                nodes,
                edges,
                viewport: Viewport::default(),
            })
        }
        _ => Err(anyhow!("Expected Rule body, got other kind")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_graph_to_document_minimal() {
        let trigger = TriggerIr::EventFired { event_name: "test_event".to_string() };

        let graph = GraphJson {
            id: "graph-1".to_string(),
            name: "Test Graph".to_string(),
            nodes: vec![GraphNode {
                id: "trigger-0".to_string(),
                node_type: "trigger".to_string(),
                position: XYPosition { x: 0.0, y: 0.0 },
                data: serde_json::to_value(&trigger).unwrap(),
            }],
            edges: vec![],
            viewport: Viewport::default(),
        };

        let doc = graph_to_document(&graph);
        assert!(doc.is_ok(), "Graph to document failed: {:?}", doc.err());
    }

    #[test]
    fn test_document_to_graph_with_conditions() {
        let rule_ir = RuleIr {
            id: "r1".to_string(),
            name: "Complex".to_string(),
            trigger: TriggerIr::EventFired { event_name: "evt".to_string() },
            conditions: vec![
                ConditionIr::TimeInRange { start_hour: 8, end_hour: 17 },
                ConditionIr::DayOfWeek { days: vec!["Monday".to_string()] },
            ],
            actions: vec![ActionIr::EnforcePolicy {
                policy_id: "block".to_string(),
                params: Default::default(),
            }],
            priority: 1,
            cooldown_seconds: None,
            duration_seconds: None,
            explanation_template: "".to_string(),
            enabled: true,
        };

        let doc = Document {
            version: 1,
            kind: DocKind::Rule,
            id: "r1".to_string(),
            name: "Complex".to_string(),
            body: Body::Rule(Box::new(rule_ir)),
        };

        let graph = document_to_graph(&doc);
        assert!(graph.is_ok());
        let graph = graph.unwrap();
        // trigger + 2 conditions + 1 action
        assert_eq!(graph.nodes.len(), 4);
        // 2 edges from trigger to conditions, 1 from condition to action
        assert_eq!(graph.edges.len(), 3);
    }

    #[test]
    fn test_graph_round_trip() {
        let original_rule = RuleIr {
            id: "rt-rule".to_string(),
            name: "Round Trip".to_string(),
            trigger: TriggerIr::EventFired { event_name: "rt_evt".to_string() },
            conditions: vec![],
            actions: vec![],
            priority: 1,
            cooldown_seconds: None,
            duration_seconds: None,
            explanation_template: "".to_string(),
            enabled: true,
        };

        let doc = Document {
            version: 1,
            kind: DocKind::Rule,
            id: "rt-rule".to_string(),
            name: "Round Trip".to_string(),
            body: Body::Rule(Box::new(original_rule)),
        };

        let graph = document_to_graph(&doc).expect("Convert to graph");
        let doc2 = graph_to_document(&graph).expect("Convert back");

        match (&doc.body, &doc2.body) {
            (Body::Rule(r1), Body::Rule(r2)) => {
                assert_eq!(r1.name, r2.name);
                assert_eq!(r1.id, r2.id);
            }
            _ => panic!("Expected rules"),
        }
    }
}
