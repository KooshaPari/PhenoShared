// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Dual-harness shared fixture adapter (Planify2 × helios-cli).
//!
//! Loads `shared-3task.v1.json` and executes the `helios_cli` adapter specs
//! via [`crate::Runner`]. Traces to FR-DH-001.

use crate::{RunError, Runner, RunnerConfig};
use serde::Deserialize;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Fixture root document (`pheno.dual_harness.fixture.v1`).
#[derive(Debug, Clone, Deserialize)]
pub struct DualHarnessFixture {
    pub schema_version: String,
    pub fixture_id: String,
    pub tasks: Vec<FixtureTask>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct FixtureTask {
    pub task_id: String,
    pub title: String,
    pub kind: String,
    pub acceptance: Acceptance,
    pub adapters: HashMap<String, AdapterSpec>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Acceptance {
    pub exit_code: Option<i32>,
    pub stdout_contains: Option<String>,
    pub stdout_path_prefix_env: Option<String>,
    pub must_error: Option<bool>,
    pub error_class: Option<String>,
    pub timeout_secs: Option<u64>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AdapterSpec {
    pub cmd: String,
    #[serde(default)]
    pub args: Vec<String>,
    pub working_dir_env: Option<String>,
    pub timeout_secs: Option<u64>,
}

/// Outcome of one fixture task under the helios adapter.
#[derive(Debug, Clone)]
pub struct TaskOutcome {
    pub task_id: String,
    pub passed: bool,
    pub detail: String,
}

/// Errors while loading or interpreting the fixture JSON.
#[derive(Debug, thiserror::Error)]
pub enum FixtureError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("fixture schema unsupported: {0}")]
    Schema(String),
    #[error("task {0} missing helios_cli adapter")]
    MissingAdapter(String),
    #[error("DUAL_HARNESS_WORKDIR unset (required for task {0})")]
    WorkdirUnset(String),
}

/// Load a dual-harness fixture from disk.
pub fn load_fixture(path: &Path) -> Result<DualHarnessFixture, FixtureError> {
    let raw = std::fs::read_to_string(path)?;
    let fixture: DualHarnessFixture = serde_json::from_str(&raw)?;
    if fixture.schema_version != "pheno.dual_harness.fixture.v1" {
        return Err(FixtureError::Schema(fixture.schema_version));
    }
    Ok(fixture)
}

/// Default path to the pheno-harness shared-3task fixture (repos layout).
pub fn default_shared_3task_path() -> PathBuf {
    // crates/harness_runner → helios worktree → worktrees → repos
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(5)
        .map(|repos| {
            repos
                .join("pheno-harness")
                .join("plans")
                .join("2026-07-22-dual-harness-matrix")
                .join("fixtures")
                .join("shared-3task.v1.json")
        })
        .unwrap_or_else(|| PathBuf::from("shared-3task.v1.json"))
}

/// Run all helios_cli adapter tasks; returns per-task outcomes.
pub async fn run_helios_fixture(
    fixture: &DualHarnessFixture,
) -> Result<Vec<TaskOutcome>, FixtureError> {
    let mut out = Vec::with_capacity(fixture.tasks.len());
    for task in &fixture.tasks {
        out.push(run_one_helios_task(task).await?);
    }
    Ok(out)
}

async fn run_one_helios_task(task: &FixtureTask) -> Result<TaskOutcome, FixtureError> {
    let adapter = task
        .adapters
        .get("helios_cli")
        .ok_or_else(|| FixtureError::MissingAdapter(task.task_id.clone()))?;

    let mut config = RunnerConfig::default();
    if let Some(secs) = adapter.timeout_secs.or(task.acceptance.timeout_secs) {
        config.timeout_secs = Some(secs);
    }
    if let Some(env_key) = &adapter.working_dir_env {
        let dir =
            std::env::var(env_key).map_err(|_| FixtureError::WorkdirUnset(task.task_id.clone()))?;
        config.working_dir = Some(dir);
    }

    let runner = Runner::with_config(config);
    let arg_refs: Vec<&str> = adapter.args.iter().map(String::as_str).collect();
    let result = runner.run(&adapter.cmd, &arg_refs).await;

    let passed = match (&task.acceptance, result) {
        (
            Acceptance { must_error: Some(true), error_class: Some(class), .. },
            Err(RunError::Timeout(_)),
        ) if class == "timeout" => true,
        (acceptance, Ok(run)) => {
            let mut ok = true;
            if let Some(code) = acceptance.exit_code {
                ok &= run.exit_code == Some(code);
            }
            if let Some(needle) = &acceptance.stdout_contains {
                ok &= run.stdout.contains(needle);
            }
            if let Some(env_key) = &acceptance.stdout_path_prefix_env {
                let prefix = std::env::var(env_key).unwrap_or_default();
                let stdout_path = PathBuf::from(run.stdout.trim());
                let prefix_path = PathBuf::from(&prefix);
                let stdout_canon = std::fs::canonicalize(&stdout_path).unwrap_or(stdout_path);
                let prefix_canon = std::fs::canonicalize(&prefix_path).unwrap_or(prefix_path);
                ok &= !prefix.is_empty()
                    && stdout_canon
                        .to_string_lossy()
                        .starts_with(prefix_canon.to_string_lossy().as_ref());
            }
            if acceptance.must_error == Some(true) {
                ok = false;
            }
            ok
        }
        (_, Err(e)) => {
            return Ok(TaskOutcome {
                task_id: task.task_id.clone(),
                passed: false,
                detail: format!("run error: {e}"),
            });
        }
    };

    Ok(TaskOutcome {
        task_id: task.task_id.clone(),
        passed,
        detail: if passed { "ok".into() } else { "acceptance failed".into() },
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    /// Traces to: FR-DH-001
    #[tokio::test]
    async fn shared_3task_fixture_passes_on_helios() {
        let path = std::env::var("DUAL_HARNESS_FIXTURE")
            .map(PathBuf::from)
            .unwrap_or_else(|_| default_shared_3task_path());
        if !path.is_file() {
            // Skip when fixture not present in this checkout layout.
            eprintln!("skip: fixture missing at {}", path.display());
            return;
        }
        let work = tempfile_workdir();
        std::env::set_var("DUAL_HARNESS_WORKDIR", &work);
        let fixture = load_fixture(&path).expect("load fixture");
        assert_eq!(fixture.tasks.len(), 3);
        let outcomes = run_helios_fixture(&fixture).await.expect("run");
        for o in &outcomes {
            assert!(o.passed, "{}: {}", o.task_id, o.detail);
        }
        let _ = std::fs::remove_dir_all(&work);
    }

    fn tempfile_workdir() -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "dual-harness-{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or(Duration::from_secs(0))
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).expect("mkdir");
        dir
    }
}
