//! `browser-provider` - the broker behind a stdio NDJSON protocol loop.
//!
//! One JSON request per line on stdin, one JSON response per line on stdout.
//! This is the transport the browser provider protocol recommends for external
//! integrations, so a client can drive it without a library.

use std::io::{BufRead, Write};

use substrate_browser_broker::Broker;
use substrate_browser_provider::Provider;

fn default_root() -> String {
    if let Ok(state) = std::env::var("XDG_STATE_HOME") {
        return format!("{state}/browser-broker");
    }
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    format!("{home}/.local/state/browser-broker")
}

#[tokio::main]
async fn main() -> std::process::ExitCode {
    let mut root = default_root();
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--root" => match args.next() {
                Some(value) => root = value,
                None => {
                    eprintln!("browser-provider: --root needs a value");
                    return std::process::ExitCode::from(2);
                },
            },
            "--help" | "-h" => {
                println!("browser-provider [--root <dir>]\n\nSpeaks the browser provider protocol over stdio NDJSON.");
                return std::process::ExitCode::SUCCESS;
            },
            other => {
                eprintln!("browser-provider: unknown argument {other}");
                return std::process::ExitCode::from(2);
            },
        }
    }

    let broker = match Broker::new(&root) {
        Ok(broker) => std::sync::Arc::new(broker),
        Err(err) => {
            eprintln!("browser-provider: cannot open broker state at {root}: {err}");
            return std::process::ExitCode::from(1);
        },
    };

    let mut provider = Provider::new(broker);
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(line) => line,
            Err(err) => {
                eprintln!("browser-provider: stdin error: {err}");
                break;
            },
        };
        if line.trim().is_empty() {
            continue;
        }

        let request: serde_json::Value = match serde_json::from_str(&line) {
            Ok(value) => value,
            Err(err) => {
                let response = serde_json::json!({
                    "protocol_version": substrate_browser_provider::PROTOCOL_VERSION,
                    "id": serde_json::Value::Null,
                    "ok": false,
                    "error": { "code": "invalid_request", "message": format!("malformed JSON: {err}"), "retryable": false, "details": {} }
                });
                let _ = writeln!(stdout, "{response}");
                let _ = stdout.flush();
                continue;
            },
        };

        let response = provider.handle(&request).await;
        let _ = writeln!(stdout, "{response}");
        let _ = stdout.flush();
    }

    std::process::ExitCode::SUCCESS
}
