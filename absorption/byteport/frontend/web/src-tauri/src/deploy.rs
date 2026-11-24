//! Deployment planning for the `byteport deploy` subcommand.
//!
//! The planner is deliberately side-effect free: it materializes the stage
//! catalog as a graph, orders it with the rank-based scheduler from
//! [`byteport_dag`], and renders the result as JSON. Nothing here spawns a
//! process, so `byteport deploy` is safe to run in CI or on an operator
//! workstation, and the printed plan can be reviewed before anything is
//! applied.

use std::collections::HashMap;
use std::io::Write;

use byteport_dag::dag::{Dag, DagError};
use byteport_dag::scheduler;
use serde::Serialize;

use crate::CliError;

/// Targets whose stage commands have been validated.
///
/// Any other `--target` value still produces a plan, but the operator is
/// warned because the catalog has not been checked against it.
const KNOWN_TARGETS: &[&str] = &["docker", "local", "nanovms", "spin"];

/// The deployment stages BytePort ships with, in dependency order.
///
/// `byteport deploy` orders stages by running this catalog through
/// [`scheduler::schedule`], so the array order below only breaks ties between
/// stages that are otherwise independent.
const STAGE_CATALOG: &[StageSpec] = &[
    StageSpec {
        name: "validate target",
        command: "byteport target verify --target {target}",
        estimated_seconds: 5,
        depends_on: &[],
    },
    StageSpec {
        name: "prepare artifact",
        command: "byteport artifact build --target {target} --profile release",
        estimated_seconds: 120,
        depends_on: &["validate target"],
    },
    StageSpec {
        name: "apply configuration",
        command: "byteport config apply --target {target} --plan-only",
        estimated_seconds: 15,
        depends_on: &["prepare artifact"],
    },
];

/// One deployment stage before it is scheduled.
#[derive(Debug, Clone, Copy)]
struct StageSpec {
    /// Stage name; unique within a catalog.
    name: &'static str,
    /// Command template; `{target}` is replaced with the plan target.
    command: &'static str,
    /// Advisory duration estimate, in seconds.
    estimated_seconds: u32,
    /// Names of stages that must complete before this one starts.
    depends_on: &'static [&'static str],
}

/// A single scheduled stage, as serialized into the plan JSON.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
struct Stage {
    /// Stage name.
    name: String,
    /// Command the operator (or a future executor) would run.
    command: String,
    /// Advisory duration estimate, in seconds.
    estimated_seconds: u32,
}

/// The deployment plan emitted by `byteport deploy`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
struct DeployPlan {
    /// Requested deployment target.
    target: String,
    /// Stages in dependency order.
    stages: Vec<Stage>,
    /// Non-fatal advisories about the plan.
    warnings: Vec<String>,
}

/// Failure modes for plan assembly.
///
/// Both variants mean the compiled-in catalog is inconsistent rather than that
/// the user passed a bad target, so they are hard errors rather than warnings.
#[derive(Debug, thiserror::Error)]
pub(crate) enum PlanError {
    /// A stage declares a prerequisite that is not a stage.
    #[error("stage `{stage}` depends on unknown stage `{dependency}`")]
    UnknownDependency {
        /// Stage that declared the prerequisite.
        stage: String,
        /// Prerequisite name that is missing from the catalog.
        dependency: String,
    },
    /// The catalog contains a cycle, so no execution order exists.
    #[error("stage graph is not acyclic: {0}")]
    Dag(#[from] DagError),
}

/// `byteport deploy --target <NAME>` — print the deployment plan as JSON.
///
/// Plans only: no stage command is executed, and the process exits non-zero
/// only when the compiled-in catalog itself is unusable.
pub(crate) fn cmd_deploy(target: &str, out: &mut dyn Write) -> Result<(), CliError> {
    let plan = build_plan(target, STAGE_CATALOG)?;

    write_plan(out, &plan)
}

/// Serialize `plan` as pretty JSON followed by a newline.
///
/// The plan is written straight from its `Serialize` impl rather than routed
/// through the shared `write_json` helper: that helper takes a
/// `serde_json::Value`, whose maps are sorted, which would reorder the
/// documented `target`, `stages`, `warnings` keys.
fn write_plan(out: &mut dyn Write, plan: &DeployPlan) -> Result<(), CliError> {
    serde_json::to_writer_pretty(&mut *out, plan)?;
    out.write_all(b"\n")?;
    Ok(())
}

/// Assemble the deployment plan for `target` from `catalog`.
///
/// Stage order is derived from the dependency graph, not from the order the
/// entries happen to appear in `catalog`.
fn build_plan(target: &str, catalog: &[StageSpec]) -> Result<DeployPlan, PlanError> {
    let position: HashMap<&str, usize> = catalog
        .iter()
        .enumerate()
        .map(|(index, spec)| (spec.name, index))
        .collect();

    // 1. Materialize the catalog as a DAG.
    let mut graph: Dag<&str> = Dag::new();
    for spec in catalog {
        graph.add_node(spec.name)?;
    }
    for spec in catalog {
        for dependency in spec.depends_on {
            if !position.contains_key(dependency) {
                return Err(PlanError::UnknownDependency {
                    stage: spec.name.to_string(),
                    dependency: (*dependency).to_string(),
                });
            }
            graph.add_edge(*dependency, spec.name)?;
        }
    }

    // 2. Order the stages with the shared scheduler.
    let schedule = scheduler::schedule(&graph)?;

    // 3. Flatten the buckets into one ordered stage list. The scheduler
    //    returns nodes within a bucket in hash order, so sort each bucket by
    //    catalog position to keep the emitted JSON deterministic.
    let mut stages = Vec::with_capacity(catalog.len());
    for bucket in &schedule.buckets {
        let mut ordered: Vec<(usize, &str)> = bucket.iter().map(|name| (position[*name], *name)).collect();
        ordered.sort_unstable();

        for (index, _) in ordered {
            let spec = &catalog[index];
            stages.push(Stage {
                name: spec.name.to_string(),
                command: render_command(spec.command, target),
                estimated_seconds: spec.estimated_seconds,
            });
        }
    }

    Ok(DeployPlan {
        target: target.to_string(),
        stages,
        warnings: warnings_for(target, &schedule.buckets),
    })
}

/// Collect the non-fatal advisories for a plan.
///
/// Warnings never stop the command; they tell the operator where the printed
/// plan is approximate or where the planner changed the requested shape.
fn warnings_for(target: &str, buckets: &[Vec<&str>]) -> Vec<String> {
    let mut warnings = vec!["plan only: byteport deploy prints this plan and executes no stage".to_string()];

    if !KNOWN_TARGETS.contains(&target) {
        warnings.push(format!(
            "unknown target `{target}`: stage commands are unverified placeholders; known targets: {}",
            KNOWN_TARGETS.join(", ")
        ));
    }

    for (index, bucket) in buckets.iter().enumerate() {
        if bucket.len() < 2 {
            continue;
        }
        let mut names = bucket.to_vec();
        names.sort_unstable();
        warnings.push(format!(
            "bucket {index} holds {} independent stages ({}); the plan lists them sequentially",
            names.len(),
            names.join(", ")
        ));
    }

    warnings
}

/// Substitute the plan target into a stage command template.
fn render_command(template: &str, target: &str) -> String {
    template.replace("{target}", target)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    /// Two independent stages feeding one dependent stage, declared out of
    /// dependency order so the planner has to reorder them.
    const PARALLEL_CATALOG: &[StageSpec] = &[
        StageSpec {
            name: "beta",
            command: "byteport beta --target {target}",
            estimated_seconds: 20,
            depends_on: &[],
        },
        StageSpec {
            name: "alpha",
            command: "byteport alpha --target {target}",
            estimated_seconds: 10,
            depends_on: &[],
        },
        StageSpec {
            name: "release",
            command: "byteport release --target {target}",
            estimated_seconds: 5,
            depends_on: &["alpha", "beta"],
        },
    ];

    /// Render a plan through the real subcommand entry point.
    fn render(target: &str) -> Value {
        let mut buffer = Vec::new();
        cmd_deploy(target, &mut buffer).expect("deploy should render");
        serde_json::from_slice(&buffer).expect("deploy output should be valid json")
    }

    #[test]
    fn default_plan_has_at_least_one_stage() {
        let plan = build_plan("docker", STAGE_CATALOG).expect("catalog is valid");

        assert_eq!(plan.target, "docker");
        assert!(!plan.stages.is_empty());
        for stage in &plan.stages {
            assert!(!stage.name.is_empty(), "stage name is empty");
            assert!(!stage.command.is_empty(), "stage command is empty");
            assert!(
                stage.command.contains("docker"),
                "target is not substituted into `{}`",
                stage.command
            );
        }
    }

    #[test]
    fn plan_json_has_the_documented_shape() {
        let value = render("docker");

        assert!(value["stages"].is_array());
        assert!(value["warnings"].is_array());
        assert_eq!(value["target"], serde_json::json!("docker"));

        let stages = value["stages"].as_array().expect("stages is an array");
        assert!(!stages.is_empty(), "plan JSON has no stages");
        for stage in stages {
            assert!(stage["name"].is_string());
            assert!(stage["command"].is_string());
            assert!(stage["estimated_seconds"].is_u64());
        }
    }

    #[test]
    fn plan_json_keeps_the_documented_key_order() {
        let mut buffer = Vec::new();
        cmd_deploy("docker", &mut buffer).expect("deploy should render");
        let text = String::from_utf8(buffer).expect("output should be utf-8");

        let target_at = text.find("\"target\"").expect("target key is present");
        let stages_at = text.find("\"stages\"").expect("stages key is present");
        let warnings_at = text.find("\"warnings\"").expect("warnings key is present");

        assert!(
            target_at < stages_at && stages_at < warnings_at,
            "expected target, stages, warnings in that order, got: {text}"
        );
    }

    #[test]
    fn stage_order_follows_dependencies_not_catalog_order() {
        let plan = build_plan("docker", PARALLEL_CATALOG).expect("catalog is valid");
        let names: Vec<&str> = plan.stages.iter().map(|s| s.name.as_str()).collect();

        assert_eq!(names.len(), 3);
        let alpha = names.iter().position(|n| *n == "alpha").expect("alpha");
        let beta = names.iter().position(|n| *n == "beta").expect("beta");
        let release = names.iter().position(|n| *n == "release").expect("release");
        assert!(release > alpha, "release must run after alpha");
        assert!(release > beta, "release must run after beta");
    }

    #[test]
    fn independent_stages_are_reported_as_a_warning() {
        let plan = build_plan("docker", PARALLEL_CATALOG).expect("catalog is valid");

        assert!(
            plan.warnings
                .iter()
                .any(|warning| warning.contains("alpha") && warning.contains("beta")),
            "expected a parallel-stage warning, got {:?}",
            plan.warnings
        );
    }

    #[test]
    fn unknown_target_warns_but_known_target_does_not() {
        let unknown = build_plan("mars", STAGE_CATALOG).expect("catalog is valid");
        assert!(
            unknown
                .warnings
                .iter()
                .any(|warning| warning.contains("unknown target `mars`")),
            "expected an unknown-target warning, got {:?}",
            unknown.warnings
        );
        assert!(unknown.stages.iter().all(|s| s.command.contains("mars")));

        let known = build_plan("docker", STAGE_CATALOG).expect("catalog is valid");
        assert!(
            !known.warnings.iter().any(|warning| warning.contains("unknown target")),
            "known target should not warn, got {:?}",
            known.warnings
        );
    }

    #[test]
    fn unknown_dependency_is_rejected() {
        const BROKEN: &[StageSpec] = &[StageSpec {
            name: "only",
            command: "byteport only --target {target}",
            estimated_seconds: 1,
            depends_on: &["missing"],
        }];

        let error = build_plan("docker", BROKEN).expect_err("catalog is inconsistent");
        assert!(matches!(error, PlanError::UnknownDependency { .. }));
    }

    #[test]
    fn plan_is_deterministic_across_builds() {
        let mut first = Vec::new();
        let mut second = Vec::new();
        cmd_deploy("docker", &mut first).expect("deploy should render");
        cmd_deploy("docker", &mut second).expect("deploy should render");

        assert_eq!(first, second);
    }
}
