//! `oci-lottery` — A1.Flex capacity lottery daemon.
//!
//! Loops `oci compute instance launch` across configured regions until
//! capacity is granted (or SIGTERM). On success, fires a hook chain
//! (post-acquire script, webhook, compute-mesh-state.md commit, iMessage).
//!
//! Per Phenotype scripting policy, this is the canonical Rust replacement
//! for prior shell-based "OCI rerun" loops.

mod config;
mod hooks;
mod oci;
mod state;

use anyhow::{Context, Result};
use chrono::Utc;
use clap::Parser;
use rand::prelude::*;
use std::path::PathBuf;
use std::str::FromStr;
use std::time::Duration;
#[cfg(unix)]
use tokio::signal::unix::{SignalKind, signal};
use tracing::{error, info, warn};
use tracing_subscriber::EnvFilter;

use crate::config::Config;
use crate::oci::{instance_public_ip, list_availability_domains, try_launch};
use crate::state::{AcquiredInstance, LotteryState, write_acquired};

#[derive(Debug, Parser)]
#[command(
    name = "oci-lottery",
    about = "OCI Always-Free A1.Flex capacity lottery daemon"
)]
struct Args {
    /// Path to JSON config (regions, OCIDs, shape).
    #[arg(long, env = "OCI_LOTTERY_CONFIG")]
    config: Option<PathBuf>,

    /// Override state file location.
    #[arg(long, env = "OCI_LOTTERY_STATE")]
    state_file: Option<PathBuf>,

    /// Override acquired-instance file location.
    #[arg(long, env = "OCI_LOTTERY_ACQUIRED")]
    acquired_file: Option<PathBuf>,

    /// Path to phenotype-infra repo root, for compute-mesh-state.md update.
    #[arg(long, env = "PHENOTYPE_INFRA_REPO")]
    infra_repo: Option<PathBuf>,

    /// Output format: auto (default), text, json.
    #[arg(long, default_value = "auto")]
    format: String,

    /// Single attempt and exit (test mode — no loop, no signal handler).
    #[arg(long)]
    once: bool,
}

/// Output format for tracing/logs.
#[derive(Debug, Clone, PartialEq)]
enum OutputFormat {
    /// Auto-detect: JSON if stdout is not a tty, text otherwise.
    Auto,
    /// Human-readable text.
    Text,
    /// JSON-structured log lines.
    Json,
}

impl FromStr for OutputFormat {
    type Err = String;

    fn from_str(s: &str) -> std::result::Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "auto" => Ok(Self::Auto),
            "text" => Ok(Self::Text),
            "json" => Ok(Self::Json),
            _ => Err(format!(
                "unknown format '{s}': expected auto, text, or json"
            )),
        }
    }
}

/// Initialize tracing-subscriber respecting --format and NO_COLOR.
fn init_tracing(format: &OutputFormat) {
    let no_color = std::env::var_os("NO_COLOR").is_some();
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));

    let is_json = matches!(format, OutputFormat::Json);

    if is_json {
        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_ansi(!no_color)
            .json()
            .init();
    } else {
        tracing_subscriber::fmt()
            .with_env_filter(filter)
            .with_ansi(!no_color)
            .init();
    }
}
fn home() -> PathBuf {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/tmp"))
}

#[tokio::main(flavor = "multi_thread", worker_threads = 2)]
async fn main() -> Result<()> {
    let args = Args::parse();
    let fmt: OutputFormat = args
        .format
        .parse()
        .map_err(|e| anyhow::anyhow!("invalid --format: {e}"))?;
    init_tracing(&fmt);

    let config_path = args
        .config
        .unwrap_or_else(|| home().join(".cloudprovider/oci-lottery.json"));
    let state_path = args
        .state_file
        .unwrap_or_else(|| home().join(".cloudprovider/oci-lottery-state.json"));
    let acquired_path = args
        .acquired_file
        .unwrap_or_else(|| home().join(".cloudprovider/oci-instance.json"));

    let cfg = Config::load_or_default(&config_path)
        .await
        .context("loading config")?;
    let mut st = LotteryState::load(&state_path)
        .await
        .context("loading state")?;
    if st.started_at.is_none() {
        st.started_at = Some(Utc::now());
    }
    st.save(&state_path).await.ok();

    info!(
        regions = ?cfg.regions,
        shape = %cfg.shape,
        ocpus = cfg.ocpus,
        memory_gb = cfg.memory_gb,
        config = %config_path.display(),
        state = %state_path.display(),
        "oci-lottery starting"
    );

    // SIGTERM/SIGINT handlers (Unix only; on other platforms the loop runs until capacity).
    #[cfg(unix)]
    let mut sigterm = signal(SignalKind::terminate()).context("install SIGTERM handler")?;
    #[cfg(unix)]
    let mut sigint = signal(SignalKind::interrupt()).context("install SIGINT handler")?;

    loop {
        for region in &cfg.regions {
            // Determine ADs to try.
            let ad_indices: Vec<u8> = cfg
                .availability_domains
                .clone()
                .unwrap_or_else(|| vec![1, 2, 3]);

            // Resolve AD names once per region. If lookup fails, skip region.
            let ad_names = match list_availability_domains(&cfg, region).await {
                Ok(names) if !names.is_empty() => names,
                Ok(_) => {
                    warn!(region = %region, "no availability domains returned");
                    continue;
                }
                Err(e) => {
                    warn!(region = %region, error = %e, "AD list failed; skipping region this round");
                    continue;
                }
            };

            for idx in ad_indices.iter().copied() {
                let i = (idx as usize).saturating_sub(1);
                let ad_name = match ad_names.get(i) {
                    Some(n) => n.clone(),
                    None => continue,
                };

                st.attempts += 1;
                st.last_attempt = Some(Utc::now());
                st.last_region = Some(region.clone());
                st.last_ad = Some(idx);

                let attempt_no = st.attempts;
                info!(attempt = attempt_no, region = %region, ad = %ad_name, "launch attempt");

                match try_launch(&cfg, region, &ad_name).await {
                    Ok(out) if out.success => {
                        let ocid = out.instance_ocid.unwrap_or_default();
                        info!(region = %region, ocid = %ocid, "CAPACITY ACQUIRED");
                        let public_ip =
                            instance_public_ip(&cfg, region, &ocid).await.ok().flatten();
                        let acquired = AcquiredInstance {
                            instance_ocid: ocid,
                            region: region.clone(),
                            ad: idx,
                            public_ip,
                            acquired_at: Utc::now(),
                        };
                        write_acquired(&acquired_path, &acquired).await.ok();
                        st.acquired = true;
                        st.last_error = None;
                        st.save(&state_path).await.ok();

                        hooks::fire_all(&acquired, args.infra_repo.as_ref()).await;
                        info!("hook chain complete; exiting");
                        return Ok(());
                    }
                    Ok(out) if out.out_of_capacity => {
                        st.last_error = Some("out-of-capacity".into());
                        info!(region = %region, ad = %ad_name, "out of capacity");
                    }
                    Ok(out) => {
                        let err = if !out.raw_stderr.is_empty() {
                            out.raw_stderr
                        } else {
                            out.raw_stdout
                        };
                        warn!(region = %region, ad = %ad_name, error = %err, "launch failed");
                        st.last_error = Some(err);
                    }
                    Err(e) => {
                        error!(region = %region, error = %e, "oci CLI invocation error");
                        st.last_error = Some(e.to_string());
                    }
                }
                st.save(&state_path).await.ok();

                if args.once {
                    info!("--once flag: exiting after a single attempt");
                    return Ok(());
                }

                // Backoff jitter between attempts.
                let sleep_secs = jitter(cfg.backoff_min_secs, cfg.backoff_max_secs);
                info!(secs = sleep_secs, "backoff");
                #[cfg(unix)]
                tokio::select! {
                    _ = tokio::time::sleep(Duration::from_secs(sleep_secs)) => {},
                    _ = sigterm.recv() => { info!("SIGTERM received"); return Ok(()); }
                    _ = sigint.recv()  => { info!("SIGINT received");  return Ok(()); }
                }
                #[cfg(not(unix))]
                tokio::time::sleep(Duration::from_secs(sleep_secs)).await;
            }
        }
    }
}

fn jitter(min: u64, max: u64) -> u64 {
    let (lo, hi) = if min <= max { (min, max) } else { (max, min) };
    if lo == hi {
        return lo;
    }
    rand::rng().random_range(lo..=hi)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_jitter_within_range() {
        for _ in 0..100 {
            let v = jitter(5, 10);
            assert!((5..=10).contains(&v), "jitter {v} outside [5,10]");
        }
    }

    #[test]
    fn test_jitter_min_equals_max() {
        assert_eq!(jitter(7, 7), 7);
    }

    #[test]
    fn test_jitter_swapped_order() {
        for _ in 0..100 {
            let v = jitter(20, 10);
            assert!((10..=20).contains(&v), "jitter {v} outside [10,20]");
        }
    }

    #[test]
    fn test_jitter_single_value() {
        assert_eq!(jitter(42, 42), 42);
    }

    #[test]
    fn test_output_format_parse() {
        assert_eq!("auto".parse::<OutputFormat>().unwrap(), OutputFormat::Auto);
        assert_eq!("text".parse::<OutputFormat>().unwrap(), OutputFormat::Text);
        assert_eq!("json".parse::<OutputFormat>().unwrap(), OutputFormat::Json);
        assert_eq!("JSON".parse::<OutputFormat>().unwrap(), OutputFormat::Json);
        assert!("bad".parse::<OutputFormat>().is_err());
    }

    #[test]
    fn test_home_from_env() {
        // home() returns a PathBuf — smoke test that it doesn't panic.
        let h = home();
        assert!(!h.as_os_str().is_empty());
    }

    #[test]
    fn test_config_default_shape() {
        let cfg = config::Config::default();
        assert_eq!(cfg.shape, "VM.Standard.A1.Flex");
        assert_eq!(cfg.ocpus, 4);
        assert_eq!(cfg.memory_gb, 24);
        assert!(!cfg.regions.is_empty());
    }

    #[test]
    fn test_state_serialization_roundtrip() {
        let acquired = state::AcquiredInstance {
            instance_ocid: "ocid1.test.123".into(),
            region: "us-ashburn-1".into(),
            ad: 1,
            public_ip: Some("10.0.0.1".into()),
            acquired_at: chrono::Utc::now(),
        };
        let json = serde_json::to_string_pretty(&acquired).unwrap();
        let back: state::AcquiredInstance = serde_json::from_str(&json).unwrap();
        assert_eq!(back.instance_ocid, acquired.instance_ocid);
        assert_eq!(back.region, acquired.region);
    }
}
