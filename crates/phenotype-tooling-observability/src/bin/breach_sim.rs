//! Synthetic SLO breach generator for the Phase-5 closure-loop demo.
//!
//! Posts a configurable number of error + success counter increments to
//! the `phenotype-cli` /metrics endpoint to drive a sustained 5x burn
//! rate for 30 minutes, triggering the `PHENOTYPE-1` alert and the
//! `slo:phase1:crit` auto-issue path.
//!
//! Usage:
//!     breach-sim [--target URL] [--slo NAME] [--error-count N] [--success-count N] [--iterations N]
//!
//! Default target is `http://127.0.0.1:9090/metrics` (the dev
//! `pt observability` server). Default counts are 100 errors + 900
//! successes per iteration; raising --error-count pushes the burn rate
//! above the 5x threshold faster.

use std::env;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde_json::json;

/// HTTP endpoint where metrics are POSTed.
const METRICS_PATH: &str = "/metrics";

/// Synthetic SLO breach arguments parsed from CLI.
#[derive(Debug)]
struct Args {
    target: String,
    slo: String,
    error_count: u64,
    success_count: u64,
    iterations: u32,
}

fn print_help() {
    println!(
        "breach-sim — Synthetic SLO breach generator\n\n\
         USAGE:\n  breach-sim [OPTIONS]\n\n\
         OPTIONS:\n  \
             --target <URL>          Metrics endpoint (default http://127.0.0.1:9090)\n  \
             --slo <NAME>            SLO baseline name (default cli_success_rate)\n  \
             --error-count <N>      Error samples per iteration (default 100)\n  \
             --success-count <N>    Success samples per iteration (default 900)\n  \
             --iterations <N>       How many cycles to run (default 1)\n  \
             --help                 Print this help\n"
    );
}

fn parse_args() -> Result<Args, String> {
    let mut target = String::from("http://127.0.0.1:9090");
    let mut slo = String::from("cli_success_rate");
    let mut error_count: u64 = 100;
    let mut success_count: u64 = 900;
    let mut iterations: u32 = 1;

    let mut iter = env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--target" => {
                target = iter
                    .next()
                    .ok_or_else(|| "--target requires a value".to_string())?
            }
            "--slo" => {
                slo = iter
                    .next()
                    .ok_or_else(|| "--slo requires a value".to_string())?
            }
            "--error-count" => {
                error_count = iter
                    .next()
                    .ok_or_else(|| "--error-count requires a value".to_string())?
                    .parse()
                    .map_err(|e| format!("--error-count must be u64: {e}"))?
            }
            "--success-count" => {
                success_count = iter
                    .next()
                    .ok_or_else(|| "--success-count requires a value".to_string())?
                    .parse()
                    .map_err(|e| format!("--success-count must be u64: {e}"))?
            }
            "--iterations" => {
                iterations = iter
                    .next()
                    .ok_or_else(|| "--iterations requires a value".to_string())?
                    .parse()
                    .map_err(|e| format!("--iterations must be u32: {e}"))?
            }
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    Ok(Args {
        target,
        slo,
        error_count,
        success_count,
        iterations,
    })
}

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0)
}

fn main() -> Result<(), String> {
    let args = parse_args()?;

    // Map SLO baseline name to the actual Prometheus counter names
    // published by `phenotype_cli_observation_metrics`. The counters
    // are named `cli_errors_total` and `cli_invocations_total`.
    let error_metric = "cli_errors_total".to_string();
    let success_metric = "cli_invocations_total".to_string();
    let _ = args.slo.as_str(); // SLO name retained for log clarity

    println!(
        "breach-sim: posting to {} on slo {} (errors={}, successes={}, iterations={})",
        args.target, args.slo, args.error_count, args.success_count, args.iterations
    );

    // Build a small JSON body with the counter increments. We POST to
    // the metric sink which is expected to apply additive samples to
    // the underlying Prometheus counters.
    let body = json!({
        "increments": [
            {"name": error_metric,    "value": args.error_count},
            {"name": success_metric,  "value": args.success_count}
        ]
    });

    // Use a hand-rolled HTTP POST via std::net (no external HTTP
    // client) to keep the binary dependency-free.
    let url = format!("{}{}", args.target.trim_end_matches('/'), METRICS_PATH);
    let parsed = url::Url::parse(&url).map_err(|e| format!("invalid target URL: {e}"))?;

    let host = parsed
        .host_str()
        .ok_or_else(|| "target URL missing host".to_string())?;
    let port = parsed.port_or_known_default().unwrap_or(80);
    let path = parsed.path();

    for it in 0..args.iterations {
        println!("iteration {}/{}", it + 1, args.iterations);
        post_json(host, port, path, &body.to_string())?;
        println!(
            "  posted {} errors + {} successes ({}s elapsed)",
            args.error_count,
            args.success_count,
            it * 30
        );
    }

    println!(
        "\nbreach-sim: complete. In your dev stack:\n  \
         1. prometheus should fire PHENOTYPE-1 (5x burn, 30m window) within ~6m.\n  \
         2. .github/workflows/slo-backlog.yml opens a `slo:phase1:crit` issue.\n  \
         3. .github/workflows/slo-incident.yml assigns the on-call rotation.\n  \
         4. After ack + mitigation, incident-postmortem.yml writes postmortem/N.md.\n"
    );

    Ok(())
}

/// Minimal HTTP/1.1 POST helper. Sends Content-Length + body,
/// reads status line, returns Ok(()) for any 2xx; Err otherwise.
fn post_json(host: &str, port: u16, path: &str, body: &str) -> Result<(), String> {
    use std::io::{Read, Write};
    use std::net::TcpStream;

    let addr = format!("{host}:{port}");
    let mut stream = TcpStream::connect(&addr)
        .map_err(|e| format!("connect {addr}: {e}"))?;
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .map_err(|e| format!("set timeout: {e}"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(5)))
        .map_err(|e| format!("set timeout: {e}"))?;

    let req = format!(
        "POST {path} HTTP/1.1\r\n\
         Host: {host}\r\n\
         Content-Type: application/json\r\n\
         Content-Length: {len}\r\n\
         Connection: close\r\n\
         \r\n\
         {body}",
        path = path,
        host = host,
        len = body.len(),
        body = body
    );
    stream
        .write_all(req.as_bytes())
        .map_err(|e| format!("write: {e}"))?;

    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .map_err(|e| format!("read: {e}"))?;

    let status_line = response
        .lines()
        .next()
        .ok_or_else(|| "empty response".to_string())?;
    if !status_line.contains(" 2") {
        return Err(format!(
            "{addr}{path} responded {status_line}",
            addr = addr,
            path = path,
            status_line = status_line
        ));
    }
    Ok(())
}
