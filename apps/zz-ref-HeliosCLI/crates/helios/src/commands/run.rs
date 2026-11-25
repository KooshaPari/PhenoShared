// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! `run` subcommand handler.

use anyhow::Result;
use std::path::PathBuf;

/// Run a command through the harness runner
pub async fn cmd_run(
    command: String,
    dir: Option<PathBuf>,
    timeout: u64,
    shell: bool,
    sandbox: bool,
) -> Result<()> {
    use harness_runner::{Runner, RunnerConfig};

    if sandbox {
        println!("[helios] Sandbox mode enabled \u{2014} enabling OS-level sandboxing\u{2026}");
        helios_sandbox::enable_sandbox();

        let dangerous = [
            "rm -rf /",
            "mkfs",
            "dd if=",
            "> /dev/",
            "chmod 777 /",
            "wget",
            "curl | sh",
            "eval ",
            "exec ",
        ];
        let cmd_lower = command.to_lowercase();
        for pattern in &dangerous {
            if cmd_lower.contains(pattern) {
                anyhow::bail!(
                    "[helios] Sandbox: command rejected \u{2014} contains dangerous pattern: '{}'",
                    pattern
                );
            }
        }

        if dir.is_none() {
            println!("[helios] Sandbox: restricting working directory to current dir");
        }

        if helios_sandbox::is_sandboxed() {
            println!("[helios] Sandbox: filesystem access is now restricted (Landlock active)");
        }
    }

    println!("[helios] Running: {}", command);
    if let Some(ref d) = dir {
        println!("[helios] Working dir: {}", d.display());
    }
    println!("[helios] Timeout: {}s, Shell: {}, Sandbox: {}", timeout, shell, sandbox);

    let config = RunnerConfig {
        working_dir: dir.map(|p| p.to_string_lossy().to_string()),
        timeout_secs: Some(timeout),
        env: std::collections::HashMap::new(),
        shell,
    };

    let runner = Runner::with_config(config);

    match runner.run(&command, &[]).await {
        Ok(output) => {
            let code = output.exit_code.unwrap_or(1);
            println!("[helios] Exit code: {}", code);
            if !output.stdout.is_empty() {
                println!("--- stdout ---");
                println!("{}", output.stdout);
            }
            if !output.stderr.is_empty() {
                println!("--- stderr ---");
                eprintln!("{}", output.stderr);
            }
            if code != 0 {
                std::process::exit(code);
            }
            Ok(())
        }
        Err(e) => {
            eprintln!("[helios] Run failed: {}", e);
            anyhow::bail!("Command failed: {}", e)
        }
    }
}
