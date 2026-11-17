//! Minimal CLI surface for the AgilePlus scorecard engine.
//!
//! Two subcommands are exposed today:
//!
//! - `validate <FILE>` — read a scorecard JSON file and run validation.
//! - `score    <FILE>` — read a scorecard JSON file and print the
//!   average, grade, and at-target count.
//!
//! These are the entry points the parent `helioslite` binary invokes when
//! a user runs `helioslite agileplus <subcommand>`.

use std::path::PathBuf;

use clap::{Parser, Subcommand};
use thiserror::Error;

use crate::pillar::Pillar;
use crate::scorecard::{AgilePlusError, Grade, PillarScorecard};

/// Errors returned from CLI subcommands.
#[derive(Debug, Error)]
pub enum CliError {
    /// I/O error reading the supplied file.
    #[error("io error reading {path}: {source}")]
    Io {
        /// Path that failed to read.
        path: PathBuf,
        /// Underlying IO error.
        #[source]
        source: std::io::Error,
    },
    /// Scorecard-specific error.
    #[error("agileplus error: {0}")]
    AgilePlus(#[from] AgilePlusError),
}

/// Top-level AgilePlus CLI.
#[derive(Parser, Debug)]
#[command(
    name = "agileplus",
    about = "AgilePlus scorecard & velocity engine",
    version
)]
pub struct Cli {
    /// Subcommand to run.
    #[command(subcommand)]
    pub command: Command,
}

/// AgilePlus subcommands.
#[derive(Subcommand, Debug, Clone)]
pub enum Command {
    /// Read a scorecard JSON file and run validation.
    Validate {
        /// Path to the scorecard JSON file.
        path: PathBuf,
    },
    /// Read a scorecard JSON file and print average / grade / at-target.
    Score {
        /// Path to the scorecard JSON file.
        path: PathBuf,
        /// Emit a single-line machine-readable summary (key=value lines).
        #[arg(long, default_value_t = false)]
        porcelain: bool,
    },
    /// List the 31 pillars tracked by the scorecard.
    Pillars,
}

impl Cli {
    /// Run the CLI. Returns the human-readable output.
    pub fn run(&self) -> Result<String, CliError> {
        Self::run_command(&self.command)
    }

    /// Run a single subcommand by reference. Used by the parent
    /// `helioslite` binary so it can dispatch without rebuilding the
    /// [`Cli`] wrapper.
    pub fn run_command(cmd: &Command) -> Result<String, CliError> {
        match cmd {
            Command::Validate { path } => Ok(validate_cmd(path)?),
            Command::Score { path, porcelain } => Ok(score_cmd(path, *porcelain)?),
            Command::Pillars => Ok(pillars_cmd()),
        }
    }
}

fn read_scorecard(path: &PathBuf) -> Result<PillarScorecard, CliError> {
    let body = std::fs::read_to_string(path)
        .map_err(|source| CliError::Io { path: path.clone(), source })?;
    Ok(PillarScorecard::from_json(&body)?)
}

fn validate_cmd(path: &PathBuf) -> Result<String, CliError> {
    let card = read_scorecard(path)?;
    match card.validate() {
        Ok(()) => Ok(format!(
            "OK: {path:?} validates as a 31-pillar AgilePlus scorecard.",
            path = path
        )),
        Err(err) => Ok(format!("INVALID: {path:?}: {err}")),
    }
}

fn score_cmd(path: &PathBuf, porcelain: bool) -> Result<String, CliError> {
    let card = read_scorecard(path)?;
    card.validate()?;
    let avg = card.average().unwrap_or(0.0);
    let grade = card.grade().unwrap_or(Grade::F);
    let at_target = card.at_target();
    if porcelain {
        Ok(format!(
            "average={:.2}\ngrade={}\nat_target={at_target}\npillars_total={}\n",
            avg,
            grade.letter(),
            card.scores.len(),
        ))
    } else {
        Ok(format!(
            "Scorecard {path:?}\n  average: {avg:.2} / 10\n  grade:    {}\n  at target (>= {target:.1}): {at_target} / {total}\n",
            grade.letter(),
            path = path,
            target = Pillar::TARGET_THRESHOLD,
            total = Pillar::COUNT,
        ))
    }
}

fn pillars_cmd() -> String {
    let mut out = String::new();
    out.push_str("Pillar # | Name\n");
    out.push_str("---------|------\n");
    for pillar in Pillar::all() {
        out.push_str(&format!(
            "{:>8} | {}\n",
            pillar.ordinal(),
            pillar.display_name()
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pillar::Score;

    fn write_card(dir: &std::path::Path, name: &str, body: &str) -> PathBuf {
        let p = dir.join(name);
        std::fs::write(&p, body).expect("write");
        p
    }

    fn full_scorecard_json() -> String {
        let mut s = PillarScorecard::new();
        for pillar in Pillar::all() {
            s.set(pillar, Score::new(7.0).unwrap());
        }
        s.to_json().unwrap()
    }

    #[test]
    fn clap_help_text_is_non_empty() {
        // Use clap's `command()` API to render help.
        use clap::CommandFactory;
        let mut cmd = Cli::command();
        let help = cmd.render_help().to_string();
        assert!(help.contains("agileplus"));
        assert!(help.contains("validate"));
        assert!(help.contains("score"));
        assert!(help.contains("pillars"));
    }

    #[test]
    fn validate_command_passes_a_complete_scorecard() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = write_card(tmp.path(), "card.json", &full_scorecard_json());
        let out = validate_cmd(&path).expect("validate");
        assert!(out.starts_with("OK:"));
    }

    #[test]
    fn validate_command_reports_incomplete_scorecard() {
        let tmp = tempfile::tempdir().expect("tempdir");
        // Only one pillar present.
        let body = r#"{
            "scores": {
                "Testing": 7.0
            }
        }"#;
        let path = write_card(tmp.path(), "card.json", body);
        let out = validate_cmd(&path).expect("validate");
        assert!(out.starts_with("INVALID:"));
    }

    #[test]
    fn score_command_prints_average_grade_at_target() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = write_card(tmp.path(), "card.json", &full_scorecard_json());
        let out = score_cmd(&path, false).expect("score");
        assert!(out.contains("average: 7.00 / 10"));
        assert!(out.contains("grade:    B"));
        assert!(out.contains("at target"));
    }

    #[test]
    fn score_command_porcelain_is_key_value_lines() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let path = write_card(tmp.path(), "card.json", &full_scorecard_json());
        let out = score_cmd(&path, true).expect("score");
        assert!(out.contains("average=7.00"));
        assert!(out.contains("grade=B"));
        assert!(out.contains("at_target=0"));
        assert!(out.contains("pillars_total=31"));
    }

    #[test]
    fn score_command_propagates_io_error() {
        let p = PathBuf::from("does-not-exist.json");
        let err = score_cmd(&p, false).unwrap_err();
        assert!(matches!(err, CliError::Io { .. }));
    }

    #[test]
    fn pillars_command_lists_31_entries() {
        let body = pillars_cmd();
        for pillar in Pillar::all() {
            assert!(body.contains(pillar.display_name()));
        }
    }

    #[test]
    fn parse_validate_subcommand() {
        let cli = Cli::try_parse_from(["agileplus", "validate", "card.json"]).expect("parse");
        match cli.command {
            Command::Validate { path } => assert_eq!(path, PathBuf::from("card.json")),
            _ => panic!("expected Validate"),
        }
    }

    #[test]
    fn parse_score_subcommand_with_porcelain() {
        let cli =
            Cli::try_parse_from(["agileplus", "score", "card.json", "--porcelain"]).expect("parse");
        match cli.command {
            Command::Score { path, porcelain } => {
                assert_eq!(path, PathBuf::from("card.json"));
                assert!(porcelain);
            }
            _ => panic!("expected Score"),
        }
    }
}
