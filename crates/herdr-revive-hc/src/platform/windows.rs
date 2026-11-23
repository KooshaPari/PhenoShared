// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0
//
// Phenotype fork addition (0.3.1-hc.1): a native-Windows platform module.
//
// Upstream v0.3.1 declared `platforms = ["linux", "macos"]` and did not compile
// for Windows at all: `src/platform.rs` re-exported only `linux` and `macos`, so
// every `platform::process*` symbol was missing and the crate failed to build.
//
// This module makes the crate build and run on native Windows for the commands
// that do not inspect other processes (`status`, `config`, `init`, `uninstall`,
// `preview`, snapshot listing). The capture/restore path needs another process's
// argv, cwd, environment and stdio; there is no `/proc` equivalent and doing it
// needs NT APIs (NtQueryInformationProcess + ReadProcessMemory) which this fork
// does not implement. Those entry points therefore refuse with an explicit
// reason instead of silently capturing a wrong snapshot.

use super::Process;
use anyhow::{Result, bail};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

const UNSUPPORTED: &str =
    "native Windows: Herdr process introspection is not implemented in this fork, so \
     capture/restore cannot read another process's identity; use macOS or Linux for \
     save/restore, or run revive inside WSL";

pub fn process_age(_: &Process) -> Result<std::time::Duration> {
    bail!(UNSUPPORTED)
}

pub fn process(_: u32) -> Result<Process> {
    bail!(UNSUPPORTED)
}

pub fn terminal_foreground_group(_: u32) -> Result<u32> {
    bail!(UNSUPPORTED)
}

pub fn process_table() -> Result<HashMap<u32, Process>> {
    bail!(UNSUPPORTED)
}

pub fn has_children(_: &Process) -> Result<bool> {
    bail!(UNSUPPORTED)
}

pub fn protected_argv(_: &Process) -> Result<(Vec<String>, bool)> {
    bail!(UNSUPPORTED)
}

pub fn executable(_: u32) -> Result<PathBuf> {
    bail!(UNSUPPORTED)
}

pub fn argv_and_cwd(_: &Process) -> Result<(Vec<String>, String)> {
    bail!(UNSUPPORTED)
}

pub fn environment(_: &Process) -> Result<Vec<u8>> {
    bail!(UNSUPPORTED)
}

pub fn terminal_stdio(_: u32, _: u32) -> Result<[bool; 3]> {
    bail!(UNSUPPORTED)
}

pub fn ssh_terminal_stdout(_: u32) -> Result<()> {
    bail!(UNSUPPORTED)
}

pub fn git_pager_stdio(_: &HashMap<u32, Process>, _: &Process, _: u32) -> Result<()> {
    bail!(UNSUPPORTED)
}

/// herdr-core's generation is read from the client socket. Windows uses a named
/// pipe, not a unix socket, so there is nothing to connect to here.
pub fn generation(_: &Path) -> Result<String> {
    bail!("native Windows: herdr-core socket generation is not readable (named pipe, not a unix socket)")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Every entry point must fail *with the fork's explanation*, not with a
    /// panic and not with a silent success.
    #[test]
    fn process_introspection_refuses_with_a_reason() {
        let process = Process {
            pid: 4,
            parent: 0,
            group: 4,
            start: 0,
        };
        for error in [
            process_age(&process).unwrap_err(),
            super::process(4).unwrap_err(),
            terminal_foreground_group(4).unwrap_err(),
            process_table().unwrap_err(),
            has_children(&process).unwrap_err(),
            protected_argv(&process).unwrap_err(),
            executable(4).unwrap_err(),
            argv_and_cwd(&process).unwrap_err(),
            environment(&process).unwrap_err(),
            terminal_stdio(4, 4).unwrap_err(),
            ssh_terminal_stdout(4).unwrap_err(),
            git_pager_stdio(&HashMap::new(), &process, 4).unwrap_err(),
            generation(Path::new("ignored")).unwrap_err(),
        ] {
            assert!(
                error.to_string().contains("native Windows"),
                "unexpected refusal text: {error}"
            );
        }
    }
}
