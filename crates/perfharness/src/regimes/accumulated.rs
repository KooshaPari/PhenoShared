//! Regime 2 — Accumulated: sequential throughput + long-running RSS memory profile.
//!
//! Sub-regimes:
//!   a) Sequential N-runs throughput — run the command N times back-to-back, report
//!      total / mean / rps. OS page-cache amortizes I/O after the first run.
//!   b) Long-running memory — spawn one long-lived instance (hold open via stdin pipe)
//!      and poll RSS every `rss_poll_ms` for `long_running_secs` seconds. Flag the
//!      forgecode-3GB-class pattern: >2× RSS growth from baseline.

use crate::HarnessConfig;
use anyhow::Result;
use std::time::Instant;
use sysinfo::{Pid, ProcessRefreshKind, RefreshKind, System};
use tokio::process::Command;
use tokio::time::{sleep, timeout, Duration};
use tracing::debug;

/// A single RSS poll sample.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct RssSample {
    /// Milliseconds elapsed since process spawn.
    pub elapsed_ms: u64,
    /// RSS in kilobytes at sample time.
    pub rss_kb: u64,
}

/// Result of the accumulated regime.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct AccumulatedResult {
    /// Number of sequential runs executed.
    pub sequential_runs: usize,
    /// Total wall-clock for all sequential runs (ms).
    pub sequential_total_ms: f64,
    /// Throughput in runs-per-second.
    pub throughput_rps: f64,
    /// RSS samples collected during long-running sub-regime (empty if skipped).
    pub rss_samples: Vec<RssSample>,
    /// True when max RSS > 2× min RSS (forgecode-class growth pattern).
    pub memory_leak_flag: bool,
}

/// Run N sequential copies of the target, then optionally run a long-lived RSS profile.
pub async fn run(cfg: &HarnessConfig) -> Result<AccumulatedResult> {
    // (a) Sequential throughput.
    let t0 = Instant::now();
    let n = cfg.accumulated_runs;
    for i in 0..n {
        let mut cmd = build_command(cfg);
        cmd.stdout(std::process::Stdio::null());
        cmd.stderr(std::process::Stdio::null());
        let child = cmd.spawn()?;
        timeout(
            Duration::from_secs(cfg.run_timeout_secs.max(1)),
            child.wait_with_output(),
        )
        .await??;
        debug!("sequential run {}/{} done", i + 1, n);
    }
    let sequential_total_ms = t0.elapsed().as_secs_f64() * 1000.0;
    let throughput_rps = n as f64 / (sequential_total_ms / 1000.0).max(f64::EPSILON);

    // (b) Long-running RSS profile (optional).
    let (rss_samples, memory_leak_flag) = if cfg.long_running_secs > 0 {
        collect_rss_profile(cfg).await?
    } else {
        (vec![], false)
    };

    Ok(AccumulatedResult {
        sequential_runs: n,
        sequential_total_ms,
        throughput_rps,
        rss_samples,
        memory_leak_flag,
    })
}

async fn collect_rss_profile(cfg: &HarnessConfig) -> Result<(Vec<RssSample>, bool)> {
    let mut cmd = build_command(cfg);
    // Pipe stdin so the child stays alive (it will block reading stdin if it expects input;
    // for short-lived commands this just keeps the process alive until we kill it).
    cmd.stdin(std::process::Stdio::piped());
    cmd.stdout(std::process::Stdio::null());
    cmd.stderr(std::process::Stdio::null());

    let mut child = cmd.spawn()?;
    let pid = child.id().expect("child has no PID");

    let t0 = Instant::now();
    let poll_dur = Duration::from_millis(cfg.rss_poll_ms.max(100));
    let run_dur = Duration::from_secs(cfg.long_running_secs);

    let mut sys = System::new_with_specifics(
        RefreshKind::nothing().with_processes(ProcessRefreshKind::nothing().with_memory()),
    );

    let mut samples: Vec<RssSample> = Vec::new();

    loop {
        if t0.elapsed() >= run_dur {
            break;
        }
        sleep(poll_dur).await;

        sys.refresh_processes_specifics(
            sysinfo::ProcessesToUpdate::All,
            true,
            ProcessRefreshKind::nothing().with_memory(),
        );
        if let Some(proc) = sys.process(Pid::from_u32(pid)) {
            samples.push(RssSample {
                elapsed_ms: t0.elapsed().as_millis() as u64,
                rss_kb: proc.memory() / 1024,
            });
        }
    }

    // Kill the long-running child.
    let _ = child.kill().await;
    let _ = child.wait().await;

    let leak_flag = detect_leak(&samples);
    Ok((samples, leak_flag))
}

/// Flag when max RSS > 2× min RSS (forgecode-3GB-class pattern).
fn detect_leak(samples: &[RssSample]) -> bool {
    if samples.len() < 2 {
        return false;
    }
    let min = samples.iter().map(|s| s.rss_kb).min().unwrap_or(0);
    let max = samples.iter().map(|s| s.rss_kb).max().unwrap_or(0);
    min > 0 && max > min * 2
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::HarnessConfig;

    fn echo_cfg(n: usize) -> HarnessConfig {
        HarnessConfig {
            command: vec!["echo".into(), "hi".into()],
            accumulated_runs: n,
            long_running_secs: 0, // skip RSS for fast tests
            run_timeout_secs: 5,
            ..Default::default()
        }
    }

    #[tokio::test]
    async fn sequential_throughput_is_positive() {
        let cfg = echo_cfg(5);
        let result = run(&cfg).await.unwrap();
        assert_eq!(result.sequential_runs, 5);
        assert!(result.sequential_total_ms > 0.0);
        assert!(result.throughput_rps > 0.0);
    }

    #[tokio::test]
    async fn rss_samples_empty_when_long_running_secs_zero() {
        let cfg = echo_cfg(3);
        let result = run(&cfg).await.unwrap();
        assert!(result.rss_samples.is_empty());
        assert!(!result.memory_leak_flag);
    }

    #[test]
    fn detect_leak_flags_2x_growth() {
        let samples = vec![
            RssSample {
                elapsed_ms: 0,
                rss_kb: 10_000,
            },
            RssSample {
                elapsed_ms: 500,
                rss_kb: 25_000,
            },
        ];
        assert!(detect_leak(&samples));
    }

    #[test]
    fn detect_leak_ok_for_stable_rss() {
        let samples = vec![
            RssSample {
                elapsed_ms: 0,
                rss_kb: 10_000,
            },
            RssSample {
                elapsed_ms: 500,
                rss_kb: 10_200,
            },
        ];
        assert!(!detect_leak(&samples));
    }

    #[test]
    fn detect_leak_ok_for_single_sample() {
        let samples = vec![RssSample {
            elapsed_ms: 0,
            rss_kb: 50_000,
        }];
        assert!(!detect_leak(&samples));
    }
}
