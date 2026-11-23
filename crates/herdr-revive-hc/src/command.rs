// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

//! The exact-command layer: turning a foreground program's argv, plus the
//! agent's own reported session, into the one command that resumes that very
//! session. It is pure string and model logic, so both the Unix capture path
//! and the native Windows capture path derive identity with the same rules.

use crate::model::*;
use anyhow::{Context, Result, ensure};

/// The command that reproduces `argv`, exactly.
///
/// An agent launch becomes an `Agent` command whose session is `native` when
/// the host reported one, and otherwise the ID the argv itself names, so a
/// `jcode --resume <id>` is resumed as `<id>` and not as `--continue`. Any
/// other program is saved as its argv.
pub fn command_for(argv: &[String], native: Option<&AgentSession>) -> Result<Option<CommandSpec>> {
    validate_argv(argv)?;
    let agent = agent_launcher(argv);
    if let Some(agent) = agent {
        let session_id = if let Some(native) = native {
            ensure!(
                native.source == format!("herdr:{}", agent.name())
                    && native.agent == agent.name()
                    && native.kind == "id",
                "untrusted native agent reference"
            );
            native.value.clone()
        } else {
            let start = if is_launcher(&argv[0]) { 2 } else { 1 };
            explicit_resume_id(agent, &argv[start..])?
        };
        return agent_command(argv, agent, session_id).map(Some);
    }
    // Never turn an unrelated foreground process into a stale stored agent session.
    let command = CommandSpec::Program {
        argv: argv.to_vec(),
    };
    command.argv()?;
    Ok(Some(command))
}

pub fn agent_command(argv: &[String], agent: AgentKind, session_id: String) -> Result<CommandSpec> {
    validate_session_id(&session_id)?;
    Ok(CommandSpec::Agent {
        executable: if is_launcher(&argv[0]) {
            agent.executable().into()
        } else {
            argv[0].clone()
        },
        agent,
        session_id,
        session_mode: AgentSessionMode::Resume,
        claude_config_dir: None,
        claude_home: None,
        null_stdio: [false; 3],
    })
}

/// The resume ID an agent's own arguments name, or why they name none
/// unambiguously.
pub fn explicit_resume_id(agent: AgentKind, args: &[String]) -> Result<String> {
    let mut index = 0;
    let mut found = None;
    while index < args.len() {
        let arg = &args[index];
        let is_resume = arg == "--resume" || (agent == AgentKind::Codex && arg == "resume");
        if is_resume {
            let value = args.get(index + 1).context("resume option has no ID")?;
            validate_session_id(value)?;
            ensure!(
                found.replace(value.clone()).is_none(),
                "multiple resume IDs"
            );
            index += 2;
        } else if let Some(value) = arg.strip_prefix("--resume=") {
            validate_session_id(value)?;
            ensure!(found.replace(value.into()).is_none(), "multiple resume IDs");
            index += 1;
        } else if agent_option_takes_value(agent, arg) {
            let value = args.get(index + 1).context("agent option has no value")?;
            ensure!(
                !value.starts_with('-'),
                "agent option value cannot be another option"
            );
            index += 2;
        } else if agent_boolean_option(agent, arg) {
            index += 1;
        } else {
            anyhow::bail!("unknown agent option or prompt; exact resume ID cannot be parsed");
        }
    }
    found.context("agent has no explicit exact resume ID")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Herdr Core reports the session it persisted for the pane: the source is
    /// the hook that reported it and the agent is its own name.
    fn session(kind: &str) -> AgentSession {
        AgentSession {
            source: format!("herdr:{kind}"),
            agent: kind.into(),
            kind: "id".into(),
            value: "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".into(),
        }
    }

    #[test]
    fn a_reported_jcode_session_becomes_an_exact_resume() {
        let argv = vec!["jcode".to_string()];
        let command = command_for(&argv, Some(&session("jcode")))
            .expect("command")
            .expect("some");
        assert_eq!(
            command.argv().expect("argv"),
            vec![
                "jcode".to_string(),
                "--resume".to_string(),
                "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".to_string()
            ]
        );
    }

    #[test]
    fn a_reported_kcode_session_becomes_an_exact_resume() {
        let argv = vec!["kcode".to_string()];
        let command = command_for(&argv, Some(&session("kcode")))
            .expect("command")
            .expect("some");
        assert_eq!(
            command.argv().expect("argv"),
            vec![
                "kcode".to_string(),
                "--resume".to_string(),
                "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".to_string()
            ]
        );
    }

    #[test]
    fn a_session_reported_for_another_agent_is_refused() {
        let argv = vec!["jcode".to_string()];
        let error = command_for(&argv, Some(&session("kcode"))).expect_err("refused");
        assert!(format!("{error:#}").contains("untrusted native agent reference"));
    }

    #[test]
    fn an_argv_resume_id_decides_when_the_host_reports_nothing() {
        let argv = vec![
            "jcode".to_string(),
            "--resume".to_string(),
            "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".to_string(),
        ];
        let command = command_for(&argv, None).expect("command").expect("some");
        assert_eq!(
            command.argv().expect("argv"),
            vec![
                "jcode".to_string(),
                "--resume".to_string(),
                "0f3d2c1b-4a59-4e8f-9b1c-2d3e4f5a6b7c".to_string()
            ]
        );
    }

    #[test]
    fn a_plain_program_is_kept_as_its_argv() {
        let argv = vec!["rg".to_string(), "needle".to_string(), ".".to_string()];
        let command = command_for(&argv, None).expect("command").expect("some");
        assert_eq!(command.argv().expect("argv"), argv);
    }
}
