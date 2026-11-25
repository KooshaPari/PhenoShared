//! Stream channel configuration for the `pt upgrade` subsystem.
//!
//! Each release stream (introduced by WP-25) can be tracked on one of three
//! release channels:
//!
//! - `stable`   — only releases with at least 1 week of soak time on `beta`
//! - `beta`     — releases with at least 24h of soak time on `nightly`
//! - `nightly`  — every release immediately upon tag
//!
//! Channels are tracked per-stream so each release group can have its own
//! promotion cadence. Configuration is loaded from
//! `$PHENOTYPE_HOME/channels.toml` (default `~/.config/phenotype/channels.toml`).

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// Channel a release can be promoted through.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Channel {
    /// Releases with >= 1 week soak on beta.
    #[default]
    Stable,
    /// Releases with >= 24h soak on nightly.
    Beta,
    /// Every release immediately on tag.
    Nightly,
}

impl Channel {
    /// Returns the minimum soak time in hours before this channel is eligible
    /// for promotion to the next channel up.
    pub fn min_soak_hours(&self) -> u64 {
        match self {
            Channel::Nightly => 0,
            Channel::Beta => 24,
            Channel::Stable => 24 * 7,
        }
    }

    /// Returns the rank (0 = highest = stable, 2 = lowest = nightly).
    pub fn rank(&self) -> u8 {
        match self {
            Channel::Stable => 0,
            Channel::Beta => 1,
            Channel::Nightly => 2,
        }
    }

    /// Returns true if `self` is more restrictive (higher rank) than `other`.
    pub fn is_stricter_than(&self, other: Channel) -> bool {
        self.rank() < other.rank()
    }
}

/// CLI args for the `pt upgrade` subcommand (WP-28).
#[derive(Debug, Clone, clap::Args)]
pub struct UpgradeArgs {
    /// Release channel to track (stable, beta, nightly).
    #[arg(short, long, default_value = "stable")]
    pub channel: Channel,

    /// Optional version specifier (e.g. "0.2.0" or "latest").
    #[arg(short, long)]
    pub version: Option<String>,

    /// Force the upgrade even if the current version is up to date.
    #[arg(long)]
    pub force: bool,

    /// Dry run — show what would be upgraded without applying.
    #[arg(long)]
    pub dry_run: bool,
}

/// Execute the `pt upgrade` subcommand.
///
/// Currently a stub that validates the channel and prints the target.
/// Full implementation (WP-28) will download, verify, and install the
/// release tarball for the specified stream.
#[must_use]
pub fn run(args: UpgradeArgs, verbosity: u8) -> i32 {
    if verbosity > 0 {
        eprintln!("upgrade: channel={}, force={}, dry_run={}",
            args.channel, args.force, args.dry_run);
    }
    let version = args.version.as_deref().unwrap_or("latest");
    println!("upgrade: {} channel -> {} (not yet implemented)", version, args.channel);
    super::exit_code::OK
}

impl std::fmt::Display for Channel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Channel::Stable => write!(f, "stable"),
            Channel::Beta => write!(f, "beta"),
            Channel::Nightly => write!(f, "nightly"),
        }
    }
}

impl std::str::FromStr for Channel {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "stable" => Ok(Channel::Stable),
            "beta" => Ok(Channel::Beta),
            "nightly" => Ok(Channel::Nightly),
            other => Err(format!("invalid channel '{other}' (expected stable|beta|nightly)")),
        }
    }
}

/// Per-stream channel subscription.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct StreamSubscription {
    /// Stream name (e.g. `core-stream`, `cli-stream`, `ops-stream`).
    pub stream: String,
    /// Current channel the user is tracking.
    pub channel: Channel,
    /// Last version pinned on the current channel.
    pub pinned_version: String,
    /// Unix timestamp of the last successful upgrade check.
    pub last_checked_at: u64,
}

/// Top-level channels config file.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ChannelsConfig {
    /// Map of stream name -> subscription.
    pub subscriptions: BTreeMap<String, StreamSubscription>,
    /// Default channel for new streams not yet subscribed.
    #[serde(default = "default_channel")]
    pub default_channel: Channel,
}

fn default_channel() -> Channel {
    Channel::Stable
}

impl ChannelsConfig {
    /// Returns the default config path: `$PHENOTYPE_HOME/channels.toml` or
    /// `~/.config/phenotype/channels.toml` if the env var is unset.
    pub fn default_path() -> PathBuf {
        if let Ok(p) = std::env::var("PHENOTYPE_HOME") {
            PathBuf::from(p).join("channels.toml")
        } else {
            let home = std::env::var("USERPROFILE")
                .or_else(|_| std::env::var("HOME"))
                .unwrap_or_else(|_| ".".to_string());
            PathBuf::from(home).join(".config").join("phenotype").join("channels.toml")
        }
    }

    /// Loads the config from `path`. Returns a default config if the file
    /// doesn't exist yet.
    pub fn load_or_default(path: &Path) -> std::io::Result<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        let raw = std::fs::read_to_string(path)?;
        toml::from_str(&raw)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Saves the config to `path`. Creates parent directories as needed.
    pub fn save(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let raw = toml::to_string_pretty(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(path, raw)
    }

    /// Returns the subscription for `stream`, or inserts a default one
    /// using `default_channel` + version `0.0.0` if absent.
    pub fn get_or_default_mut(&mut self, stream: &str) -> &mut StreamSubscription {
        self.subscriptions.entry(stream.to_string()).or_insert_with(|| StreamSubscription {
            stream: stream.to_string(),
            channel: self.default_channel,
            pinned_version: "0.0.0".to_string(),
            last_checked_at: 0,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn channel_soak_hours_match_phase6_plan() {
        assert_eq!(Channel::Nightly.min_soak_hours(), 0);
        assert_eq!(Channel::Beta.min_soak_hours(), 24);
        assert_eq!(Channel::Stable.min_soak_hours(), 24 * 7);
    }

    #[test]
    fn channel_rank_ordering() {
        assert!(Channel::Stable.rank() < Channel::Beta.rank());
        assert!(Channel::Beta.rank() < Channel::Nightly.rank());
        assert!(Channel::Stable.is_stricter_than(Channel::Nightly));
    }

    #[test]
    fn channel_from_str_round_trip() {
        for c in [Channel::Stable, Channel::Beta, Channel::Nightly] {
            let s = c.to_string();
            let parsed: Channel = s.parse().expect("round-trip");
            assert_eq!(parsed, c);
        }
    }

    #[test]
    fn default_config_round_trip() {
        let cfg = ChannelsConfig::default();
        let raw = toml::to_string(&cfg).expect("serialize");
        let parsed: ChannelsConfig = toml::from_str(&raw).expect("deserialize");
        assert_eq!(parsed, cfg);
    }

    #[test]
    fn get_or_default_inserts_default() {
        let mut cfg = ChannelsConfig::default();
        let sub = cfg.get_or_default_mut("cli-stream");
        assert_eq!(sub.stream, "cli-stream");
        assert_eq!(sub.channel, Channel::Stable);
        assert_eq!(sub.pinned_version, "0.0.0");
    }
}