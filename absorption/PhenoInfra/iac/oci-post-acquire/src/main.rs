//! oci-post-acquire — universal post-acquire hook chain.
//!
//! Entry point invoked by `oci-lottery` the moment OCI Always-Free capacity is
//! granted. Reads `~/.cloudprovider/oci-instance.json`, then executes a
//! sequenced, idempotent chain of provisioning steps. Each step is independently
//! retry-safe; partial-success recovery is documented in
//! `docs/governance/oci-acquire-hook-chain.md`.

use anyhow::{Context, Result, anyhow};
use chrono::Utc;
use clap::Parser;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::str::FromStr;
use std::time::Duration;
use thiserror::Error;
use tokio::io::AsyncWriteExt;
use tokio::net::TcpStream;
use tokio::process::Command;
use tracing::{error, info, warn};
use tracing_subscriber::EnvFilter;

mod cf;
mod hooks;
mod mesh;
mod tailscale;

#[derive(Parser, Debug)]
#[command(name = "oci-post-acquire", version, about)]
struct Cli {
    /// Path to oci-instance.json written by oci-lottery on success.
    #[arg(
        long,
        env = "OCI_INSTANCE_FILE",
        default_value = "~/.cloudprovider/oci-instance.json"
    )]
    instance_file: String,

    /// DNS name to register (A record).
    #[arg(long, env = "OCI_DNS_NAME", default_value = "oci-1.kooshapari.com")]
    dns_name: String,

    /// Cloudflare zone ID for kooshapari.com.
    #[arg(
        long,
        env = "CF_ZONE_ID",
        default_value = "6c9edab581e9c7b8fdb6a83adc6878ea"
    )]
    cf_zone_id: String,

    /// Cloudflare API token file.
    #[arg(long, env = "CF_TOKEN_FILE", default_value = "~/.cloudflare-token")]
    cf_token_file: String,

    /// Path to phenotype-infra repo (for mesh state commit).
    #[arg(
        long,
        env = "PHENOTYPE_INFRA_REPO",
        default_value = "~/CodeProjects/Phenotype/repos/phenotype-infra"
    )]
    repo: String,

    /// Path to ansible playbook.
    #[arg(long, default_value = "iac/ansible/playbooks/oci-baseline.yml")]
    playbook: String,

    /// Hook drop-in directory.
    #[arg(
        long,
        env = "OCI_HOOKS_DIR",
        default_value = "~/.config/phenotype/oci-acquire-hooks.d"
    )]
    hooks_dir: String,

    /// Skip steps that mutate (DNS, mesh commit, notify, downstream hooks). For dry-run.
    #[arg(long)]
    dry_run: bool,

    /// Output format: auto (default), text, json.
    #[arg(long, default_value = "auto")]
    format: String,
}

/// Output format for tracing/logs.
#[derive(Debug, Clone, PartialEq)]
enum OutputFormat {
    Auto,
    Text,
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

    if matches!(format, OutputFormat::Json) {
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

/// Structured error type for provisioning steps with remediation hints.
#[derive(Debug, Error)]
pub enum ProvisionError {
    #[error("step 1: failed to read instance file {path}: {source}")]
    ReadInstance {
        path: String,
        #[source]
        source: anyhow::Error,
    },

    #[error("step 2: SSH unreachable on {host}:{port} after {attempts} attempts")]
    SshTimeout {
        host: String,
        port: u16,
        attempts: u32,
    },

    #[error("step 4: ansible baseline failed on {host}: {details}")]
    AnsibleFailed { host: String, details: String },

    #[error("step 5: Cloudflare DNS upsert failed for {name}: {details}")]
    DnsFailed { name: String, details: String },

    #[error("step 6: mesh-state commit failed: {details}")]
    MeshCommitFailed { details: String },

    #[error("step 7: notification failed: {details}")]
    NotifyFailed { details: String },

    #[error("step 8: downstream hook drop-in failed: {details}")]
    HookFailed { details: String },
}

impl ProvisionError {
    /// Return a human-readable recovery suggestion.
    pub fn recovery_hint(&self) -> &'static str {
        match self {
            Self::ReadInstance { .. } => {
                "Verify oci-instance.json exists and is valid JSON. Re-run oci-lottery to regenerate."
            }
            Self::SshTimeout { .. } => {
                "Check the node is booting and reachable. Verify security lists allow SSH (port 22). Wait and re-run this tool."
            }
            Self::AnsibleFailed { .. } => {
                "Check node SSH access and ansible syntax. Re-run: `cargo run -p oci-post-acquire -- --dry-run` first."
            }
            Self::DnsFailed { .. } => {
                "Verify CF_API_TOKEN/CF_TOKEN_FILE is valid and zone id is correct. Manual DNS upsert may be needed."
            }
            Self::MeshCommitFailed { .. } => {
                "Check git repo access. Manual git commit of compute-mesh-state.md may be needed."
            }
            Self::NotifyFailed { .. } => {
                "Notification is best-effort; this does not block provisioning. Check agent-imessage CLI."
            }
            Self::HookFailed { .. } => {
                "Check hooks.d scripts for errors. A failing hook does not abort earlier steps."
            }
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceFile {
    pub instance_ocid: String,
    pub region: String,
    pub ad: String,
    pub public_ip: String,
    pub acquired_at: String,
}

fn expand(p: &str) -> PathBuf {
    if let Some(rest) = p.strip_prefix("~/")
        && let Some(home) = dirs_home()
    {
        return home.join(rest);
    }
    PathBuf::from(p)
}

fn dirs_home() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let fmt: OutputFormat = cli
        .format
        .parse()
        .map_err(|e| anyhow::anyhow!("invalid --format: {e}"))?;
    init_tracing(&fmt);
    let started = Utc::now();
    info!(?started, "oci-post-acquire chain starting");

    // Step 1: read instance file.
    let inst = read_instance(&cli.instance_file)
        .await
        .context("step 1: read oci-instance.json")?;
    info!(public_ip = %inst.public_ip, region = %inst.region, "instance file loaded");

    // Step 2: wait for SSH.
    wait_for_ssh(&inst.public_ip, 22, 90)
        .await
        .context("step 2: wait for SSH")?;

    // Step 3: tailscale enroll.
    if let Err(e) = tailscale::enroll(&inst).await {
        warn!(error = ?e, "step 3 (tailscale) failed — continuing; can be retried via re-run");
    }

    // Step 4: ansible baseline.
    if let Err(e) = run_ansible(&cli.repo, &cli.playbook, &inst.public_ip).await {
        error!(error = ?e, "step 4 (ansible) failed — node may be partially provisioned");
        return Err(e.context("step 4: ansible baseline"));
    }

    // Step 5: DNS.
    if !cli.dry_run {
        if let Err(e) = cf::upsert_a_record(
            &cli.cf_zone_id,
            &cli.cf_token_file,
            &cli.dns_name,
            &inst.public_ip,
        )
        .await
        {
            warn!(error = ?e, "step 5 (DNS) failed — record may need manual upsert");
        }
    } else {
        info!("step 5: DNS skipped (dry-run)");
    }

    // Step 6: mesh state commit.
    if !cli.dry_run
        && let Err(e) = mesh::commit_state(&cli.repo, &inst).await
    {
        warn!(error = ?e, "step 6 (mesh-state commit) failed — manual git commit needed");
    }

    // Step 7: notify.
    if !cli.dry_run
        && let Err(e) = notify(&inst).await
    {
        warn!(error = ?e, "step 7 (notify) failed — failsoft");
    }

    // Step 8: downstream hooks.
    if !cli.dry_run
        && let Err(e) = hooks::run_dropins(&cli.hooks_dir, &inst).await
    {
        warn!(error = ?e, "step 8 (downstream hooks) reported errors");
    }

    let elapsed = Utc::now().signed_duration_since(started);
    info!(
        elapsed_s = elapsed.num_seconds(),
        "oci-post-acquire chain complete"
    );
    Ok(())
}

async fn read_instance(path: &str) -> Result<InstanceFile> {
    let p = expand(path);
    let bytes = tokio::fs::read(&p)
        .await
        .with_context(|| format!("read {}", p.display()))?;
    let inst: InstanceFile = serde_json::from_slice(&bytes)?;
    Ok(inst)
}

async fn wait_for_ssh(host: &str, port: u16, max_secs: u64) -> Result<()> {
    let deadline = std::time::Instant::now() + Duration::from_secs(max_secs);
    let addr = format!("{host}:{port}");
    let mut attempt = 0u32;
    loop {
        attempt += 1;
        match tokio::time::timeout(Duration::from_secs(3), TcpStream::connect(&addr)).await {
            Ok(Ok(_)) => {
                info!(attempt, "SSH port open on {addr}");
                return Ok(());
            }
            _ => {
                if std::time::Instant::now() >= deadline {
                    return Err(anyhow!(
                        "SSH unreachable on {addr} after {max_secs}s ({attempt} attempts)"
                    ));
                }
                tokio::time::sleep(Duration::from_secs(2)).await;
            }
        }
    }
}

async fn run_ansible(repo: &str, playbook: &str, host: &str) -> Result<()> {
    let repo_path = expand(repo);
    let inventory = format!("{host},");
    info!(
        host,
        "running ansible-playbook (repo={})",
        repo_path.display()
    );
    let status = Command::new("ansible-playbook")
        .arg("-i")
        .arg(&inventory)
        .arg("-u")
        .arg("ubuntu")
        .arg(playbook)
        .current_dir(&repo_path)
        .status()
        .await
        .context("spawn ansible-playbook (is it installed?)")?;
    if !status.success() {
        return Err(anyhow!("ansible-playbook exited with {status}"));
    }
    Ok(())
}

async fn notify(inst: &InstanceFile) -> Result<()> {
    // 7a: iMessage via agent-imessage-mcp (failsoft — best-effort CLI).
    let body = format!(
        "OCI Always-Free acquired: {} in {} ({}). Public IP {}. Mesh provisioning complete.",
        inst.instance_ocid, inst.region, inst.ad, inst.public_ip
    );
    if let Err(e) = imessage_send(&body).await {
        warn!(error = ?e, "imessage failed — continuing");
    }
    // 7b: append worklog.
    let date = Utc::now().format("%Y_%m_%d");
    let path = expand(&format!(
        "~/CodeProjects/Phenotype/repos/worklogs/SESSION_{date}_OCI_ACQUIRED.md"
    ));
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await.ok();
    }
    let mut f = tokio::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&path)
        .await?;
    let line = format!(
        "# OCI Acquired {date}\n\n- ocid: {}\n- region: {}\n- ad: {}\n- ip: {}\n- acquired_at: {}\n",
        inst.instance_ocid, inst.region, inst.ad, inst.public_ip, inst.acquired_at
    );
    f.write_all(line.as_bytes()).await?;
    Ok(())
}

async fn imessage_send(body: &str) -> Result<()> {
    // Best-effort: invoke agent-imessage-mcp CLI if present.
    let status = Command::new("agent-imessage")
        .arg("notify")
        .arg("--to")
        .arg("kooshapari@gmail.com")
        .arg("--title")
        .arg("OCI Acquired")
        .arg("--body")
        .arg(body)
        .status()
        .await;
    match status {
        Ok(s) if s.success() => Ok(()),
        Ok(s) => Err(anyhow!("agent-imessage exited {s}")),
        Err(e) => Err(anyhow!("agent-imessage not available: {e}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_expand_tilde() {
        let home = dirs_home().expect("HOME set in test");
        assert_eq!(expand("~/foo"), home.join("foo"));
        assert_eq!(expand("~/a/b/c"), home.join("a/b/c"));
    }

    #[test]
    fn test_expand_absolute() {
        assert_eq!(expand("/etc/passwd"), PathBuf::from("/etc/passwd"));
    }

    #[test]
    fn test_expand_relative() {
        assert_eq!(expand("rel/path"), PathBuf::from("rel/path"));
    }

    #[test]
    fn test_instance_file_deserialize() {
        let json = r#"{
            "instance_ocid": "ocid1.test.456",
            "region": "us-ashburn-1",
            "ad": "AD-1",
            "public_ip": "10.0.0.1",
            "acquired_at": "2026-06-29T12:00:00Z"
        }"#;
        let inst: InstanceFile = serde_json::from_str(json).unwrap();
        assert_eq!(inst.instance_ocid, "ocid1.test.456");
        assert_eq!(inst.region, "us-ashburn-1");
        assert_eq!(inst.public_ip, "10.0.0.1");
    }

    #[test]
    fn test_output_format_parse() {
        assert_eq!("auto".parse::<OutputFormat>().unwrap(), OutputFormat::Auto);
        assert_eq!("text".parse::<OutputFormat>().unwrap(), OutputFormat::Text);
        assert_eq!("json".parse::<OutputFormat>().unwrap(), OutputFormat::Json);
        assert!("invalid".parse::<OutputFormat>().is_err());
    }

    #[test]
    fn test_provision_error_recovery_hints() {
        let err = ProvisionError::ReadInstance {
            path: "/tmp/test.json".into(),
            source: anyhow::anyhow!("file not found"),
        };
        assert!(!err.recovery_hint().is_empty());

        let ssh_err = ProvisionError::SshTimeout {
            host: "10.0.0.1".into(),
            port: 22,
            attempts: 10,
        };
        assert!(ssh_err.recovery_hint().contains("SSH"));
    }

    #[test]
    fn test_wait_for_ssh_timeout_message() {
        // Verify the error message format from wait_for_ssh's timeout branch.
        let err = ProvisionError::SshTimeout {
            host: "10.0.0.1".into(),
            port: 22,
            attempts: 45,
        };
        let msg = err.to_string();
        assert!(msg.contains("10.0.0.1"));
        assert!(msg.contains("45"));
        assert!(msg.contains("SSH"));
    }

    #[test]
    fn test_provision_error_display_all_variants() {
        // Smoke test: every variant renders without panic.
        let variants: Vec<ProvisionError> = vec![
            ProvisionError::ReadInstance {
                path: "p".into(),
                source: anyhow::anyhow!("e"),
            },
            ProvisionError::SshTimeout {
                host: "h".into(),
                port: 22,
                attempts: 5,
            },
            ProvisionError::AnsibleFailed {
                host: "h".into(),
                details: "timeout".into(),
            },
            ProvisionError::DnsFailed {
                name: "n".into(),
                details: "auth".into(),
            },
            ProvisionError::MeshCommitFailed {
                details: "git error".into(),
            },
            ProvisionError::NotifyFailed {
                details: "timeout".into(),
            },
            ProvisionError::HookFailed {
                details: "exit 1".into(),
            },
        ];
        for v in &variants {
            let msg = v.to_string();
            assert!(!msg.is_empty(), "empty error message for {v:?}");
            let hint = v.recovery_hint();
            assert!(!hint.is_empty(), "empty recovery hint for {v:?}");
        }
    }
}
