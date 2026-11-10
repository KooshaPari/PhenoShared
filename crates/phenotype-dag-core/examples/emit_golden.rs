//! Emits a fully-populated `DagSchema` as YAML, for the Go side to consume.
//!
//! Why an example and not a test: this file exists to produce a fixture that a
//! DIFFERENT language's test reads. `dagrun` (Go) claims to read this schema, and
//! the only way that claim is checkable is if the Rust crate - the schema's owner
//! - generates the document the Go test parses. A hand-written YAML fixture would
//! prove that Go agrees with my reading of schema.rs, which is precisely the
//! assumption that needs testing.
//!
//! Run:
//!   cargo run -p phenotype-dag-core --example emit_golden > dagschema-golden.yaml

use phenotype_dag_core::schema::{
    AcceptanceCriterion, AuditHook, HookTiming, Prerequisite, SchemaEdge, SchemaNode,
};
use phenotype_dag_core::serialize::DagSchema;
use std::collections::HashMap;

fn main() {
    let mut meta = HashMap::new();
    meta.insert("owner".to_string(), "platform".to_string());

    let nodes = vec![
        SchemaNode {
            id: "1".to_string(),
            label: Some("Freeze scope".to_string()),
            description: Some("Write the intent down before any work starts.".to_string()),
            prerequisites: vec![Prerequisite::EnvironmentVariable {
                variable: "TARGET_ENV".to_string(),
            }],
            acceptance: vec![AcceptanceCriterion::ExitCode { code: 0 }],
            audit_hooks: vec![AuditHook::LogEntry {
                message: "scope frozen".to_string(),
                level: "info".to_string(),
                timing: HookTiming::OnSuccess,
            }],
            metadata: Some(meta),
        },
        SchemaNode {
            id: "2".to_string(),
            label: Some("Build the thing".to_string()),
            description: Some("Implement and prove it.".to_string()),
            prerequisites: vec![
                Prerequisite::FileExists {
                    path: "artifacts/INTENT.md".to_string(),
                },
                Prerequisite::CustomScript {
                    command: "mkdir -p artifacts".to_string(),
                    description: Some("ensure the output dir".to_string()),
                },
                Prerequisite::ImageReady {
                    image: "golang:1.24".to_string(),
                },
            ],
            acceptance: vec![
                AcceptanceCriterion::OutputContains {
                    pattern: "ok".to_string(),
                    regex: false,
                },
                AcceptanceCriterion::CustomCheck {
                    command: "test -s artifacts/SPEC.md".to_string(),
                    description: Some("the spec is non-empty".to_string()),
                },
                AcceptanceCriterion::MetricThreshold {
                    metric: "coverage".to_string(),
                    min: Some(85.0),
                    max: None,
                },
            ],
            audit_hooks: vec![
                AuditHook::Webhook {
                    url: "https://example.invalid/hook".to_string(),
                    headers: None,
                    timing: HookTiming::Post,
                },
                AuditHook::Notify {
                    channel: "slack".to_string(),
                    message: "build done".to_string(),
                    timing: HookTiming::OnSuccess,
                },
            ],
            metadata: None,
        },
    ];

    let edges = vec![
        SchemaEdge {
            from: "1".to_string(),
            to: "2".to_string(),
            label: None,
            condition: None,
        },
        SchemaEdge {
            from: "1".to_string(),
            to: "2".to_string(),
            label: Some("retry path".to_string()),
            condition: Some("1.exit_code == 0".to_string()),
        },
    ];

    let schema = DagSchema {
        version: "2.0.0".to_string(),
        name: Some("golden".to_string()),
        nodes,
        edges,
    };

    // to_yaml is the crate's own serializer: whatever it emits IS the wire
    // format, so the Go reader has to cope with this and nothing else.
    print!("{}", schema.to_yaml().expect("serialize"));
}
