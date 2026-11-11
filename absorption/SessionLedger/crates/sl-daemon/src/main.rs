//! `sl-daemon` — SessionLedger daemon and CLI companion.
//!
//! ## Subcommands
//!
//! | Command     | Description                                               |
//! |-------------|-----------------------------------------------------------|
//! | `sl-daemon serve`  | Start the file-watcher daemon (long-running or `--once`)  |
//! | `sl-daemon status` | Check daemon liveness (`GET /healthz`)                    |
//! | `sl-daemon list`   | List compiled OKF bundle paths (`GET /api/bundles`)       |
//! | `sl-daemon tail`   | Stream new bundle paths as they arrive (`GET /api/stream`)|
//! | `sl-daemon export` | Export bundle metadata as CSV / Markdown / JSON            |
//! | `sl-daemon summary`| Print aggregate statistics across all bundles              |
//! | `sl-daemon check-update` | Compare installed version to GitHub latest release (no install) |
//!
//! ## HTTP API (exposed by `sl serve`)
//!
//! * `GET /healthz` — liveness probe
//! * `GET /api/bundles` — current OKF documents as JSON array
//! * `GET /api/stream` — SSE stream of new `*.okf.json` paths
//!
//! ## Exit codes
//!
//! * `0` — success (or daemon running, for `status`)
//! * `1` — daemon not running, validation failed, or no search matches
//! * `2` — general / unexpected error

// Platform default allocators (C00 L8). Unix → jemalloc; Windows → mimalloc.
// Opt out with `cargo build --no-default-features --features system-allocator`.
// See docs/ops/jemalloc-default-on.md.
#[cfg(all(unix, feature = "platform-allocator", not(feature = "system-allocator")))]
#[global_allocator]
static GLOBAL: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

#[cfg(all(windows, feature = "platform-allocator", not(feature = "system-allocator")))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

mod archive;
mod audit;
mod banner;
mod cli;
mod discovery;
mod etl;
mod export;
mod filter;
mod http;
mod metrics;
#[cfg(feature = "otel")]
mod otel;
#[cfg(feature = "otel-metrics")]
mod otel_metrics;
mod resilience;
mod shutdown;
mod tag;
mod update_check;
mod validation;
mod watcher;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use clap::{CommandFactory, Parser, Subcommand};
use clap_complete::{generate, Shell};
use sl_daemon::resolver;
use std::path::Path;
use tokio::sync::{broadcast, mpsc};
use tracing::{error, info, info_span, warn, Instrument};

/// Channel depth. Bounded so a slow consumer applies backpressure to the
/// watcher instead of letting an unbounded queue grow without limit.
const CHANNEL_CAPACITY: usize = 256;

/// Broadcast channel capacity for SSE notifications.
const BROADCAST_CAPACITY: usize = 256;

const CLI_AFTER_HELP: &str = r#"Examples:
  sl-daemon serve --watch ~/.cursor/agent-transcripts --out ./okf-out
  sl-daemon serve --watch ./sessions --out ./okf-out --once --http-bind 127.0.0.1:8080
  curl -X POST http://127.0.0.1:8080/api/ingest \
    -H 'content-type: application/json' --data-binary @bundle.json
  sl-daemon status
  sl-daemon search --tag production --format json
  sl-daemon completions zsh > _sl-daemon
  sl-daemon check-update
  sh scripts/install-sl-daemon-completions.sh
"#;

const CHECK_UPDATE_AFTER_HELP: &str = r#"Examples:
  sl-daemon check-update
  sl-daemon check-update --json
  sl-daemon check-update --repo KooshaPari/SessionLedger

Compares the installed sl-daemon version to the latest GitHub Release tag.
Does not download or install updates — see docs/ops/update-check.md and ADR 0001.
"#;

const SERVE_AFTER_HELP: &str = r#"Examples:
  sl-daemon serve --out ./okf-out  # auto-discovers native session roots
  sl-daemon serve --watch ~/.cursor/agent-transcripts --out ./okf-out
  sl-daemon serve --watch ./sessions --out ./okf-out --once
  sl-daemon serve --watch ./sessions --out ./okf-out --http-bind off
  SL_API_KEY=secret sl-daemon serve --watch ./sessions --out ./okf-out --http-bind 0.0.0.0:8080

Loopback binds (127.0.0.0/8, ::1) keep the local trust model: SL_API_KEY is optional
and only gates mutating routes when set. Non-loopback binds require a non-empty
SL_API_KEY and gate all /api/* routes. Use --http-bind off for batch jobs that do
not need HTTP.
"#;

const EXPORT_AFTER_HELP: &str = r#"Examples:
  sl-daemon export --format csv
  sl-daemon export --format md --out report.md ./out/sess-abc.okf.json
  sl-daemon export --format json --url http://127.0.0.1:9001
"#;

const SEARCH_AFTER_HELP: &str = r#"Examples:
  sl-daemon search --since 2026-01-01 --model gpt
  sl-daemon search --tag production --format json
  sl-daemon search --min-tokens 1000 --limit 10
"#;

const TAG_AFTER_HELP: &str = r#"Examples:
  sl-daemon tag add ./out/sess-abc.okf.json reviewed production
  sl-daemon tag list ./out/sess-abc.okf.json
  sl-daemon tag search reviewed --dir ./out
"#;

const ARCHIVE_AFTER_HELP: &str = r#"Examples:
  sl-daemon archive --before 2025-01-01 --data-dir ./okf-out
  sl-daemon archive --before 2025-01-01 --data-dir ./okf-out --dry-run
"#;

const RESTORE_AFTER_HELP: &str = r#"Examples:
  sl-daemon restore sess-abc --data-dir ./okf-out
  sl-daemon restore sess-abc --data-dir ./okf-out --out ./restored
"#;

const REPLAY_AFTER_HELP: &str = r#"Examples:
  sl-daemon replay sess-abc
  sl-daemon replay ./okf-out/sess-abc.okf.json --speed 2.0
  sl-daemon replay sess-abc --no-stream
"#;

const VALIDATE_AFTER_HELP: &str = r#"Examples:
  sl-daemon validate sess-abc --data-dir ./okf-out
"#;

const COMPLETIONS_AFTER_HELP: &str = r#"Examples:
  sl-daemon completions bash > sl-daemon.bash
  sl-daemon completions zsh > _sl-daemon
  sl-daemon completions fish > sl-daemon.fish
  sl-daemon completions powershell > sl-daemon.ps1

Committed scripts live under crates/sl-daemon/completions/. Install with:
  sh scripts/install-sl-daemon-completions.sh
  pwsh -File scripts/install-sl-daemon-completions.ps1
"#;

/// SessionLedger — daemon and CLI companion.
#[derive(Parser, Debug)]
#[command(name = "sl-daemon", version, about, after_help = CLI_AFTER_HELP)]
struct Args {
    /// Base URL of the daemon HTTP server (used by status / list / tail).
    #[arg(long, global = true, default_value = cli::DEFAULT_BASE_URL)]
    url: String,

    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Start the file-watcher daemon.
    #[command(after_help = SERVE_AFTER_HELP)]
    Serve {
        /// Directory to watch for `*.jsonl` session transcripts. When omitted,
        /// native Codex, Claude Code, and Cursor roots are discovered automatically.
        #[arg(long)]
        watch: Option<PathBuf>,

        /// Directory to write `<session-id>.okf.json` files into.
        #[arg(long)]
        out: PathBuf,

        /// Do a single sweep of `--watch` then exit (CI / cron-friendly).
        #[arg(long)]
        once: bool,

        /// Address to bind the HTTP server on (e.g. `127.0.0.1:8080`).
        /// Loopback keeps optional API-key trust; non-loopback requires `SL_API_KEY`.
        /// Pass `off` to disable the HTTP server entirely.
        #[arg(long, default_value = "127.0.0.1:8080")]
        http_bind: String,

        /// SQLite database for durable episodic memory (`SL_MEMORY_DB`).
        /// Requires `sl-daemon` built with `--features sqlite`.
        #[arg(long)]
        memory_db: Option<PathBuf>,
    },

    /// Check daemon status (exit 0 = running, exit 1 = not running).
    Status,

    /// List compiled OKF bundle paths (one per line).
    List,

    /// Stream new bundle paths as they arrive (SSE). Press Ctrl+C to stop.
    Tail,

    /// Export bundle metadata as CSV, Markdown, or JSON.
    ///
    /// When no bundle paths are given, all bundles are fetched from the daemon
    /// via GET /api/bundles.  Each bundle path must point to an OKF JSON file
    /// on the local filesystem.
    #[command(after_help = EXPORT_AFTER_HELP)]
    Export {
        /// Output format: csv | md | json  (default: csv).
        #[arg(long, default_value = "csv")]
        format: String,

        /// Write output to this file; defaults to stdout.
        #[arg(long)]
        out: Option<PathBuf>,

        /// OKF bundle file paths to export.  If omitted, fetches all from
        /// the daemon.
        bundles: Vec<PathBuf>,
    },

    /// Print aggregate statistics across all bundles.
    Summary {
        /// OKF bundle file paths to summarise.  If omitted, fetches all from
        /// the daemon.
        bundles: Vec<PathBuf>,
    },

    /// Manage tags on OKF bundle files.
    #[command(after_help = TAG_AFTER_HELP)]
    Tag {
        #[command(subcommand)]
        action: TagAction,
    },

    /// Archive bundles older than a given date by gzipping them.
    #[command(after_help = ARCHIVE_AFTER_HELP)]
    Archive {
        /// Archive bundles with created_at strictly before this date (YYYY-MM-DD).
        #[arg(long)]
        before: String,

        /// Directory containing the bundle JSON files (and where the archive
        /// sub-tree will be created).
        #[arg(long, default_value = ".")]
        data_dir: std::path::PathBuf,

        /// Print what would be archived without touching the filesystem.
        #[arg(long)]
        dry_run: bool,
    },

    /// Restore a previously archived bundle by decompressing it.
    #[command(after_help = RESTORE_AFTER_HELP)]
    Restore {
        /// Bundle ID (without extension) to restore from the archive.
        bundle_id: String,

        /// Directory that contains the `archive/` sub-tree.
        #[arg(long, default_value = ".")]
        data_dir: std::path::PathBuf,

        /// Directory to write the restored `.okf.json` file into.
        /// Defaults to `<data_dir>`.
        #[arg(long)]
        out: Option<PathBuf>,
    },

    /// Replay a compiled OKF bundle, streaming its entities in chronological
    /// order.  Connects to the running daemon's SSE endpoint unless
    /// `--bundle` points to a local file.
    #[command(after_help = REPLAY_AFTER_HELP)]
    Replay {
        /// Bundle ID (e.g. `sess-abc`) or path to a `.okf.json` file.
        bundle_id: String,

        /// Playback speed multiplier (default 1.0).  `--speed 2.0` replays
        /// at 2× real-time.
        #[arg(long, default_value = "1.0")]
        speed: f64,

        /// Print all entities at once without any delay.
        #[arg(long)]
        no_stream: bool,
    },

    /// Validate an OKF bundle on disk against the structural OKF contract.
    ///
    /// Reads `<data_dir>/<bundle_id>.okf.json` and validates its v1 graph,
    /// provenance, and relation references. Exits 0 when valid, 1 when invalid
    /// (diagnostics printed to stdout as JSON), 2 on I/O or parse error.
    #[command(after_help = VALIDATE_AFTER_HELP)]
    Validate {
        /// Bundle ID (filename stem, without `.okf.json`).
        bundle_id: String,

        /// Directory containing the `.okf.json` files.
        #[arg(long, default_value = ".")]
        data_dir: PathBuf,
    },

    /// Search / filter bundles by date, model, token count, or tags.
    ///
    /// When no `--bundles` paths are given, all bundles are fetched from the
    /// daemon via GET /api/bundles.
    #[command(after_help = SEARCH_AFTER_HELP)]
    Search {
        /// Include only bundles created on or after this date (YYYY-MM-DD).
        #[arg(long)]
        since: Option<String>,

        /// Include only bundles created on or before this date (YYYY-MM-DD).
        #[arg(long)]
        until: Option<String>,

        /// Include only bundles whose model name contains this substring
        /// (case-insensitive).
        #[arg(long)]
        model: Option<String>,

        /// Include only bundles with at least this many tokens.
        #[arg(long)]
        min_tokens: Option<u64>,

        /// Include only bundles that carry this tag (repeat for AND logic).
        #[arg(long = "tag", action = clap::ArgAction::Append)]
        tags: Vec<String>,

        /// Maximum number of results to return (default: 50).
        #[arg(long, default_value = "50")]
        limit: usize,

        /// Output format: text | json | csv  (default: text).
        #[arg(long, default_value = "text")]
        format: String,

        /// OKF bundle file paths to search. If omitted, fetches all from the
        /// daemon.
        bundles: Vec<PathBuf>,
    },

    /// Generate shell completion scripts to stdout.
    ///
    /// Supported shells: bash, zsh, fish, powershell.
    #[command(after_help = COMPLETIONS_AFTER_HELP)]
    Completions {
        /// Shell to generate completions for.
        #[arg(value_enum)]
        shell: Shell,
    },

    /// Compare installed version to the latest GitHub Release tag (no install).
    ///
    /// Exit 0 when up to date, 1 when a newer release exists, 2 on error.
    #[command(after_help = CHECK_UPDATE_AFTER_HELP)]
    CheckUpdate {
        /// GitHub `owner/repo` to query (default: KooshaPari/SessionLedger).
        #[arg(long, default_value = update_check::DEFAULT_REPO)]
        repo: String,

        /// Emit JSON instead of human-readable text.
        #[arg(long)]
        json: bool,

        /// Use this release tag instead of calling the GitHub API (tests / offline).
        #[arg(long)]
        latest: Option<String>,
    },
}

/// Sub-actions for `sl tag`.
#[derive(Subcommand, Debug)]
enum TagAction {
    /// Add one or more tags to a bundle.
    Add {
        /// Path to the `.okf.json` bundle file.
        bundle: PathBuf,
        /// Tags to add.
        #[arg(required = true)]
        tags: Vec<String>,
    },

    /// Remove one or more tags from a bundle.
    Remove {
        /// Path to the `.okf.json` bundle file.
        bundle: PathBuf,
        /// Tags to remove.
        #[arg(required = true)]
        tags: Vec<String>,
    },

    /// List current tags on a bundle.
    List {
        /// Path to the `.okf.json` bundle file.
        bundle: PathBuf,
    },

    /// Search a directory for bundles that carry a specific tag.
    Search {
        /// Tag to search for.
        tag: String,
        /// Directory to scan (recursively) for `*.okf.json` files.
        /// Defaults to the current directory.
        #[arg(default_value = ".")]
        dir: PathBuf,
    },
}

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    #[cfg(feature = "otel")]
    let otel_provider = init_tracing();
    #[cfg(not(feature = "otel"))]
    init_tracing();
    #[cfg(feature = "otel-metrics")]
    let otel_metrics_provider = otel_metrics::maybe_init();
    let args = Args::parse();

    match args.command {
        Command::Serve { watch, out, once, http_bind, memory_db } => {
            let memory_db = memory_db.or_else(|| {
                std::env::var("SL_MEMORY_DB")
                    .ok()
                    .filter(|value| !value.trim().is_empty())
                    .map(PathBuf::from)
            });
            if let Err(error) = run_serve(watch, out, once, http_bind, memory_db).await {
                cli::exit_error(error);
            }
        }
        Command::Status => run_status(&args.url).await,
        Command::List => run_list(&args.url).await,
        Command::Tail => run_tail(&args.url).await,
        Command::Export { format, out, bundles } => {
            run_export(&args.url, &format, out.as_deref(), &bundles).await;
        }
        Command::Summary { bundles } => {
            run_summary(&args.url, &bundles).await;
        }
        Command::Tag { action } => {
            run_tag(action);
        }
        Command::Archive { before, data_dir, dry_run } => {
            run_archive(&before, &data_dir, dry_run);
        }
        Command::Restore { bundle_id, data_dir, out } => {
            run_restore(&bundle_id, &data_dir, out.as_deref());
        }
        Command::Replay { bundle_id, speed, no_stream } => {
            run_replay(&args.url, &bundle_id, speed, no_stream).await;
        }
        Command::Validate { bundle_id, data_dir } => {
            run_validate(&bundle_id, &data_dir);
        }
        Command::Search { since, until, model, min_tokens, tags, limit, format, bundles } => {
            run_search(&args.url, since, until, model, min_tokens, tags, limit, &format, &bundles)
                .await;
        }
        Command::Completions { shell } => {
            run_completions(shell);
        }
        Command::CheckUpdate { repo, json, latest } => {
            run_check_update(&repo, json, latest.as_deref()).await;
        }
    }

    #[cfg(feature = "otel")]
    if let Some(provider) = otel_provider {
        let _ = provider.shutdown();
    }
    #[cfg(feature = "otel-metrics")]
    if let Some(provider) = otel_metrics_provider {
        let _ = provider.shutdown();
    }

    Ok(())
}

fn run_completions(shell: Shell) {
    let mut command = Args::command();
    generate(shell, &mut command, "sl-daemon", &mut std::io::stdout());
}

/// Install a `tracing` subscriber filtered by `RUST_LOG`.
///
/// Default when unset: `sl_daemon=info` (matches docs/ops/observability.md).
#[cfg(not(feature = "otel"))]
fn init_tracing() {
    use tracing_subscriber::EnvFilter;

    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("sl_daemon=info"));

    #[cfg(feature = "json-logs")]
    if json_logs_requested() {
        tracing_subscriber::fmt().json().with_env_filter(filter.clone()).with_target(true).init();
        return;
    }

    tracing_subscriber::fmt().with_env_filter(filter).with_target(true).init();
}

#[cfg(feature = "json-logs")]
fn json_logs_requested() -> bool {
    std::env::var("SL_LOG_FORMAT").is_ok_and(|value| value.eq_ignore_ascii_case("json"))
}

/// Install the formatting subscriber and, when configured, OTLP trace export.
#[cfg(feature = "otel")]
fn init_tracing() -> Option<opentelemetry_sdk::trace::SdkTracerProvider> {
    use tracing_subscriber::EnvFilter;

    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("sl_daemon=info"));
    match otel::LangfuseConfig::from_env() {
        Ok(Some(config)) => {
            #[cfg(feature = "json-logs")]
            let json_logs = json_logs_requested();
            #[cfg(not(feature = "json-logs"))]
            let json_logs = false;
            match otel::init_langfuse(filter.clone(), &config, json_logs) {
                Ok(provider) => return Some(provider),
                Err(error) => eprintln!("warning: failed to initialize Langfuse OTLP export: {error}; continuing with local logs"),
            }
        }
        Ok(None) => {}
        Err(error) => eprintln!(
            "warning: invalid Langfuse configuration: {error}; continuing with local logs"
        ),
    }
    let endpoint = std::env::var("SL_OTLP_ENDPOINT")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .or_else(|| {
            std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
                .ok()
                .filter(|value| !value.trim().is_empty())
        });

    if let Some(endpoint) = endpoint {
        #[cfg(feature = "json-logs")]
        let json_logs = json_logs_requested();
        #[cfg(not(feature = "json-logs"))]
        let json_logs = false;
        match otel::init(filter, &endpoint, json_logs) {
            Ok(provider) => return Some(provider),
            Err(error) => {
                eprintln!(
                    "warning: failed to initialize OTLP export for {endpoint:?}: {error}; \
                     continuing with local logs"
                );
            }
        }
    }

    let filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("sl_daemon=info"));
    #[cfg(feature = "json-logs")]
    if json_logs_requested() {
        tracing_subscriber::fmt().json().with_env_filter(filter.clone()).with_target(true).init();
        return None;
    }

    tracing_subscriber::fmt().with_env_filter(filter).with_target(true).init();
    None
}

fn parse_http_bind(value: &str) -> Result<SocketAddr, String> {
    value.parse().map_err(|error| format!("invalid --http-bind address {value:?}: {error}"))
}

/// Non-loopback binds require a configured API key; loopback keeps optional-key behavior.
fn ensure_http_bind_auth(addr: SocketAddr, auth: &http::ApiKeyAuth) -> Result<(), String> {
    if addr.ip().is_loopback() {
        return Ok(());
    }
    if auth.is_configured() {
        return Ok(());
    }
    Err(format!(
        "non-loopback --http-bind {addr} requires SL_API_KEY \
         (set a non-empty shared secret, or bind to 127.0.0.0/8 or ::1 for the local trust model)"
    ))
}

fn audit_event(
    sink: &audit::AuditSink,
    action: &'static str,
    outcome: &'static str,
    resource: &dyn std::fmt::Display,
) {
    let request_id = audit::local_request_id();
    let resource = resource.to_string();
    info!(
        target: "sl_daemon::audit",
        event_kind = "audit",
        actor = audit::LOCAL_ACTOR,
        action,
        outcome,
        request_id,
        resource = %resource,
        "local operation"
    );
    let event = audit::AuditEvent {
        timestamp: audit::timestamp_unix_ms(),
        actor: audit::LOCAL_ACTOR,
        action,
        outcome,
        request_id: &request_id,
        reason: None,
        resource: Some(resource),
    };
    if let Err(error) = sink.append(&event) {
        warn!(error = %error, path = %sink.path().display(), "failed to append audit event");
    }
}

// ---------------------------------------------------------------------------
// serve
// ---------------------------------------------------------------------------

async fn run_serve(
    watch: Option<PathBuf>,
    out: PathBuf,
    once: bool,
    http_bind: String,
    memory_db: Option<PathBuf>,
) -> Result<(), Box<dyn std::error::Error>> {
    let watch_roots = match watch {
        Some(path) => vec![path],
        None => discovery::local_watch_roots(None),
    };
    if watch_roots.is_empty() {
        return Err(
            "no supported local session stores found; pass --watch to use a custom root".into()
        );
    }
    info!(roots = ?watch_roots, "session roots selected");
    let version = env!("CARGO_PKG_VERSION");
    banner::emit_interactive_banner(version);
    info!(banner = %banner::plain_banner(version), "startup");

    #[cfg(not(feature = "sqlite"))]
    if memory_db.is_some() {
        return Err(
            "--memory-db / SL_MEMORY_DB requires sl-daemon built with --features sqlite".into()
        );
    }

    #[cfg(feature = "sqlite")]
    let memory_store: Option<Arc<session_ledger::SqliteMemoryStore>> = if let Some(path) = memory_db
    {
        let store = session_ledger::SqliteMemoryStore::open(&path).map_err(|error| {
            format!("failed to open memory database {}: {error}", path.display())
        })?;
        info!(memory_db = %path.display(), "durable memory store enabled");
        Some(Arc::new(store))
    } else {
        None
    };

    // Broadcast channel: ETL consumer publishes every written path; HTTP SSE
    // handler subscribes one receiver per connected client.
    let (bcast_tx, _bcast_rx) = broadcast::channel::<PathBuf>(BROADCAST_CAPACITY);

    let shutdown = shutdown::ServeShutdown::new();
    let _ctrl_c = shutdown.spawn_ctrl_c_handler();

    let (tx, mut rx) = mpsc::channel::<PathBuf>(CHANNEL_CAPACITY);
    let out_dir = out.clone();
    let data_dir = audit::data_dir_from_env_or(&out);
    let audit_sink = Arc::new(
        audit::AuditSink::open(&data_dir).map_err(|error| format!("audit sink: {error}"))?,
    );

    // Consumer: drain the channel, transforming each path.
    let bcast_for_consumer = bcast_tx.clone();
    let audit_sink_for_consumer = audit_sink.clone();
    #[cfg(feature = "sqlite")]
    let memory_for_consumer = memory_store.clone();
    let shutdown_for_consumer = shutdown.clone();
    let consumer = tokio::spawn(
        async move {
            let mut total = 0usize;
            loop {
                tokio::select! {
                    _ = shutdown_for_consumer.cancelled() => {
                        info!("ETL consumer cancelled");
                        break;
                    }
                    path = rx.recv() => {
                        let Some(path) = path else {
                            break;
                        };
                        let span = info_span!("etl.transform", path = %path.display());
                        async {
                            #[cfg(feature = "sqlite")]
                            let memory_ref = memory_for_consumer
                                .as_ref()
                                .map(|store| store.as_ref() as &dyn session_ledger::ports::MemoryStore);
                            #[cfg(not(feature = "sqlite"))]
                            let memory_ref: Option<&dyn session_ledger::ports::MemoryStore> = None;
                            match etl::transform_file(&path, &out_dir, memory_ref) {
                                Ok(written) => {
                                    total += written.len();
                                    for w in &written {
                                        let _ = bcast_for_consumer.send(w.clone());
                                        audit_event(
                                            &audit_sink_for_consumer,
                                            "export",
                                            "succeeded",
                                            &w.display(),
                                        );
                                    }
                                    info!(
                                        path = %path.display(),
                                        okf_docs = written.len(),
                                        "ETL transform ok"
                                    );
                                }
                                Err(err) => {
                                    audit_event(
                                        &audit_sink_for_consumer,
                                        "export",
                                        "failed",
                                        &path.display(),
                                    );
                                    error!(path = %path.display(), error = %err, "ETL transform failed");
                                }
                            }
                        }
                        .instrument(span)
                        .await;
                    }
                }
            }
            total
        }
        .instrument(info_span!("etl.consumer")),
    );

    // HTTP server (optional).
    let http_handle = if http_bind.eq_ignore_ascii_case("off") {
        None
    } else {
        let addr = parse_http_bind(&http_bind)?;
        let ingest_admission = http::IngestAdmission::from_env()?;
        let mut api_key_auth = http::ApiKeyAuth::from_env();
        ensure_http_bind_auth(addr, &api_key_auth)?;
        if !addr.ip().is_loopback() {
            api_key_auth = api_key_auth.with_protect_all_api(true);
            info!(%addr, "non-loopback HTTP bind; SL_API_KEY required for all /api/* routes");
        }
        // Shared-key or non-loopback path gets a default tower-style API throttle;
        // pure loopback DX leaves it off unless SL_API_RATE_LIMIT is set.
        let enforce_api_rate_default = api_key_auth.is_configured() || !addr.ip().is_loopback();
        let api_rate_limit = http::ApiRateLimit::from_env(enforce_api_rate_default)?;
        if api_rate_limit.is_enabled() {
            info!(
                limit = api_rate_limit.limit,
                window_ms = api_rate_limit.window.as_millis() as u64,
                "HTTP /api/* rate limit enabled"
            );
        }
        let api_circuit_breaker =
            resilience::ApiCircuitBreaker::from_env(enforce_api_rate_default)?;
        if api_circuit_breaker.is_enabled() {
            info!(
                failure_threshold = api_circuit_breaker.failure_threshold,
                open_ms = api_circuit_breaker.open_for.as_millis() as u64,
                "HTTP /api/* circuit breaker enabled"
            );
        }
        let state = http::AppState {
            resolver: resolver::Resolver::open(
                std::env::var_os("SL_NATIVE_SESSION_REGISTRY")
                    .map(PathBuf::from)
                    .unwrap_or_else(|| out.join("native-sessions.jsonl")),
            )
            .unwrap_or_default(),
            out_dir: Arc::new(out.clone()),
            broadcast_tx: bcast_tx.clone(),
            http_metrics: Arc::new(metrics::HttpMetrics::default()),
            ingest_admission,
            api_rate_limit,
            api_circuit_breaker,
            api_key_auth,
            audit_sink: audit_sink.clone(),
            idempotency_cache: http::IngestIdempotencyCache::default(),
            #[cfg(feature = "sqlite")]
            memory_store: memory_store.clone(),
        };
        // Start serving with centralized bind+serve flow.
        let shutdown_for_http = shutdown.clone();
        let handle = tokio::spawn(async move {
            if let Err(e) = http::serve(addr, state, async move {
                shutdown_for_http.cancelled().await;
            })
            .await
            {
                error!(error = %e, "HTTP server error");
            }
        });
        info!(%addr, "HTTP server listening");
        Some(handle)
    };

    if once {
        let mut sent = 0;
        for root in &watch_roots {
            sent += watcher::scan_once(root, &tx, shutdown.token()).await?;
        }
        info!(enqueued = sent, "once: scan complete");
        drop(tx);
        let total = consumer.await?;
        info!(okf_docs = total, "once: ETL complete");
        shutdown.cancel();
        if let Some(handle) = http_handle {
            let _ = handle.await;
        }
        return Ok(());
    }

    // Long-running mode.
    let mut watchers = Vec::with_capacity(watch_roots.len());
    for root in &watch_roots {
        watcher::scan_once(root, &tx, shutdown.token()).await?;
        watchers.push(watcher::spawn_fs_watcher(root, tx.clone())?);
    }
    info!(roots = ?watch_roots, out = %out.display(), "watching for sessions");

    drop(tx);

    shutdown.cancelled().await;
    info!("shutting down");
    drop(watchers);

    if let Some(handle) = http_handle {
        let _ = handle.await;
    }

    let total = consumer.await?;
    info!(okf_docs = total, "ETL consumer finished");
    Ok(())
}

// ---------------------------------------------------------------------------
// check-update
// ---------------------------------------------------------------------------

async fn run_check_update(repo: &str, json: bool, latest_override: Option<&str>) {
    let installed = env!("CARGO_PKG_VERSION");
    let latest_override = latest_override.map(str::to_owned).or_else(|| {
        std::env::var("SL_CHECK_UPDATE_LATEST").ok().filter(|value| !value.trim().is_empty())
    });
    let latest_tag = match latest_override {
        Some(tag) => tag,
        None => {
            let client = reqwest::Client::new();
            match update_check::fetch_latest_release_tag(&client, repo).await {
                Ok(tag) => tag,
                Err(error) => cli::exit_error(format!("update check failed: {error}")),
            }
        }
    };

    let status = update_check::compare_versions(installed, &latest_tag);
    if json {
        let payload = serde_json::to_string_pretty(&status).unwrap_or_default();
        println!("{payload}");
    } else {
        println!("{}", update_check::format_status(&status));
    }

    if status.is_update_available() {
        std::process::exit(cli::EXIT_NOT_OK);
    }
}

// ---------------------------------------------------------------------------
// status
// ---------------------------------------------------------------------------

async fn run_status(base_url: &str) {
    let client = reqwest::Client::new();
    match cli::fetch_health(&client, base_url).await {
        Ok(cli::HealthStatus::Running { body }) => {
            println!("daemon running — {body}");
            std::process::exit(cli::EXIT_OK);
        }
        Ok(cli::HealthStatus::NotRunning) => {
            println!("daemon not running");
            eprintln!("hint: {}", cli::daemon_down_message(base_url));
            std::process::exit(cli::EXIT_NOT_OK);
        }
        Err(e) => cli::exit_on_reqwest(base_url, "health check failed", e),
    }
}

// ---------------------------------------------------------------------------
// list
// ---------------------------------------------------------------------------

async fn run_list(base_url: &str) {
    let client = reqwest::Client::new();
    match cli::fetch_bundle_paths(&client, base_url).await {
        Ok(paths) => {
            for p in &paths {
                println!("{p}");
            }
        }
        Err(e) => cli::exit_on_reqwest(base_url, "fetching bundle list", e),
    }
}

// ---------------------------------------------------------------------------
// tail
// ---------------------------------------------------------------------------

async fn run_tail(base_url: &str) {
    use futures_util::TryStreamExt as _;
    use tokio::io::{AsyncBufReadExt, BufReader};
    use tokio_util::io::StreamReader;

    let url = cli::build_url(base_url, "/api/stream");
    let client = reqwest::Client::new();

    let resp = match client.get(&url).header("Accept", "text/event-stream").send().await {
        Ok(r) => r,
        Err(e) => cli::exit_on_reqwest(base_url, "connecting to SSE stream", e),
    };

    let byte_stream = resp.bytes_stream().map_err(std::io::Error::other);
    let stream_reader = StreamReader::new(byte_stream);
    let mut lines = BufReader::new(stream_reader).lines();

    tokio::select! {
        _ = async {
            while let Ok(Some(line)) = lines.next_line().await {
                // SSE data lines: "data: <payload>"
                if let Some(payload) = line.strip_prefix("data: ") {
                    println!("{payload}");
                }
            }
        } => {}
        _ = tokio::signal::ctrl_c() => {
            println!("\nstopped.");
        }
    }
}

// ---------------------------------------------------------------------------
// export
// ---------------------------------------------------------------------------

/// Load OKF JSON files from `paths` into [`export::BundleMeta`] objects.
///
/// Skips files that cannot be read or parsed, printing a warning to stderr.
fn load_metas(paths: &[PathBuf]) -> Vec<export::BundleMeta> {
    paths
        .iter()
        .filter_map(|p| match std::fs::read_to_string(p) {
            Err(e) => {
                eprintln!("warning: cannot read {}: {e}", p.display());
                None
            }
            Ok(text) => match serde_json::from_str::<serde_json::Value>(&text) {
                Err(e) => {
                    eprintln!("warning: cannot parse {}: {e}", p.display());
                    None
                }
                Ok(v) => Some(export::BundleMeta::from_value(&v)),
            },
        })
        .collect()
}

async fn resolve_bundle_paths(base_url: &str, given: &[PathBuf]) -> Vec<PathBuf> {
    if !given.is_empty() {
        return given.to_vec();
    }
    let client = reqwest::Client::new();
    match cli::fetch_bundle_paths(&client, base_url).await {
        Ok(paths) => paths.into_iter().map(PathBuf::from).collect(),
        Err(e) => cli::exit_on_reqwest(base_url, "fetching bundle list", e),
    }
}

async fn run_export(
    base_url: &str,
    format_str: &str,
    out_path: Option<&std::path::Path>,
    given_bundles: &[PathBuf],
) {
    use std::str::FromStr as _;

    let fmt = match export::ExportFormat::from_str(format_str) {
        Ok(f) => f,
        Err(e) => cli::exit_error(e),
    };

    let paths = resolve_bundle_paths(base_url, given_bundles).await;
    let metas = load_metas(&paths);

    let rendered = match fmt {
        export::ExportFormat::Csv => export::render_csv(&metas),
        export::ExportFormat::Markdown => export::render_markdown(&metas),
        export::ExportFormat::Json => export::render_json(&metas),
    };

    match out_path {
        Some(p) => {
            if let Err(e) = std::fs::write(p, &rendered) {
                cli::exit_error(format!("writing to {}: {e}", p.display()));
            }
        }
        None => print!("{rendered}"),
    }
}

// ---------------------------------------------------------------------------
// tag
// ---------------------------------------------------------------------------

fn run_tag(action: TagAction) {
    match action {
        TagAction::Add { bundle, tags } => match tag::add(&bundle, &tags) {
            Ok(updated) => {
                eprintln!("tags updated: {:?}", updated);
            }
            Err(e) => cli::exit_error(e),
        },
        TagAction::Remove { bundle, tags } => match tag::remove(&bundle, &tags) {
            Ok(updated) => {
                eprintln!("tags updated: {:?}", updated);
            }
            Err(e) => cli::exit_error(e),
        },
        TagAction::List { bundle } => match tag::list(&bundle) {
            Ok(tags) => {
                for t in &tags {
                    println!("{t}");
                }
            }
            Err(e) => cli::exit_error(e),
        },
        TagAction::Search { tag: search_tag, dir } => match tag::search_dir(&dir, &search_tag) {
            Ok(paths) => {
                for p in &paths {
                    println!("{}", p.display());
                }
            }
            Err(e) => cli::exit_error(e),
        },
    }
}

// ---------------------------------------------------------------------------
// summary
// ---------------------------------------------------------------------------

async fn run_summary(base_url: &str, given_bundles: &[PathBuf]) {
    let paths = resolve_bundle_paths(base_url, given_bundles).await;
    let metas = load_metas(&paths);
    let summary = export::compute_summary(&metas);
    print!("{}", export::render_summary(&summary));
}

// ---------------------------------------------------------------------------
// archive
// ---------------------------------------------------------------------------

fn run_archive(before_str: &str, data_dir: &Path, dry_run: bool) {
    let before = match chrono::NaiveDate::parse_from_str(before_str, "%Y-%m-%d") {
        Ok(d) => d,
        Err(e) => {
            cli::exit_error(format!(
                "invalid --before date {before_str:?}: {e} (expected YYYY-MM-DD)"
            ));
        }
    };

    if dry_run {
        println!("[dry-run] bundles that would be archived (before {before}):");
    }

    match archive::archive_bundles(data_dir, before, dry_run) {
        Ok(stats) => {
            let audit_sink = audit::AuditSink::open(data_dir).unwrap_or_else(|error| {
                eprintln!("error: audit sink: {error}");
                std::process::exit(2);
            });
            audit_event(
                &audit_sink,
                "archive",
                if dry_run { "dry_run" } else { "succeeded" },
                &stats.archive_dir.display(),
            );
            let mb_saved = stats.bytes_saved as f64 / 1_048_576.0;
            println!(
                "Archived {} bundle(s), saved {:.2} MB  (archive: {})",
                stats.archived_count,
                mb_saved,
                stats.archive_dir.display()
            );
        }
        Err(e) => {
            let audit_sink = audit::AuditSink::open(data_dir).unwrap_or_else(|error| {
                eprintln!("error: audit sink: {error}");
                std::process::exit(2);
            });
            audit_event(&audit_sink, "archive", "failed", &data_dir.display());
            cli::exit_error(e);
        }
    }
}

// ---------------------------------------------------------------------------
// restore
// ---------------------------------------------------------------------------

fn run_restore(bundle_id: &str, data_dir: &Path, out: Option<&Path>) {
    let audit_sink = audit::AuditSink::open(data_dir).unwrap_or_else(|error| {
        eprintln!("error: audit sink: {error}");
        std::process::exit(2);
    });
    let archive_root = data_dir.join("archive");
    let archive_path = match archive::find_archive_path(&archive_root, bundle_id) {
        Ok(p) => p,
        Err(e) => cli::exit_error(e),
    };

    let output_dir = out.unwrap_or(data_dir);
    match archive::restore_bundle(&archive_path, output_dir) {
        Ok(restored) => {
            audit_event(&audit_sink, "restore", "succeeded", &restored.display());
            println!("Restored: {}", restored.display());
        }
        Err(e) => {
            audit_event(&audit_sink, "restore", "failed", &archive_path.display());
            cli::exit_error(e);
        }
    }
}

// ---------------------------------------------------------------------------
// validate
// ---------------------------------------------------------------------------

fn run_validate(bundle_id: &str, data_dir: &Path) {
    let errors = match validate_on_disk_okf(bundle_id, data_dir) {
        Ok(errors) => errors,
        Err(error) => cli::exit_error(error),
    };
    let result = serde_json::json!({
        "valid": errors.is_empty(),
        "errors": errors,
    });
    println!("{result}");
    if !errors.is_empty() {
        std::process::exit(cli::EXIT_NOT_OK);
    }
}

fn validate_on_disk_okf(
    bundle_id: &str,
    data_dir: &Path,
) -> Result<Vec<session_ledger::OkfValidationError>, String> {
    let path = data_dir.join(format!("{}.okf.json", crate::etl::sanitize(bundle_id)));
    let text = std::fs::read_to_string(&path)
        .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    let document: session_ledger::OkfDocument = serde_json::from_str(&text)
        .map_err(|error| format!("cannot parse {}: {error}", path.display()))?;
    Ok(session_ledger::validate_okf_document(&document))
}

// ---------------------------------------------------------------------------
// search
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
async fn run_search(
    base_url: &str,
    since: Option<String>,
    until: Option<String>,
    model: Option<String>,
    min_tokens: Option<u64>,
    tags: Vec<String>,
    limit: usize,
    format_str: &str,
    given_bundles: &[PathBuf],
) {
    use std::str::FromStr as _;

    let paths = resolve_bundle_paths(base_url, given_bundles).await;
    let metas = load_metas(&paths);

    let spec = filter::FilterSpec { since, until, model, min_tokens, tags, limit };
    let matched: Vec<&export::BundleMeta> = filter::apply_filters(&metas, &spec);

    if matched.is_empty() {
        eprintln!("no bundles matched the given filters");
        std::process::exit(cli::EXIT_NOT_OK);
    }

    let owned: Vec<export::BundleMeta> = matched.into_iter().cloned().collect();

    let rendered = if format_str.eq_ignore_ascii_case("text") {
        let mut out = String::new();
        for m in &owned {
            out.push_str(&format!(
                "{}\t{}\t{}\t{}\t[{}]\n",
                m.session_id,
                m.created_at,
                m.model,
                m.token_count,
                m.tags.join(", ")
            ));
        }
        out
    } else {
        let fmt = match export::ExportFormat::from_str(format_str) {
            Ok(f) => f,
            Err(e) => cli::exit_error(e),
        };
        match fmt {
            export::ExportFormat::Csv => export::render_csv(&owned),
            export::ExportFormat::Markdown => export::render_markdown(&owned),
            export::ExportFormat::Json => export::render_json(&owned),
        }
    };

    print!("{rendered}");
}

// ---------------------------------------------------------------------------
// replay
// ---------------------------------------------------------------------------

/// Format a timestamp from seconds as `HH:MM:SS`.
pub(crate) fn format_timestamp(secs: u64) -> String {
    let h = secs / 3600;
    let m = (secs % 3600) / 60;
    let s = secs % 60;
    format!("{h:02}:{m:02}:{s:02}")
}

/// Truncate `text` to at most `max_chars` characters, appending `…` when cut.
pub(crate) fn truncate(text: &str, max_chars: usize) -> String {
    let chars: Vec<char> = text.chars().collect();
    if chars.len() <= max_chars {
        text.to_owned()
    } else {
        let mut s: String = chars[..max_chars.saturating_sub(1)].iter().collect();
        s.push('\u{2026}');
        s
    }
}

/// Format one OKF entity into a single stdout line.
///
/// Output: `[HH:MM:SS] <type>/<id>: <label_preview>`
pub(crate) fn format_entity_line(entity: &serde_json::Value, event_index: usize) -> String {
    let ts = format_timestamp(event_index as u64);
    let entity_type = entity.get("type").and_then(|v| v.as_str()).unwrap_or("unknown");
    let entity_id = entity.get("id").and_then(|v| v.as_str()).unwrap_or("?");
    let label = entity.get("label").and_then(|v| v.as_str()).unwrap_or("");
    let preview = truncate(label, 80);
    format!("[{ts}] {entity_type}/{entity_id}: {preview}")
}

async fn run_replay(base_url: &str, bundle_id: &str, speed: f64, no_stream: bool) {
    use futures_util::TryStreamExt as _;
    use tokio::io::{AsyncBufReadExt, BufReader};
    use tokio_util::io::StreamReader;

    // Build `?speed=N` only when not no_stream (speed irrelevant then).
    let speed_param = if no_stream { String::new() } else { format!("?speed={speed}") };
    let url = format!("{}/api/replay/{bundle_id}{speed_param}", base_url.trim_end_matches('/'));

    let client = reqwest::Client::new();
    let resp = match client.get(&url).header("Accept", "text/event-stream").send().await {
        Ok(r) => r,
        Err(e) => cli::exit_on_reqwest(base_url, "connecting to replay stream", e),
    };

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        cli::exit_error(format!("server error {status}: {body}"));
    }

    let byte_stream = resp.bytes_stream().map_err(std::io::Error::other);
    let stream_reader = StreamReader::new(byte_stream);
    let mut lines = BufReader::new(stream_reader).lines();

    // Parse SSE line-by-line; accumulate data for each event block.
    let mut current_event: Option<String> = None;
    let mut current_data = String::new();

    let print_entity = |data: &str| {
        if let Ok(v) = serde_json::from_str::<serde_json::Value>(data) {
            // Done sentinel.
            if v.as_object().is_some_and(|o| o.is_empty()) {
                println!("[replay complete]");
                return;
            }
            let idx = v.get("event_index").and_then(|x| x.as_u64()).unwrap_or(0) as usize;
            if let Some(entity) = v.get("entity") {
                println!("{}", format_entity_line(entity, idx));
            }
        }
    };

    tokio::select! {
        _ = async {
            while let Ok(Some(line)) = lines.next_line().await {
                if let Some(stripped) = line.strip_prefix("event: ") {
                    current_event = Some(stripped.to_owned());
                } else if let Some(data) = line.strip_prefix("data: ") {
                    current_data = data.to_owned();
                } else if line.is_empty() {
                    // End of event block.
                    if matches!(current_event.as_deref(), Some("done")) {
                        println!("[replay complete]");
                        break;
                    }
                    if !current_data.is_empty() {
                        print_entity(&current_data);
                    }
                    current_event = None;
                    current_data.clear();
                }
            }
        } => {}
        _ = tokio::signal::ctrl_c() => {
            println!("\nstopped.");
        }
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_on_disk_okf_accepts_daemon_generated_document() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let watch = tmp.path().join("watch");
        let out = tmp.path().join("out");
        std::fs::create_dir_all(&watch).expect("create watch directory");

        let mut session =
            session_ledger::Session::new("nested/session", session_ledger::Corpus::Forge);
        session.messages.push(session_ledger::Message::new(session_ledger::Role::User, "ship it"));
        let transcript = serde_json::to_string(&session).expect("serialize session");
        std::fs::write(watch.join("session.jsonl"), format!("{transcript}\n"))
            .expect("write transcript");

        let written = crate::etl::transform_file(&watch.join("session.jsonl"), &out, None)
            .expect("daemon ETL should export OKF");
        assert_eq!(written.len(), 1);
        assert!(validate_on_disk_okf("nested/session", &out)
            .expect("validate daemon output")
            .is_empty());
    }

    #[test]
    fn format_timestamp_zero() {
        assert_eq!(format_timestamp(0), "00:00:00");
    }

    #[test]
    fn format_timestamp_one_hour_one_min_one_sec() {
        assert_eq!(format_timestamp(3661), "01:01:01");
    }

    #[test]
    fn truncate_short_string_unchanged() {
        assert_eq!(truncate("hello", 80), "hello");
    }

    #[test]
    fn truncate_long_string_ends_with_ellipsis() {
        let s = "a".repeat(100);
        let result = truncate(&s, 80);
        assert!(result.ends_with('\u{2026}'));
        assert_eq!(result.chars().count(), 80);
    }

    #[test]
    fn format_entity_line_produces_expected_format() {
        let entity = serde_json::json!({
            "type": "intent",
            "id": "intent-0",
            "label": "fix the pagination bug"
        });
        let line = format_entity_line(&entity, 0);
        assert!(line.starts_with("[00:00:00]"));
        assert!(line.contains("intent/intent-0"));
        assert!(line.contains("fix the pagination bug"));
    }

    #[test]
    fn format_entity_line_missing_fields_use_defaults() {
        let entity = serde_json::json!({});
        let line = format_entity_line(&entity, 5);
        assert!(line.starts_with("[00:00:05]"));
        assert!(line.contains("unknown/?"));
    }

    #[test]
    fn http_bind_parses_loopback_and_non_loopback_addresses() {
        assert!(parse_http_bind("127.0.0.1:8080").is_ok());
        assert!(parse_http_bind("[::1]:8080").is_ok());
        assert!(parse_http_bind("0.0.0.0:8080").is_ok());
        assert!(parse_http_bind("[::]:8080").is_ok());
        assert!(parse_http_bind("not-an-addr").is_err());
    }

    #[test]
    fn non_loopback_bind_requires_configured_api_key() {
        let loopback = parse_http_bind("127.0.0.1:8080").unwrap();
        let remote = parse_http_bind("0.0.0.0:8080").unwrap();
        let unset = http::ApiKeyAuth::from_value(None);
        let configured = http::ApiKeyAuth::from_value(Some("secret".into()));

        assert!(ensure_http_bind_auth(loopback, &unset).is_ok());
        assert!(ensure_http_bind_auth(loopback, &configured).is_ok());
        assert!(ensure_http_bind_auth(remote, &configured).is_ok());
        let err = ensure_http_bind_auth(remote, &unset).unwrap_err();
        assert!(err.contains("requires SL_API_KEY"));
    }
}
