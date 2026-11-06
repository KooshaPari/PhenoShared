//! `brokerd` - run the browser broker as a service.
//!
//! ```text
//! brokerd --root ~/.local/state/browser-broker --bind 127.0.0.1:8787
//! brokerd --root /var/lib/broker --bind 0.0.0.0:8787 --token-env BROKER_TOKEN
//! ```

use std::{env, process::ExitCode, sync::Arc};

use substrate_browser_broker::{serve, Broker, ViewerConfig};

struct Args {
    root: String,
    bind: String,
    token: Option<String>,
    headed: bool,
    principal_tokens: bool,
}

fn parse_args() -> Result<Args, String> {
    let mut root = default_root();
    let mut bind = "127.0.0.1:8787".to_string();
    let mut token = None;
    let mut headed = false;
    let mut principal_tokens = false;

    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--root" => root = args.next().ok_or("--root needs a value")?,
            "--bind" => bind = args.next().ok_or("--bind needs a value")?,
            "--token" => token = args.next(),
            "--token-env" => {
                let name = args.next().ok_or("--token-env needs a name")?;
                token = env::var(&name).ok();
                if token.is_none() {
                    return Err(format!("{name} is not set"));
                }
            },
            "--headed" => headed = true,
            "--principal-tokens" => principal_tokens = true,
            "--help" | "-h" => {
                println!("{}", HELP);
                std::process::exit(0);
            },
            other => return Err(format!("unknown argument {other}")),
        }
    }

    Ok(Args {
        root,
        bind,
        token,
        headed,
        principal_tokens,
    })
}

const HELP: &str = "\
brokerd - lease-guarded browser broker

  --root <dir>       state directory (default: $XDG_STATE_HOME/browser-broker)
  --bind <addr>      viewer address (default: 127.0.0.1:8787)
  --token <value>    require this bearer token
  --token-env <var>  read the bearer token from an environment variable
  --headed           run browsers with a window instead of headless
  --principal-tokens require <PRINCIPAL>_BROKER_TOKEN env vars and scope each
                     token to that principal's sessions (overrides --token)

Binding anywhere other than loopback without --token is refused.";

fn default_root() -> String {
    if let Ok(state) = env::var("XDG_STATE_HOME") {
        return format!("{state}/browser-broker");
    }
    let home = env::var("HOME").unwrap_or_else(|_| ".".to_string());
    format!("{home}/.local/state/browser-broker")
}

fn is_loopback(bind: &str) -> bool {
    bind.starts_with("127.0.0.1:") || bind.starts_with("localhost:") || bind.starts_with("[::1]:")
}

#[tokio::main]
async fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(args) => args,
        Err(err) => {
            eprintln!("brokerd: {err}");
            return ExitCode::from(2);
        },
    };

    if !is_loopback(&args.bind) && args.token.is_none() && !args.principal_tokens {
        eprintln!(
            "brokerd: refusing to bind {} without a bearer token; \
             pass --token or --token-env",
            args.bind
        );
        return ExitCode::from(2);
    }

    let mut broker = match Broker::new(&args.root) {
        Ok(broker) => broker,
        Err(err) => {
            eprintln!("brokerd: {err}");
            return ExitCode::from(1);
        },
    };
    if args.headed {
        broker = broker.headed();
    }
    let broker = Arc::new(broker);

    let address = args.bind.clone();
    // Per-principal tokens come from `<PRINCIPAL>_BROKER_TOKEN` env vars when
    // `--principal-tokens` is passed; otherwise the single token applies.
    let mut principal_tokens = std::collections::BTreeMap::new();
    if args.principal_tokens {
        for (key, value) in std::env::vars() {
            if let Some(principal) = key.strip_suffix("_BROKER_TOKEN") {
                if !principal.is_empty() && !value.is_empty() {
                    principal_tokens.insert(principal.to_ascii_lowercase(), value);
                }
            }
        }
        if principal_tokens.is_empty() {
            eprintln!("brokerd: --principal-tokens found no <PRINCIPAL>_BROKER_TOKEN env vars");
            return ExitCode::from(2);
        }
    }

    let config = ViewerConfig {
        bind: args.bind,
        token: args.token,
        principal_tokens,
    };

    match serve(broker, config).await {
        Ok(()) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("brokerd: cannot serve on {address}: {err}");
            ExitCode::from(1)
        },
    }
}
