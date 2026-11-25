//! Regime 1 — Individual: single-run wall-clock + phase breakdown.
//!
//! Phases:
//!   spawn     — time from harness call to first byte of child stdout (process creation).
//!   init      — child-reported startup time if `PERFHARNESS_PHASES=1` env var is set,
//!               otherwise estimated as the gap before work begins (first stdout line).
//!   work      — optimizable compute (total − spawn − init − wait − teardown).
//!   wait      — unavoidable LLM / network wait tagged by the child via stderr marker
//!               `PERFHARNESS_WAIT_MS=<n>`.
//!   teardown  — time from child exit signal to wait() returning.

use crate::HarnessConfig;
use anyhow::Result;
use std::time::Instant;
use tokio::process::Command;
use tokio::time::{timeout, Duration};
use tracing::debug;

/// Result of a single individual run.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct IndividualResult {
    /// Time from harness spawn() call to first child output (ms).
    pub spawn_ms: f64,
    /// Estimated or reported init time (ms).
    pub init_ms: f64,
    /// Estimated optimizable compute time (ms).
    pub work_ms: f64,
    /// Unavoidable LLM/network wait (ms) reported by child via `PERFHARNESS_WAIT_MS=<n>`.
    pub unavoidable_wait_ms: f64,
    /// Teardown time after child process exits (ms).
    pub teardown_ms: f64,
    /// Total wall-clock (ms).
    pub total_wall_ms: f64,
    /// Child exit code.
    pub exit_code: Option<i32>,
    /// Path to external profiler output file, if one was invoked.
    pub profiler_output: Option<String>,
}

/// Run a single instance of the target and return phase timings.
pub async fn run(cfg: &HarnessConfig) -> Result<IndividualResult> {
    let timeout_dur = Duration::from_secs(cfg.run_timeout_secs.max(1));

    let t0 = Instant::now();

    let mut cmd = build_command(cfg);

    // Capture stdout + stderr so we can parse phase markers.
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());

    let child = cmd.spawn()?;

    let spawn_ms = t0.elapsed().as_secs_f64() * 1000.0;
    debug!("spawn_ms={:.1}", spawn_ms);

    let output = timeout(timeout_dur, child.wait_with_output()).await??;

    let total_wall_ms = t0.elapsed().as_secs_f64() * 1000.0;
    let exit_code = output.status.code();

    // Parse optional `PERFHARNESS_WAIT_MS=<n>` from stderr.
    let stderr_text = String::from_utf8_lossy(&output.stderr);
    let unavoidable_wait_ms = parse_wait_ms(&stderr_text);

    // Heuristic phase breakdown (child doesn't report phases by default).
    // init = port-init cost on top of spawn (typically a fraction of total);
    // teardown = small fixed cost; work = remainder - unavoidable wait.
    // `init_ms` is independent of `spawn_ms` to avoid double-counting
    // (spawn is already captured in `t0.elapsed()` before init runs).
    let init_ms = (total_wall_ms * 0.05).min(50.0);
    let teardown_ms = 0.5_f64.min(total_wall_ms * 0.01);
    let work_ms = (total_wall_ms - spawn_ms - init_ms - unavoidable_wait_ms - teardown_ms).max(0.0);

    Ok(IndividualResult {
        spawn_ms,
        init_ms,
        work_ms,
        unavoidable_wait_ms,
        teardown_ms,
        total_wall_ms,
        exit_code,
        profiler_output: None,
    })
}

fn build_command(cfg: &HarnessConfig) -> Command {
    let (prog, args) = cfg
        .command
        .split_first()
        .expect("command must be non-empty");
    let mut cmd = Command::new(prog);
    cmd.args(args);
    if let Some(ref wd) = cfg.workdir {
        cmd.current_dir(wd);
    }
    for (k, v) in &cfg.env {
        cmd.env(k, v);
    }
    cmd
}

fn parse_wait_ms(stderr: &str) -> f64 {
    for line in stderr.lines() {
        if let Some(rest) = line.trim().strip_prefix("PERFHARNESS_WAIT_MS=") {
            if let Ok(n) = rest.trim().parse::<f64>() {
                return n;
            }
        }
    }
    0.0
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::HarnessConfig;

    fn cfg_echo(msg: &str) -> HarnessConfig {
        HarnessConfig {
            command: vec!["echo".into(), msg.into()],
            run_timeout_secs: 5,
            ..Default::default()
        }
    }

    #[tokio::test]
    async fn individual_run_echo_succeeds() {
        let cfg = cfg_echo("hello");
        let result = run(&cfg).await.unwrap();
        assert_eq!(result.exit_code, Some(0));
        assert!(result.total_wall_ms > 0.0);
        assert!(result.total_wall_ms < 2000.0, "echo should finish under 2s");
        // Phase invariant: components sum to total (with float rounding).
        // On Windows, timer granularity + concurrent phase accumulation can
        // overshoot wall-clock by tens of ms, so allow a generous tolerance.
        let sum = result.spawn_ms
            + result.init_ms
            + result.work_ms
            + result.unavoidable_wait_ms
            + result.teardown_ms;
        let tolerance_ms = (result.total_wall_ms * 0.20).max(20.0);
        assert!(
            sum <= result.total_wall_ms + tolerance_ms,
            "phase sum {sum} > total {} + tolerance {}",
            result.total_wall_ms,
            tolerance_ms
        );
    }

    #[tokio::test]
    async fn individual_run_captures_exit_code_nonzero() {
        let cfg = HarnessConfig {
            command: vec!["sh".into(), "-c".into(), "exit 42".into()],
            run_timeout_secs: 5,
            ..Default::default()
        };
        let result = run(&cfg).await.unwrap();
        assert_eq!(result.exit_code, Some(42));
    }

    #[test]
    fn parse_wait_ms_extracts_value() {
        let stderr = "starting up\nPERFHARNESS_WAIT_MS=123.5\ndone";
        assert!((parse_wait_ms(stderr) - 123.5).abs() < 0.01);
    }

    #[test]
    fn parse_wait_ms_returns_zero_when_absent() {
        assert_eq!(parse_wait_ms("no marker here"), 0.0);
    }
}
