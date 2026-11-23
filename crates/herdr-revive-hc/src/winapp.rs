// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

//! The native Windows command surface.
//!
//! The Unix `app` owns a boot-claim journal, shell-hook install, the setup
//! planner and typed-command recovery; none of that has a Windows meaning yet,
//! so this module is a separate, smaller surface rather than a gate that hides
//! a refusal:
//!
//! | action | what it does |
//! |---|---|
//! | `save` | capture the live session and store the snapshot |
//! | `list` | list retained snapshots |
//! | `preview` | print the restore plan for the latest (or a named) snapshot |
//! | `restore` | type the planned commands into idle panes (`--dry-run` prints the plan) |
//! | `config` | print the default configuration |
//! | `status` | one JSON document: latest snapshot, plan, per-pane decision |
//!
//! Restore refuses a pane that is not running just its own shell, so a hidden
//! program is never typed over. It also refuses any argv it cannot write on one
//! shell line without changing it: nothing is resumed approximately.

use anyhow::{Context, Result, bail, ensure};
use clap::{Parser, Subcommand};
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

use crate::model::*;
use crate::transport::{Host, Transport};

#[derive(Parser)]
#[command(
    name = "herdr-revive",
    version,
    about = "Session-scoped command restoration for Herdr (native Windows)"
)]
pub struct Cli {
    #[arg(long, global = true)]
    pub config_dir: Option<PathBuf>,
    #[arg(long, global = true)]
    pub state_dir: Option<PathBuf>,
    #[arg(long, global = true)]
    pub socket: Option<PathBuf>,
    #[arg(long, global = true)]
    pub json: bool,
    #[command(subcommand)]
    pub command: Action,
}

#[derive(Subcommand)]
pub enum Action {
    /// Save the current session without running pane commands.
    Save,
    /// List retained session snapshots.
    List,
    /// Inspect restore decisions. Does not execute anything.
    Preview {
        #[arg(long, alias = "file")]
        snapshot: Option<PathBuf>,
    },
    /// Type the saved commands into panes that are running only their shell.
    Restore {
        #[arg(long, alias = "file")]
        snapshot: Option<PathBuf>,
        #[arg(long)]
        dry_run: bool,
    },
    /// Print the default TOML configuration.
    Config,
    /// One read-only JSON document: latest snapshot, plan, decisions.
    Status,
}

pub fn run(cli: Cli) -> Result<i32> {
    let config = store_config(cli.config_dir.as_deref())?;
    let (socket, session) = socket_and_session(cli.socket.as_deref())?;
    let state = state_dir(cli.state_dir.as_deref())?;
    let store = crate::store::Store::new(&state, session)?;
    match cli.command {
        Action::Config => {
            let text = toml::to_string_pretty(&Config::default())?;
            print(cli.json, json!({"config": text}))?;
            Ok(0)
        }
        Action::List => {
            let names = store.list("snapshots")?;
            print(
                cli.json,
                json!({
                    "snapshots": names
                        .iter()
                        .filter_map(|p| p.file_name().and_then(|n| n.to_str()))
                        .collect::<Vec<_>>(),
                }),
            )?;
            Ok(0)
        }
        Action::Save => {
            let mut host = Transport::new(socket.clone(), None, &config);
            let snapshot = crate::capture::capture(&mut host, &store.session, None, &config)?;
            let _lock = store
                .try_lock()?
                .context("another save or restore holds the session lock")?;
            store.save(&snapshot, None, config.retention)?;
            print(
                cli.json,
                json!({"saved": snapshot.panes.len(), "session": store.session}),
            )?;
            Ok(0)
        }
        Action::Preview { snapshot } => {
            let saved = read_snapshot(&store, snapshot.as_deref())?;
            let mut host = Transport::new(socket, None, &config);
            let live = host.snapshot()?;
            let plan = crate::planner::plan(&saved, &store.session, &live, &config)?;
            print(cli.json, plan_json(&saved, &plan))?;
            Ok(0)
        }
        Action::Status => {
            let saved = read_snapshot(&store, None).ok();
            let mut host = Transport::new(socket, None, &config);
            let live = host.snapshot()?;
            let document = match saved {
                Some(saved) => {
                    let plan = crate::planner::plan(&saved, &store.session, &live, &config)?;
                    let mut value = plan_json(&saved, &plan);
                    value["live"] = live_json(&live);
                    value
                }
                None => json!({"snapshot": Value::Null, "live": live_json(&live)}),
            };
            print(cli.json, document)?;
            Ok(0)
        }
        Action::Restore { snapshot, dry_run } => {
            let saved = read_snapshot(&store, snapshot.as_deref())?;
            let mut host = Transport::new(socket, None, &config);
            let live = host.snapshot()?;
            let plan = crate::planner::plan(&saved, &store.session, &live, &config)?;
            let mut sent = Vec::new();
            let mut refused = Vec::new();
            for entry in &plan.entries {
                if entry.decision != crate::planner::Decision::Candidate {
                    continue;
                }
                let pane = saved
                    .panes
                    .iter()
                    .find(|p| p.pane_id == entry.pane_id)
                    .context("plan references unknown pane")?;
                let Some(command) = pane.command.as_ref() else {
                    continue;
                };
                let line = match shell_line(command)? {
                    Some(line) => line,
                    None => {
                        refused.push(json!({"pane_id": entry.pane_id, "why": "argv cannot be written exactly on one shell line"}));
                        continue;
                    }
                };
                if !crate::capture::idle_shell(&mut host, &entry.pane_id)? {
                    refused.push(json!({"pane_id": entry.pane_id, "why": "pane is running a program"}));
                    continue;
                }
                if !dry_run {
                    host.run(&entry.pane_id, &line)?;
                }
                sent.push(json!({"pane_id": entry.pane_id, "command": line}));
            }
            let mut document = plan_json(&saved, &plan);
            document["dry_run"] = json!(dry_run);
            document["sent"] = json!(sent);
            document["refused"] = json!(refused);
            print(cli.json, document)?;
            Ok(0)
        }
    }
}

fn plan_json(saved: &Snapshot, plan: &crate::planner::Plan) -> Value {
    json!({
        "session": saved.session,
        "created_ms": saved.created_ms,
        "panes": saved.panes.len(),
        "plan": plan.entries,
    })
}

fn live_json(live: &LiveSnapshot) -> Value {
    json!({
        "workspaces": live.workspaces.len(),
        "tabs": live.tabs.len(),
        "panes": live.panes.len(),
        "focused_workspace_id": live.focused_workspace_id,
    })
}

fn read_snapshot(store: &crate::store::Store, named: Option<&Path>) -> Result<Snapshot> {
    let path = match named {
        Some(path) => path.to_path_buf(),
        None => store.snapshot_path(None)?,
    };
    store.read_snapshot(&path)
}

/// The one shell line that runs `command` unchanged, or `None` when it cannot
/// be written without altering its arguments.
fn shell_line(command: &CommandSpec) -> Result<Option<String>> {
    let (argv, null_stdio) = match command {
        CommandSpec::Program { argv } => (argv.clone(), [false; 3]),
        CommandSpec::ProgramNullStdio { argv, null_stdio } => (argv.clone(), *null_stdio),
        CommandSpec::Agent { .. } => (command.argv()?, [false; 3]),
    };
    // A redirect the Unix host could promise has no exact Windows spelling in a
    // typed line, and typing it without the redirect would change the command.
    ensure!(
        null_stdio == [false; 3],
        "stream redirection cannot be reproduced on Windows"
    );
    let mut line = String::new();
    for (index, arg) in argv.iter().enumerate() {
        if index > 0 {
            line.push(' ');
        }
        match quote(arg) {
            Some(quoted) => line.push_str(&quoted),
            None => return Ok(None),
        }
    }
    Ok(Some(line))
}

/// An argument as `cmd.exe` and PowerShell both read it back unchanged, or
/// `None` when no such spelling exists.
fn quote(arg: &str) -> Option<String> {
    if arg.is_empty() {
        return Some("\"\"".into());
    }
    if arg.contains('"') || arg.contains('\n') || arg.contains('\r') {
        return None;
    }
    if arg
        .chars()
        .any(|c| c.is_whitespace() || "&|<>^()%!;,$`".contains(c))
    {
        return Some(format!("\"{arg}\""));
    }
    Some(arg.into())
}

fn store_config(explicit: Option<&Path>) -> Result<Config> {
    let dir = env_path(explicit, "HERDR_PLUGIN_CONFIG_DIR")?;
    let config = crate::store::load_config(&dir)?;
    config.validate()?;
    Ok(config)
}

fn state_dir(explicit: Option<&Path>) -> Result<PathBuf> {
    env_path(explicit, "HERDR_PLUGIN_STATE_DIR")
}

fn env_path(explicit: Option<&Path>, variable: &str) -> Result<PathBuf> {
    if let Some(path) = explicit {
        return Ok(path.to_path_buf());
    }
    match std::env::var_os(variable) {
        Some(value) => Ok(PathBuf::from(value)),
        None => bail!("--{} or {variable} is required on native Windows", slug(variable)),
    }
}

fn slug(variable: &str) -> String {
    variable.to_ascii_lowercase().replace('_', "-")
}

fn socket_and_session(explicit: Option<&Path>) -> Result<(PathBuf, String)> {
    let path = env_path(explicit, "HERDR_SOCKET_PATH")?;
    crate::store::session_identity(&path)
}

fn print(json_mode: bool, value: Value) -> Result<()> {
    if json_mode {
        println!("{}", serde_json::to_string_pretty(&value)?);
        return Ok(());
    }
    if let Some(text) = value.get("config").and_then(Value::as_str) {
        print!("{text}");
        return Ok(());
    }
    println!("{}", serde_json::to_string_pretty(&value)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_plain_command_is_written_as_is() {
        let command = CommandSpec::Program {
            argv: vec!["rg".into(), "needle".into(), ".".into()],
        };
        assert_eq!(
            shell_line(&command).expect("line").as_deref(),
            Some("rg needle .")
        );
    }

    #[test]
    fn a_jcode_resume_is_written_exactly() {
        let command = CommandSpec::Agent {
            executable: "C:\\Users\\koosh\\.local\\bin\\jcode.exe".into(),
            agent: AgentKind::Jcode,
            session_id: "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".into(),
            session_mode: AgentSessionMode::Resume,
            claude_config_dir: None,
            claude_home: None,
            null_stdio: [false; 3],
        };
        assert_eq!(
            shell_line(&command).expect("line").as_deref(),
            Some(
                "C:\\Users\\koosh\\.local\\bin\\jcode.exe --resume 0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c"
            )
        );
    }

    #[test]
    fn an_argument_with_spaces_is_quoted() {
        let command = CommandSpec::Program {
            argv: vec!["rg".into(), "two words".into()],
        };
        assert_eq!(
            shell_line(&command).expect("line").as_deref(),
            Some("rg \"two words\"")
        );
    }

    #[test]
    fn an_argument_that_cannot_be_written_exactly_is_refused() {
        let command = CommandSpec::Program {
            argv: vec!["rg".into(), "say \"hi\"".into()],
        };
        assert!(shell_line(&command).expect("line").is_none());
    }

    #[test]
    fn stream_redirection_is_refused_rather_than_dropped() {
        let command = CommandSpec::ProgramNullStdio {
            argv: vec!["tool".into()],
            null_stdio: [false, true, false],
        };
        assert!(shell_line(&command).is_err());
    }
}
