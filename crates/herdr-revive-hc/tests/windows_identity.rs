// SPDX-FileCopyrightText: 2026 Phenotype (fork addition)
// SPDX-License-Identifier: Apache-2.0

// Phenotype fork (0.3.1-hc.1): native Windows has no restore implementation yet,
// so on Windows we assert the one thing that must still be exact there: jcode and
// kcode are recognised as resumable agents and their resume argv is
// `<executable> --resume <id>` (a flag, not a `resume` subcommand).
#![cfg(windows)]

use herdr_revive::model::{AgentKind, AgentSessionMode, CommandSpec, Config, agent_launcher};

#[test]
fn windows_recognises_jcode_and_kcode_session_identity() {
    let id = "01234567-89ab-cdef-0123-456789abcdef";
    for (agent, executable) in [(AgentKind::Jcode, "jcode"), (AgentKind::Kcode, "kcode")] {
        assert_eq!(AgentKind::from_name(executable), Some(agent));
        assert_eq!(agent.name(), executable);
        assert_eq!(agent.executable(), executable);
        assert_eq!(agent_launcher(&[executable.to_string()]), Some(agent));

        let command = CommandSpec::Agent {
            executable: executable.into(),
            agent,
            session_id: id.into(),
            session_mode: AgentSessionMode::Resume,
            claude_config_dir: None,
            claude_home: None,
            null_stdio: [false; 3],
        };
        assert_eq!(command.argv().unwrap(), [executable, "--resume", id]);
    }
    assert!(AgentKind::from_name("jcode-dev").is_none());

    let mut cfg = Config::default();
    cfg.agent_extra_args
        .insert("jcode".into(), vec!["--model".into(), "m".into()]);
    cfg.agent_extra_args
        .insert("kcode".into(), vec!["--model".into(), "m".into()]);
    cfg.validate().unwrap();
}
