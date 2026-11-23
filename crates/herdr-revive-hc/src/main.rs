// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

use clap::Parser;
#[cfg(not(windows))]
use std::io::{BufWriter, IsTerminal, Write};

fn main() {
    #[cfg(windows)]
    match run_windows() {
        Ok(0) => {}
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("herdr-revive: {error:#}");
            std::process::exit(1);
        }
    }
    #[cfg(not(windows))]
    match run() {
        Ok(0) => {}
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("herdr-revive: {error:#}");
            std::process::exit(1);
        }
    }
}

/// Native Windows entry: save/list/preview/restore/status over Herdr Core's
/// named pipe. Shell-hook install, migrate and the Unix timer are not part of
/// this surface.
#[cfg(windows)]
fn run_windows() -> anyhow::Result<i32> {
    herdr_revive::winapp::run(herdr_revive::winapp::Cli::parse())
}

#[cfg(not(windows))]
fn run() -> anyhow::Result<i32> {
    let cli = herdr_revive::app::Cli::parse();
    if let Some((direction, confirm)) = herdr_revive::app::setup_request(&cli)? {
        let paths = herdr_revive::core::setup::Paths::from_env()?;
        let stdin = std::io::stdin();
        let tty = stdin.is_terminal() && std::io::stderr().is_terminal();
        return herdr_revive::core::setup::run(
            direction,
            confirm,
            &paths,
            &mut stdin.lock(),
            &mut std::io::stdout().lock(),
            &mut std::io::stderr().lock(),
            tty,
        );
    }
    if let Some(request) = herdr_revive::app::migrate_request(&cli)? {
        let stdin = std::io::stdin();
        let tty = stdin.is_terminal() && std::io::stderr().is_terminal();
        return herdr_revive::migrate::run(
            &request,
            &mut stdin.lock(),
            &mut std::io::stdout().lock(),
            &mut std::io::stderr().lock(),
            tty,
        );
    }
    let value = herdr_revive::app::run(cli)?;
    let mut output = BufWriter::new(std::io::stdout().lock());
    if let Some(text) = value
        .get("config")
        .or_else(|| value.get("text"))
        .and_then(serde_json::Value::as_str)
    {
        output.write_all(text.as_bytes())?;
    } else {
        serde_json::to_writer_pretty(&mut output, &value)?;
        writeln!(output)?;
    }
    output.flush()?;
    Ok(0)
}
