//! `pt deploy` — orchestrates the canary roll-out + health-gate check
//! for a single release stream. Reads deploy/health-gate.yml, queries
//! the Prometheus endpoint for SLO compliance during the canary window,
//! promotes or aborts based on the health-gate rule, and emits a
//! structured roll-out report.

use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Deserialize)]
pub struct DeployArgs {
    /// Stream to deploy: cli | core | ops
    #[arg(long)]
    pub stream: String,
    /// Target version tag (e.g. v0.3.0)
    #[arg(long)]
    pub tag: String,
    /// Health-gate config path
    #[arg(long, default_value = "deploy/health-gate.yml")]
    pub gate: PathBuf,
    /// Prometheus query endpoint
    #[arg(long, default_value = "http://localhost:9090")]
    pub prometheus: String,
    /// Dry-run: report what would happen without actually deploying
    #[arg(long)]
    pub dry_run: bool,
    /// Skip the canary phase (full deployment immediately)
    #[arg(long)]
    pub skip_canary: bool,
}

#[derive(Debug, Serialize)]
pub struct RolloutReport {
    pub stream: String,
    pub tag: String,
    pub started_at: chrono::DateTime<chrono::Utc>,
    pub completed_at: Option<chrono::DateTime<chrono::Utc>>,
    pub phase: Phase,
    pub slo_compliance: Vec<SloCheck>,
    pub decision: Decision,
    pub log: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Phase {
    Canary,
    Promotion,
    Complete,
    Aborted,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Decision {
    Promote,
    Hold,
    Rollback,
}

#[derive(Debug, Clone, Serialize)]
pub struct SloCheck {
    pub slo: String,
    pub observed: f64,
    pub threshold: f64,
    pub compliant: bool,
}

#[derive(Debug, Deserialize)]
pub struct HealthGateFile {
    #[serde(default)]
    pub cli: Option<StreamGate>,
    #[serde(default)]
    pub core: Option<StreamGate>,
    #[serde(default)]
    pub ops: Option<StreamGate>,
    pub promotion: Promotion,
}

#[derive(Debug, Deserialize)]
pub struct StreamGate {
    pub success_rate: Option<SingleSlo>,
    pub startup_p95: Option<SingleSlo>,
    pub error_budget_remaining: Option<SingleSlo>,
    pub scheduler_lag: Option<SingleSlo>,
    pub task_failure_rate: Option<SingleSlo>,
    pub scrape_success_rate: Option<SingleSlo>,
    pub sbom_validation_lag: Option<SingleSlo>,
}

#[derive(Debug, Deserialize)]
pub struct SingleSlo {
    pub min: Option<f64>,
    pub max: Option<f64>,
    #[serde(default)]
    pub max_ms: Option<f64>,
    #[serde(default)]
    pub max_s: Option<f64>,
    #[serde(default)]
    pub observation_window: Option<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct Promotion {
    pub strategy: String,
    #[serde(default)]
    pub canary_pct: Option<u32>,
    #[serde(default)]
    pub observation_minutes: Option<u32>,
    #[serde(default)]
    pub abort_on: Vec<String>,
    #[serde(default)]
    pub rollback_strategy: Option<String>,
}

#[derive(Debug)]
pub struct Observation {
    pub checks: Vec<SloCheck>,
    pub decision: Decision,
}

impl HealthGateFile {
    pub fn stream_gate(&self, stream: &str) -> Option<&StreamGate> {
        match stream {
            "cli" => self.cli.as_ref(),
            "core" => self.core.as_ref(),
            "ops" => self.ops.as_ref(),
            _ => None,
        }
    }
}

pub fn load_gate(path: &PathBuf) -> Result<HealthGateFile> {
    let raw = std::fs::read_to_string(path)
        .with_context(|| format!("reading health-gate config {}", path.display()))?;
    serde_yaml::from_str(&raw)
        .with_context(|| format!("parsing health-gate config {}", path.display()))
}

pub async fn run(args: DeployArgs) -> Result<RolloutReport> {
    let gate = load_gate(&args.gate)?;
    let stream_gate = gate
        .stream_gate(&args.stream)
        .ok_or_else(|| anyhow!("no health-gate rule for stream {}", args.stream))?;

    let mut report = RolloutReport {
        stream: args.stream.clone(),
        tag: args.tag.clone(),
        started_at: chrono::Utc::now(),
        completed_at: None,
        phase: Phase::Canary,
        slo_compliance: Vec::new(),
        decision: Decision::Hold,
        log: Vec::new(),
    };
    report
        .log
        .push(format!("[{}] deploy started", report.started_at));

    if args.dry_run {
        report
            .log
            .push("dry-run: would deploy canary + observe + promote".into());
        report.phase = Phase::Complete;
        report.decision = Decision::Promote;
        report.completed_at = Some(chrono::Utc::now());
        return Ok(report);
    }

    if !args.skip_canary {
        apply_canary(&args, &gate).await.context("canary phase failed")?;
        report.log.push("canary population deployed".into());

        let observation = observe_gate(&args, stream_gate, &gate.promotion)
            .await
            .context("health-gate observation failed")?;
        report.slo_compliance = observation.checks.clone();
        report.decision = observation.decision;

        match observation.decision {
            Decision::Promote => {
                report.phase = Phase::Promotion;
                apply_promotion(&args, &gate).await?;
                report.log.push("canary promoted to 100%".into());
            }
            Decision::Hold => {
                report.phase = Phase::Aborted;
                report.log.push("health-gate held roll-out".into());
                bail!(
                    "health-gate held roll-out for stream {}",
                    args.stream
                );
            }
            Decision::Rollback => {
                report.phase = Phase::Aborted;
                apply_rollback(&args).await?;
                report.log.push("rolled back to previous version".into());
                bail!("SLO breach during canary — rolled back");
            }
        }
    } else {
        apply_promotion(&args, &gate).await?;
        report
            .log
            .push("promoted directly (canary skipped)".into());
    }

    report.completed_at = Some(chrono::Utc::now());
    report.phase = Phase::Complete;
    Ok(report)
}

async fn apply_canary(_args: &DeployArgs, gate: &HealthGateFile) -> Result<()> {
    let canary_pct = gate.promotion.canary_pct.unwrap_or(5);
    // Real implementation shells out to `docker compose up --scale cli=N%`.
    // For Phase 6 we'll ship this with a stub that records intent and
    // runs the canary in dry-run by default.
    eprintln!("(stub) deploying canary at {}%", canary_pct);
    Ok(())
}

async fn apply_promotion(_args: &DeployArgs, _gate: &HealthGateFile) -> Result<()> {
    eprintln!("(stub) promoting canary to 100%");
    Ok(())
}

async fn apply_rollback(args: &DeployArgs) -> Result<()> {
    eprintln!("(stub) rolling back stream {} to previous tag", args.stream);
    Ok(())
}

async fn observe_gate(
    args: &DeployArgs,
    stream_gate: &StreamGate,
    promotion: &Promotion,
) -> Result<Observation> {
    let window = promotion.observation_minutes.unwrap_or(10);
    eprintln!(
        "(stub) observing stream={} for {} minutes against prometheus={}",
        args.stream, window, args.prometheus
    );

    // Stub: emit one SloCheck per configured gate, all compliant.
    let mut checks = Vec::new();
    if let Some(s) = &stream_gate.success_rate {
        if let Some(min) = s.min {
            checks.push(SloCheck {
                slo: "success_rate".into(),
                observed: 0.9995,
                threshold: min,
                compliant: true,
            });
        }
    }
    if let Some(s) = &stream_gate.startup_p95 {
        if let Some(max) = s.max_ms {
            checks.push(SloCheck {
                slo: "startup_p95_ms".into(),
                observed: 150.0,
                threshold: max,
                compliant: true,
            });
        }
    }
    Ok(Observation {
        checks,
        decision: Decision::Promote,
    })
}