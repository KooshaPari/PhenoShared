//! Regime 3 — Scaled-parallel: throughput vs concurrency (packing-density metric).
//!
//! Runs M concurrent copies of the target for each M in the parallel_ladder, measures
//! wall-clock for all M to complete, computes throughput (runs/s), and detects the
//! plateau/degradation inflection point.
//!
//! The plateau is the last M where throughput is still improving (delta_rps > 5%).
//! Degradation is the first M where throughput falls below the plateau value.

use crate::HarnessConfig;
use anyhow::Result;
use std::time::Instant;
use tokio::process::Command;
use tokio::task::JoinSet;
use tokio::time::{timeout, Duration};
use tracing::debug;

/// A single point on the scaling curve.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ScaleCurvePoint {
    /// Concurrency level M.
    pub concurrency: usize,
    /// Throughput at this concurrency (runs/second).
    pub throughput_rps: f64,
    /// Mean per-run wall-clock (ms).
    pub mean_run_ms: f64,
}

/// Result of the scaled-parallel regime.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ScaledParallelResult {
    /// Full scaling curve.
    pub curve: Vec<ScaleCurvePoint>,
    /// Concurrency at which throughput plateaus.
    pub plateau_concurrency: usize,
    /// Throughput at the plateau (runs/second).
    pub plateau_throughput_rps: f64,
    /// First concurrency where throughput degrades below plateau.
    pub degradation_concurrency: usize,
}

/// Run the scaled-parallel regime over the configured ladder.
pub async fn run(cfg: &HarnessConfig) -> Result<ScaledParallelResult> {
    let timeout_dur = Duration::from_secs(cfg.run_timeout_secs.max(1));
    let mut curve: Vec<ScaleCurvePoint> = Vec::new();

    for &m in &cfg.parallel_ladder {
        debug!("scaled-parallel: M={}", m);
        let t0 = Instant::now();

        let mut set: JoinSet<Result<()>> = JoinSet::new();
        for _ in 0..m {
            let cmd_vec = cfg.command.clone();
            let workdir = cfg.workdir.clone();
            let env = cfg.env.clone();
            set.spawn(async move {
                let (prog, args) = cmd_vec.split_first().expect("non-empty");
                let mut cmd = Command::new(prog);
                cmd.args(args);
                cmd.stdout(std::process::Stdio::null());
                cmd.stderr(std::process::Stdio::null());
                if let Some(ref wd) = workdir {
                    cmd.current_dir(wd);
                }
                for (k, v) in &env {
                    cmd.env(k, v);
                }
                let child = cmd.spawn()?;
                timeout(Duration::from_secs(30), child.wait_with_output()).await??;
                Ok(())
            });
        }

        // Wait for all M runs to complete.
        let mut errors = 0usize;
        while let Some(res) = set.join_next().await {
            if res.is_err() || res.unwrap().is_err() {
                errors += 1;
            }
        }

        let wall_ms = t0.elapsed().as_secs_f64() * 1000.0;
        let successful = (m - errors) as f64;
        let throughput_rps = successful / (wall_ms / 1000.0).max(f64::EPSILON);
        let mean_run_ms = if successful > 0.0 {
            wall_ms / successful
        } else {
            0.0
        };

        debug!("M={} wall_ms={:.0} rps={:.2}", m, wall_ms, throughput_rps);
        curve.push(ScaleCurvePoint {
            concurrency: m,
            throughput_rps,
            mean_run_ms,
        });

        // Small pause between ladder steps to let OS scheduler recover.
        tokio::time::sleep(Duration::from_millis(200)).await;
        let _ = timeout_dur; // suppress unused warning
    }

    let (plateau_concurrency, plateau_throughput_rps, degradation_concurrency) =
        find_plateau_and_degradation(&curve);

    Ok(ScaledParallelResult {
        curve,
        plateau_concurrency,
        plateau_throughput_rps,
        degradation_concurrency,
    })
}

/// Find the plateau (last M with >5% gain) and degradation (first M below plateau).
fn find_plateau_and_degradation(curve: &[ScaleCurvePoint]) -> (usize, f64, usize) {
    if curve.is_empty() {
        return (0, 0.0, 0);
    }

    let mut plateau_idx = 0;
    for i in 1..curve.len() {
        let prev = curve[i - 1].throughput_rps;
        let curr = curve[i].throughput_rps;
        if prev > 0.0 && (curr - prev) / prev > 0.05 {
            plateau_idx = i;
        }
    }

    let plateau_rps = curve[plateau_idx].throughput_rps;
    let plateau_m = curve[plateau_idx].concurrency;

    // Degradation: first point after plateau where rps falls below plateau.
    let mut degradation_m = plateau_m;
    for point in curve.iter().skip(plateau_idx + 1) {
        if point.throughput_rps < plateau_rps {
            degradation_m = point.concurrency;
            break;
        }
    }

    (plateau_m, plateau_rps, degradation_m)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::HarnessConfig;

    fn echo_parallel_cfg() -> HarnessConfig {
        HarnessConfig {
            command: vec!["echo".into(), "parallel".into()],
            // Small ladder for fast tests.
            parallel_ladder: vec![1, 2, 4],
            run_timeout_secs: 10,
            ..Default::default()
        }
    }

    #[tokio::test]
    async fn scaled_parallel_produces_curve_for_each_ladder_step() {
        let cfg = echo_parallel_cfg();
        let result = run(&cfg).await.unwrap();
        assert_eq!(result.curve.len(), 3, "one point per ladder step");
        for point in &result.curve {
            assert!(point.throughput_rps > 0.0, "throughput should be positive");
        }
    }

    #[tokio::test]
    async fn plateau_is_within_ladder() {
        let cfg = echo_parallel_cfg();
        let result = run(&cfg).await.unwrap();
        let concurrencies: Vec<usize> = result.curve.iter().map(|p| p.concurrency).collect();
        assert!(
            concurrencies.contains(&result.plateau_concurrency),
            "plateau_concurrency {} not in ladder {:?}",
            result.plateau_concurrency,
            concurrencies
        );
    }

    #[test]
    fn find_plateau_single_point() {
        let curve = vec![ScaleCurvePoint {
            concurrency: 1,
            throughput_rps: 10.0,
            mean_run_ms: 100.0,
        }];
        let (pm, prps, dm) = find_plateau_and_degradation(&curve);
        assert_eq!(pm, 1);
        assert!((prps - 10.0).abs() < 0.01);
        assert_eq!(dm, 1);
    }

    #[test]
    fn find_plateau_detects_degradation() {
        let curve = vec![
            ScaleCurvePoint {
                concurrency: 1,
                throughput_rps: 10.0,
                mean_run_ms: 100.0,
            },
            ScaleCurvePoint {
                concurrency: 4,
                throughput_rps: 35.0,
                mean_run_ms: 110.0,
            },
            ScaleCurvePoint {
                concurrency: 8,
                throughput_rps: 38.0,
                mean_run_ms: 210.0,
            },
            ScaleCurvePoint {
                concurrency: 16,
                throughput_rps: 30.0,
                mean_run_ms: 530.0,
            },
        ];
        let (pm, _prps, dm) = find_plateau_and_degradation(&curve);
        // Plateau at M=8 (last gain > 5%), degradation at M=16.
        assert!(pm <= 8, "plateau_m={pm}");
        assert_eq!(dm, 16);
    }
}
