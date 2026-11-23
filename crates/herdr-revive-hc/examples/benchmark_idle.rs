// SPDX-FileCopyrightText: 2026 Su Kang Yin <paradyse@gmail.com>
// SPDX-License-Identifier: Apache-2.0

//! Measure the same idle-shell API in the baseline and candidate libraries.
//! It reads another process's identity, which this fork does on Unix only.
#[cfg(not(unix))]
fn main() {
    eprintln!("benchmark_idle: Unix process introspection is required");
    std::process::exit(2);
}

#[cfg(unix)]
fn main() -> anyhow::Result<()> {
    benchmark()
}

#[cfg(unix)]
fn benchmark() -> anyhow::Result<()> {
    use anyhow::{Context, ensure};
    use herdr_revive::{
        model::{ForegroundProcess, ProcessInfo},
        platform,
    };
    let args: Vec<_> = std::env::args().collect();
    let pid: u32 = args
        .get(1)
        .context("usage: benchmark_idle PID CHECKS")?
        .parse()?;
    let checks: u32 = args.get(2).context("missing check count")?.parse()?;
    ensure!((1..=10000).contains(&checks), "invalid check count");
    let shell = platform::process(pid)?;
    let info = ProcessInfo {
        pane_id: "benchmark".into(),
        shell_pid: Some(pid),
        foreground_process_group_id: Some(shell.group),
        foreground_processes: vec![ForegroundProcess {
            pid,
            ..ForegroundProcess::default()
        }],
    };
    let start = std::time::Instant::now();
    for _ in 0..checks {
        ensure!(
            platform::idle_shell(&info)?.is_some(),
            "fixture is no longer idle"
        );
    }
    println!(
        "{}",
        serde_json::json!({"checks":checks,"elapsed_ms":start.elapsed().as_secs_f64()*1000.0})
    );
    Ok(())
}
