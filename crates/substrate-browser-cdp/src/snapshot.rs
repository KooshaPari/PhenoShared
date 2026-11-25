//! Normalized page snapshot built from the Chrome accessibility tree.
//!
//! The accessibility tree is the right source: it is what the browser already
//! computed for assistive technology, it is stable across DOM changes, and
//! selected nodes carry a `backendDOMNodeId` that can be resolved back to a live
//! element for clicking and typing.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Roles that a caller can reasonably act on.
const ACTIONABLE_ROLES: &[&str] = &[
    "button",
    "checkbox",
    "combobox",
    "disclosure triangle",
    "link",
    "listbox",
    "menu item",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "option",
    "radio",
    "searchbox",
    "slider",
    "spinbutton",
    "switch",
    "tab",
    "textbox",
    "treeitem",
];

/// One node in the normalized tree.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AxNode {
    /// Stable identifier within this snapshot.
    pub node_id: String,
    /// Accessibility role, empty when the node does not report one.
    pub role: String,
    /// Accessible name.
    pub name: String,
    /// True when this node can be clicked or typed into.
    pub actionable: bool,
    /// Opaque reference usable in [`crate::CdpProvider::click`] and friends.
    pub element_ref: Option<String>,
}

/// A parameterized browser page snapshot.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Snapshot {
    /// Snapshot format identifier.
    pub format: String,
    /// Page URL at capture time.
    pub url: String,
    /// Document title.
    pub title: String,
    /// Readable text extracted from the tree.
    pub text: String,
    /// Normalized nodes.
    pub nodes: Vec<AxNode>,
    /// The actionable subset of `nodes`, in document order.
    pub elements: Vec<AxNode>,
}

/// Result of normalizing an accessibility tree.
#[derive(Debug, Clone, Default)]
pub struct Normalized {
    /// All nodes.
    pub nodes: Vec<AxNode>,
    /// Actionable nodes only.
    pub elements: Vec<AxNode>,
    /// `element_ref` to CDP `backendNodeId`.
    pub backend_ids: BTreeMap<String, i64>,
    /// Flattened readable text.
    pub text: String,
}

fn string_field(node: &Value, key: &str) -> String {
    node.get(key)
        .and_then(|value| value.get("value"))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string()
}

/// Normalize a `Accessibility.getFullAXTree` node array.
pub fn normalize(ax_nodes: &[Value]) -> Normalized {
    let mut normalized = Normalized::default();
    let mut text = String::new();

    for node in ax_nodes {
        let ignored = node
            .get("ignored")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        if ignored {
            continue;
        }

        let role = string_field(node, "role");
        let name = string_field(node, "name");
        let node_id = node
            .get("nodeId")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_string();
        if node_id.is_empty() {
            continue;
        }

        let backend = node.get("backendDOMNodeId").and_then(Value::as_i64);
        let role_is_actionable = ACTIONABLE_ROLES.contains(&role.as_str());
        let actionable = role_is_actionable && backend.is_some();

        let element_ref = if actionable {
            let reference = format!("el_{}", normalized.elements.len() + 1);
            if let Some(backend) = backend {
                normalized.backend_ids.insert(reference.clone(), backend);
            }
            Some(reference)
        } else {
            None
        };

        let entry = AxNode {
            node_id,
            role: role.clone(),
            name: name.clone(),
            actionable,
            element_ref,
        };

        if !name.trim().is_empty() {
            let speaks = role.is_empty()
                || matches!(
                    role.as_str(),
                    "StaticText"
                        | "text"
                        | "heading"
                        | "button"
                        | "link"
                        | "listitem"
                        | "paragraph"
                        | "cell"
                );
            if speaks {
                text.push_str(name.trim());
                text.push('\n');
            }
        }

        normalized.nodes.push(entry.clone());
        if actionable {
            normalized.elements.push(entry);
        }
    }

    normalized.text = text;
    normalized
}

/// Assemble a [`Snapshot`] from a normalized tree and page identity.
pub fn snapshot_from(normalized: Normalized, url: String, title: String) -> Snapshot {
    Snapshot {
        format: "jcode.page_snapshot.v1".to_string(),
        url,
        title,
        text: normalized.text,
        nodes: normalized.nodes,
        elements: normalized.elements,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn tree() -> Vec<Value> {
        vec![
            json!({"nodeId": "1", "ignored": false, "role": {"value": "document"},
                   "name": {"value": ""}}),
            json!({"nodeId": "2", "ignored": false, "role": {"value": "heading"},
                   "name": {"value": "Example Domain"}}),
            json!({"nodeId": "3", "ignored": false, "role": {"value": "link"},
                   "name": {"value": "More information..."}, "backendDOMNodeId": 42}),
            json!({"nodeId": "4", "ignored": true, "role": {"value": "link"},
                   "name": {"value": "hidden"}, "backendDOMNodeId": 43}),
            json!({"nodeId": "5", "ignored": false, "role": {"value": "textbox"},
                   "name": {"value": "Email"}}),
        ]
    }

    #[test]
    fn skips_ignored_nodes() {
        let normalized = normalize(&tree());
        assert!(!normalized.nodes.iter().any(|n| n.name == "hidden"));
    }

    #[test]
    fn actionable_requires_a_backend_node_id() {
        let normalized = normalize(&tree());
        let link = normalized
            .elements
            .iter()
            .find(|n| n.role == "link")
            .expect("link is actionable");
        assert_eq!(link.element_ref.as_deref(), Some("el_1"));
        // A textbox without a backend id cannot be acted on.
        assert!(!normalized.elements.iter().any(|n| n.role == "textbox"));
    }

    #[test]
    fn text_includes_readable_content() {
        let normalized = normalize(&tree());
        assert!(normalized.text.contains("Example Domain"));
        assert!(normalized.text.contains("More information"));
    }
}
