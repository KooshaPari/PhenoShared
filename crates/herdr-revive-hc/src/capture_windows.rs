// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

//! Capture on native Windows.
//!
//! Herdr Core on Windows reports a pane's foreground job as concrete process
//! records (`panes.process_info`: pid, name, argv, cmdline, cwd) instead of a
//! readable process table. Those records are the whole of the identity
//! evidence, so this capture derives every command from them and refuses to
//! guess where they are silent:
//!
//! * argv missing or empty: the pane is saved with no command, because a
//!   `cmdline` string cannot be re-split into argv without guessing quoting.
//! * an agent whose exact resume ID is neither reported by Herdr nor present in
//!   its own argv: saved with no command, never as a fresh session.
//! * an agent reported for a pane whose launcher is not an agent launcher:
//!   refused, exactly as on Unix.
//!
//! What Windows capture does not have, and therefore does not claim: stdio
//! redirection detection (there are no `null_stdio` promises), the
//! permission-denied fallback to a typed command line, and layout capture.

use crate::command::command_for;
use crate::model::*;
use crate::transport::Host;
use anyhow::{Context, Result, ensure};

/// Capture the live session. Warnings name every pane saved without a command
/// and why, so a resume is never silently weakened.
pub fn capture(
    host: &mut impl Host,
    session: &str,
    workspace: Option<&str>,
    _config: &Config,
) -> Result<Snapshot> {
    let live = host.snapshot()?;
    crate::planner::index_live(&live)?;
    if let Some(id) = workspace {
        ensure!(
            live.workspaces.iter().any(|w| w.workspace_id == id),
            "named workspace is not present"
        );
    }
    let mut panes = Vec::new();
    for pane in live
        .panes
        .iter()
        .filter(|p| workspace.is_none_or(|id| id == p.workspace_id))
    {
        panes.push(saved_pane(host, pane)?);
    }
    panes.sort_by(|a, b| a.pane_id.cmp(&b.pane_id));
    let snapshot = Snapshot {
        tool: TOOL.into(),
        schema: SCHEMA,
        session: session.into(),
        created_ms: crate::store::now_ms()?,
        scope: workspace.map_or(Scope::Session, |id| Scope::Space {
            workspace_id: id.into(),
        }),
        panes,
        // Layout capture needs terminal geometry that the Windows pane API
        // does not expose; restoring without it keeps every pane's command.
        layout: Vec::new(),
        focused_workspace_id: live.focused_workspace_id,
    };
    snapshot.validate()?;
    Ok(snapshot)
}

fn saved_pane(host: &mut impl Host, pane: &LivePane) -> Result<SavedPane> {
    let info = host.process_info(&pane.pane_id)?;
    let shell = info.shell_pid.context("capture requires shell PID")?;
    let foreground = select_foreground(&info, shell);
    let resumable = pane.agent.as_deref().and_then(AgentKind::from_name);
    let mut cwd = pane.cwd.clone();

    let command = match foreground.map(|process| (process, foreground_argv(&info.pane_id, process))) {
        None => None,
        Some((_process, None)) => None,
        Some((process, Some(argv))) => {
            cwd = process.cwd.clone().or(cwd);
            command_for(&argv, reported_session(pane, &argv)?)?
        }
    };

    // An agent pane without a command would otherwise restore as a fresh
    // session, which is never the same session: say so per pane.
    if command.is_none()
        && let Some(agent) = resumable
    {
        eprintln!(
            "herdr-revive: warning: pane {}: {} has no exact resume ID; saved without a command",
            pane.pane_id,
            agent.name()
        );
    }

    Ok(SavedPane {
        workspace_id: pane.workspace_id.clone(),
        tab_id: pane.tab_id.clone(),
        pane_id: pane.pane_id.clone(),
        cwd: cwd.context("pane cwd unavailable")?,
        command,
    })
}

/// Whether the pane runs nothing but its own shell, so a command may be typed
/// into it without clobbering a foreground program. Restore re-reads this right
/// before it sends anything.
pub fn idle_shell(host: &mut impl Host, pane_id: &str) -> Result<bool> {
    let info = host.process_info(pane_id)?;
    let Some(shell) = info.shell_pid else {
        return Ok(false);
    };
    Ok(select_foreground(&info, shell).is_none())
}

/// The pane's foreground program: the reported job entry that is not the pane's
/// own shell. Herdr reports one record for a single foreground program and one
/// topmost record for an agent chain, so more than one non-shell record means
/// the group leader is the one to reproduce.
fn select_foreground<'a>(info: &'a ProcessInfo, shell: u32) -> Option<&'a ForegroundProcess> {
    let mut candidates = info.foreground_processes.iter().filter(|p| p.pid != shell);
    let first = candidates.next()?;
    Some(match info.foreground_process_group_id {
        Some(group) => info
            .foreground_processes
            .iter()
            .find(|p| p.pid == group)
            .unwrap_or(first),
        None => first,
    })
}

fn foreground_argv(pane: &str, process: &ForegroundProcess) -> Option<Vec<String>> {
    let Some(argv) = process.argv.clone().filter(|argv| !argv.is_empty()) else {
        unidentifiable(
            pane,
            "Herdr reported no argv for the foreground program, and a cmdline string cannot be re-split exactly",
        );
        return None;
    };
    match validate_argv(&argv) {
        Ok(()) => Some(argv),
        Err(error) => {
            unidentifiable(pane, &format!("the reported argv is not usable ({error:#})"));
            None
        }
    }
}

/// The agent session Herdr itself reports for this pane, when it belongs to the
/// agent that argv runs. A session reported for a different agent would resume
/// the wrong conversation, so it is dropped with a warning instead.
fn reported_session<'a>(
    pane: &'a LivePane,
    argv: &[String],
) -> Result<Option<&'a AgentSession>> {
    let Some(session) = pane.agent_session.as_ref() else {
        return Ok(None);
    };
    let running = agent_launcher(argv).map(|agent| agent.name().to_string());
    if running.as_deref() != Some(session.agent.as_str()) {
        eprintln!(
            "herdr-revive: warning: pane {}: Herdr reports a {} session but the foreground program is {}; ignoring it",
            pane.pane_id,
            session.agent,
            running.as_deref().unwrap_or("not an agent")
        );
        return Ok(None);
    }
    Ok(Some(session))
}

fn unidentifiable(pane: &str, why: &str) {
    eprintln!("herdr-revive: warning: pane {pane}: {why}; saved without a command");
}

#[cfg(test)]
mod tests {
    use super::*;

    fn process(pid: u32, argv: Option<&[&str]>) -> ForegroundProcess {
        ForegroundProcess {
            pid,
            argv: argv.map(|argv| argv.iter().map(|s| s.to_string()).collect()),
            ..ForegroundProcess::default()
        }
    }

    fn info(processes: Vec<ForegroundProcess>, group: Option<u32>) -> ProcessInfo {
        ProcessInfo {
            pane_id: "w1:p1".into(),
            shell_pid: Some(1),
            foreground_process_group_id: group,
            foreground_processes: processes,
        }
    }

    #[test]
    fn an_idle_shell_has_no_foreground_program() {
        let info = info(vec![process(1, Some(&["pwsh.exe"]))], Some(1));
        assert!(select_foreground(&info, 1).is_none());
    }

    #[test]
    fn a_single_foreground_program_is_the_job() {
        let info = info(
            vec![process(1, Some(&["pwsh.exe"])), process(42, Some(&["rg"]))],
            Some(42),
        );
        assert_eq!(select_foreground(&info, 1).map(|p| p.pid), Some(42));
    }

    #[test]
    fn the_group_leader_wins_when_several_are_reported() {
        let info = info(
            vec![
                process(1, Some(&["pwsh.exe"])),
                process(42, Some(&["jcode"])),
                process(43, Some(&["node"])),
            ],
            Some(42),
        );
        assert_eq!(select_foreground(&info, 1).map(|p| p.pid), Some(42));
    }

    #[test]
    fn argv_is_required_for_an_exact_command() {
        let without_argv = process(42, None);
        assert!(foreground_argv("w1:p1", &without_argv).is_none());
        let with_argv = process(42, Some(&["rg", "needle", "."]));
        assert_eq!(
            foreground_argv("w1:p1", &with_argv).expect("argv"),
            vec!["rg".to_string(), "needle".to_string(), ".".to_string()]
        );
    }
}
