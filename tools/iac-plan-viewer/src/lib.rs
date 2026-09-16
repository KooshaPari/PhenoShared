//! # IaC Plan Viewer
//!
//! A WASM-compiled library that parses Terraform/OpenTofu `plan JSON`
//! and exposes interactive diff summaries to the browser.
//!
//! ## Input format
//!
//! The expected input is the output of `terraform show -json` or
//! `tofu show -json` — a structured JSON document specified in the
//! [Terraform JSON output format] spec.
//!
//! [Terraform JSON output format]: https://developer.hashicorp.com/terraform/internals/json-format

use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;

// ---------------------------------------------------------------------------
// Types that mirror the Terraform plan JSON output format
// ---------------------------------------------------------------------------

/// Top-level Terraform plan JSON document.
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct PlanDocument {
    pub format_version: String,
    pub terraform_version: Option<String>,
    pub planned_values: Option<PlannedValues>,
    pub resource_changes: Vec<ResourceChange>,
    pub output_changes: Option<std::collections::HashMap<String, OutputChange>>,
    pub configuration: Option<serde_json::Value>,
    pub relevant_attributes: Option<serde_json::Value>,
    pub timestamp: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct PlannedValues {
    pub root_module: Option<Module>,
    pub output_values: Option<std::collections::HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Module {
    pub resources: Vec<Resource>,
    pub child_modules: Option<Vec<Module>>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Resource {
    pub address: String,
    pub mode: String,
    #[serde(rename = "type")]
    pub resource_type: String,
    pub name: String,
    pub provider_name: String,
    pub values: Option<serde_json::Value>,
    pub index: Option<serde_json::Value>,
}

/// A single resource change as reported by the plan.
#[derive(Debug, Deserialize, Serialize)]
pub struct ResourceChange {
    pub address: String,
    pub module_address: Option<String>,
    pub mode: String,
    #[serde(rename = "type")]
    pub resource_type: String,
    pub name: String,
    pub provider_name: String,
    pub change: Change,
    pub index: Option<serde_json::Value>,
    pub deposed: Option<String>,
}

/// The change block describing before/after state and the action taken.
#[derive(Debug, Deserialize, Serialize)]
pub struct Change {
    pub actions: Vec<String>,
    pub before: Option<serde_json::Value>,
    pub after: Option<serde_json::Value>,
    pub after_unknown: Option<serde_json::Value>,
    pub before_sensitive: Option<serde_json::Value>,
    pub after_sensitive: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct OutputChange {
    pub actions: Vec<String>,
    pub before: Option<serde_json::Value>,
    pub after: Option<serde_json::Value>,
}

// ---------------------------------------------------------------------------
// Aggregated summary — what the browser actually renders
// ---------------------------------------------------------------------------

/// A human-readable summary row describing one changed resource.
#[derive(Debug, Serialize, Deserialize)]
pub struct ResourceDiff {
    pub address: String,
    pub resource_type: String,
    pub action: String,
    pub provider: String,
}

/// Aggregated plan statistics.
#[derive(Debug, Serialize, Deserialize)]
pub struct PlanSummary {
    pub total_resources: usize,
    pub create: usize,
    pub update: usize,
    pub delete: usize,
    pub no_op: usize,
    pub read: usize,
    pub replace: usize,
    pub resources: Vec<ResourceDiff>,
    pub terraform_version: Option<String>,
    pub timestamp: Option<String>,
}

impl PlanSummary {
    fn from_plan(plan: PlanDocument) -> Self {
        let mut create = 0usize;
        let mut update = 0usize;
        let mut delete = 0usize;
        let mut no_op = 0usize;
        let mut read = 0usize;
        let mut replace = 0usize;
        let mut resources = Vec::new();

        for rc in &plan.resource_changes {
            let action = classify_action(&rc.change.actions);
            match action.as_str() {
                "create" => create += 1,
                "update" => update += 1,
                "delete" => delete += 1,
                "no-op" => no_op += 1,
                "read" => read += 1,
                "replace" => replace += 1,
                _ => {}
            }
            resources.push(ResourceDiff {
                address: rc.address.clone(),
                resource_type: format!("{}.{}", rc.mode, rc.resource_type),
                action,
                provider: rc.provider_name.clone(),
            });
        }

        Self {
            total_resources: plan.resource_changes.len(),
            create,
            update,
            delete,
            no_op,
            read,
            replace,
            resources,
            terraform_version: plan.terraform_version,
            timestamp: plan.timestamp,
        }
    }
}

/// Classify a change based on its actions vector.
fn classify_action(actions: &[String]) -> String {
    if actions.len() == 1 {
        actions[0].clone()
    } else if actions.len() >= 2 {
        "replace".to_string()
    } else {
        "unknown".to_string()
    }
}

// ---------------------------------------------------------------------------
// WASM-exported public API
// ---------------------------------------------------------------------------

/// Parse a Terraform/OpenTofu plan JSON string and return a JSON summary.
#[wasm_bindgen]
pub fn parse_plan(plan_json: &str) -> Result<JsValue, JsValue> {
    let plan: PlanDocument =
        serde_json::from_str(plan_json).map_err(|e| JsValue::from_str(&e.to_string()))?;
    let summary = PlanSummary::from_plan(plan);
    Ok(serde_json::to_string(&summary)
        .map_err(|e| JsValue::from_str(&e.to_string()))?
        .into())
}

/// Return the number of resource changes grouped by action as a JSON string.
#[wasm_bindgen]
pub fn plan_change_counts(plan_json: &str) -> Result<JsValue, JsValue> {
    let plan: PlanDocument =
        serde_json::from_str(plan_json).map_err(|e| JsValue::from_str(&e.to_string()))?;
    let summary = PlanSummary::from_plan(plan);
    let counts = serde_json::json!({
        "create": summary.create,
        "update": summary.update,
        "delete": summary.delete,
        "no_op": summary.no_op,
        "read": summary.read,
        "replace": summary.replace,
    });
    Ok(serde_json::to_string(&counts)
        .map_err(|e| JsValue::from_str(&e.to_string()))?
        .into())
}

/// Verify the WASM module loaded correctly.
#[wasm_bindgen]
pub fn version() -> String {
    format!("iac-plan-viewer/{}", env!("CARGO_PKG_VERSION"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_plan_json() -> &'static str {
        r#"{
            "format_version": "1.2",
            "terraform_version": "1.9.0",
            "planned_values": { "root_module": { "resources": [] } },
            "resource_changes": [
                {
                    "address": "aws_instance.web",
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "web",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["create"], "before": null, "after": {"ami": "ami-12345"} }
                },
                {
                    "address": "aws_security_group.sg",
                    "mode": "managed",
                    "type": "aws_security_group",
                    "name": "sg",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["update"], "before": {"name": "old"}, "after": {"name": "new"} }
                },
                {
                    "address": "aws_s3_bucket.old",
                    "mode": "managed",
                    "type": "aws_s3_bucket",
                    "name": "old",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["delete"], "before": {"bucket": "old-bucket"}, "after": null }
                },
                {
                    "address": "data.aws_ami.ubuntu",
                    "mode": "data",
                    "type": "aws_ami",
                    "name": "ubuntu",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["read"], "before": null, "after": {"id": "ami-xxx"} }
                },
                {
                    "address": "aws_instance.replaced",
                    "mode": "managed",
                    "type": "aws_instance",
                    "name": "replaced",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["delete", "create"], "before": {"ami": "ami-old"}, "after": {"ami": "ami-new"} }
                },
                {
                    "address": "aws_lb.existing",
                    "mode": "managed",
                    "type": "aws_lb",
                    "name": "existing",
                    "provider_name": "hashicorp/aws",
                    "change": { "actions": ["no-op"], "before": {"name": "alb"}, "after": {"name": "alb"} }
                }
            ]
        }"#
    }

    #[test]
    fn parse_sample_plan() {
        let plan: PlanDocument = serde_json::from_str(sample_plan_json()).unwrap();
        assert_eq!(plan.format_version, "1.2");
        assert_eq!(plan.resource_changes.len(), 6);
    }

    #[test]
    fn summarize_sample_plan() {
        let plan: PlanDocument = serde_json::from_str(sample_plan_json()).unwrap();
        let summary = PlanSummary::from_plan(plan);
        assert_eq!(summary.create, 1);
        assert_eq!(summary.update, 1);
        assert_eq!(summary.delete, 1);
        assert_eq!(summary.read, 1);
        assert_eq!(summary.replace, 1);
        assert_eq!(summary.no_op, 1);
        assert_eq!(summary.total_resources, 6);
    }

    #[test]
    fn classify_actions() {
        let a = |s: &str| s.to_string();
        assert_eq!(classify_action(&[a("create")]), "create");
        assert_eq!(classify_action(&[a("update")]), "update");
        assert_eq!(classify_action(&[a("delete")]), "delete");
        assert_eq!(classify_action(&[a("no-op")]), "no-op");
        assert_eq!(classify_action(&[a("read")]), "read");
        assert_eq!(classify_action(&[a("delete"), a("create")]), "replace");
        assert_eq!(classify_action(&[a("create"), a("delete")]), "replace");
    }

    #[test]
    fn wasm_version_string() {
        let v = version();
        assert!(v.starts_with("iac-plan-viewer/"));
    }
}
