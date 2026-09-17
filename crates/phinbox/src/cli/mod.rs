//! CLI binary entry point and argument definitions.
//!
//! Subcommands are implemented in sibling modules (`ask`, `inbox`, `daemon`,
//! etc.) and dispatched from `main()`.

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};

use phinbox::options::RendererPreference;

mod answer;
mod ask;
mod common;
mod daemon;
mod inbox;
mod install;
mod open;
mod wait;

/// Native OS popup elicitation — render a modal dialog and read the user's
/// response as typed JSON.
#[derive(Debug, Parser)]
#[command(
    name = "phinbox",
    version,
    about = "Native OS popup elicitation for autonomous agents",
    long_about = "phinbox renders a native OS popup (NSAlert on macOS, Win32 form on Windows, \
                  zenity/kdialog/Tk/inquire on Linux) and returns the user's response as typed JSON. \
                  For non-blocking workflows, queue the prompt in the inbox via `--async` and use \
                  `phinbox wait --request-id <id>` to retrieve the answer later."
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,

    /// Increase verbosity (-v, -vv, -vvv).
    #[arg(short, long, action = clap::ArgAction::Count, global = true)]
    verbose: u8,

    /// Force a specific renderer.
    #[arg(long, global = true, value_enum)]
    renderer: Option<RendererArg>,

    /// Override the inbox data directory (also used for `install`).
    #[arg(long, global = true, env = "PHINBOX_INBOX_DIR")]
    inbox_dir: Option<PathBuf>,
}

#[derive(Debug, Clone, Copy, clap::ValueEnum)]
enum RendererArg {
    Auto,
    Gui,
    Tty,
}

impl From<RendererArg> for RendererPreference {
    fn from(r: RendererArg) -> Self {
        match r {
            RendererArg::Auto => RendererPreference::AutoGui,
            RendererArg::Gui => RendererPreference::ForceGui,
            RendererArg::Tty => RendererPreference::ForceTty,
        }
    }
}

#[derive(Debug, Subcommand)]
enum Cmd {
    /// Render a popup from CLI flags, --from-json, or --from-file.
    Ask(ask::AskArgs),
    /// Print the JSON Schema for `PromptSpec` (or `FieldSpec` / `ElicitResponse`).
    Schema(common::SchemaArgs),
    /// Detect platform + renderer kind.
    Detect,
    /// Render a built-in test popup (used for CI smoke).
    Smoke(common::SmokeArgs),
    /// Install phinbox globally + enable auto-launch helper.
    Install(install::InstallArgs),
    /// Remove the binaries and launcher registration installed by `install`.
    Uninstall(install::UninstallArgs),
    /// Run the inbox daemon in the foreground (server mode).
    Daemon(daemon::DaemonArgs),
    /// Inspect the inbox: list pending, show one in detail, or open the UI.
    Inbox(inbox::InboxArgs),
    /// Open the inbox in the default browser.
    Open(open::OpenArgs),
    /// Block until a queued `--async` request has been answered (or times out).
    Wait(wait::WaitArgs),
    /// Submit an answer to a queued inbox request via the CLI (no UI).
    Answer(answer::AnswerArgs),
    /// Alias: run the MCP stdio server.
    Serve,
    /// Print version + license info.
    Version,
}

pub fn main() -> ExitCode {
    let cli = Cli::parse();
    common::init_tracing(cli.verbose);

    let renderer = cli.renderer.map(std::convert::Into::into);
    let inbox_dir = cli
        .inbox_dir
        .clone()
        .unwrap_or_else(phinbox::inbox::default_inbox_root);

    let result = match cli.cmd {
        Cmd::Ask(args) => ask::cmd_ask(args, renderer, &inbox_dir),
        Cmd::Schema(args) => {
            common::cmd_schema(args);
            Ok(())
        },
        Cmd::Detect => {
            common::cmd_detect();
            Ok(())
        },
        Cmd::Smoke(args) => common::cmd_smoke(args, renderer),
        Cmd::Install(args) => install::cmd_install(args, &inbox_dir),
        Cmd::Uninstall(args) => install::cmd_uninstall(args, &inbox_dir),
        Cmd::Daemon(args) => daemon::cmd_daemon(args, &inbox_dir),
        Cmd::Inbox(args) => inbox::cmd_inbox(args, &inbox_dir),
        Cmd::Open(args) => open::cmd_open(args, &inbox_dir),
        Cmd::Wait(args) => wait::cmd_wait(args, &inbox_dir),
        Cmd::Answer(args) => answer::cmd_answer(args, &inbox_dir),
        Cmd::Serve => {
            eprintln!("error: 'serve' is provided by the `phinbox-mcp` binary, not `phinbox`. Run `phinbox-mcp` instead.");
            return ExitCode::from(2);
        }
        Cmd::Version => {
            println!("phinbox {}", env!("CARGO_PKG_VERSION"));
            println!("license: MIT");
            println!("repository: https://github.com/KooshaPari/phenotype-tooling");
            return ExitCode::SUCCESS;
        }
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn open_url_from_handle(h: &phinbox::inbox::daemon::DaemonHandle) -> String {
    format!("http://{}:{}/inbox", h.bind_addr, h.port)
}

// ---- tests ----------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn parse_help() {
        assert!(Cli::try_parse_from(["phinbox", "--help"]).is_err());
    }

    #[test]
    fn parse_schema_subcommand() {
        let cli = Cli::try_parse_from(["phinbox", "schema"]).unwrap();
        assert!(matches!(cli.cmd, Cmd::Schema(_)));
    }

    #[test]
    fn parse_detect_subcommand() {
        let cli = Cli::try_parse_from(["phinbox", "detect"]).unwrap();
        assert!(matches!(cli.cmd, Cmd::Detect));
    }

    #[test]
    fn parse_ask_with_from_json() {
        let json = r#"{"title":"t","question":"q","field":{"kind":"boolean","label":"?","default":true}}"#;
        let cli = Cli::try_parse_from(["phinbox", "ask", "--from-json", json]).unwrap();
        assert!(matches!(cli.cmd, Cmd::Ask(_)));
    }

    #[test]
    fn parse_ask_async() {
        let json = r#"{"title":"t","question":"q","field":{"kind":"boolean","label":"?","default":true}}"#;
        let cli =
            Cli::try_parse_from(["phinbox", "ask", "--async", "--from-json", json]).unwrap();
        if let Cmd::Ask(a) = cli.cmd {
            assert!(a.r#async);
        } else {
            panic!("expected Ask");
        }
    }

    #[test]
    fn parse_ask_requires_either_flags_or_json() {
        let cli = Cli::try_parse_from(["phinbox", "ask"]);
        assert!(cli.is_ok());
    }

    #[test]
    fn parse_install() {
        let cli = Cli::try_parse_from(["phinbox", "install", "--dry-run"]).unwrap();
        assert!(matches!(cli.cmd, Cmd::Install(_)));
    }

    #[test]
    fn parse_wait() {
        let cli =
            Cli::try_parse_from(["phinbox", "wait", "--request-id", "abc"]).unwrap();
        if let Cmd::Wait(w) = cli.cmd {
            assert_eq!(w.request_id, "abc");
        } else {
            panic!("expected Wait");
        }
    }

    #[test]
    fn parse_answer_bool() {
        let cli = Cli::try_parse_from([
            "phinbox",
            "answer",
            "--request-id",
            "abc",
            "--boolean",
            "true",
        ])
        .unwrap();
        if let Cmd::Answer(a) = cli.cmd {
            assert_eq!(a.boolean, Some(true));
        } else {
            panic!("expected Answer");
        }
    }
}
