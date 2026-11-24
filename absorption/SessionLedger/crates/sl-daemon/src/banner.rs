//! Lab-Coat ANSI startup banner for interactive `serve` launches.
//!
//! Colors map to `assets/tokens.css` Lab-Coat accents:
//! cobalt (#2563eb), teal (#14b8a6), orange (#f97316).

use std::io::{IsTerminal, Write};

const COBALT: &str = "\x1b[38;2;37;99;235m";
const TEAL: &str = "\x1b[38;2;20;184;166m";
const ORANGE: &str = "\x1b[38;2;249;115;22m";
const SLATE: &str = "\x1b[38;2;31;41;55m";
const RESET: &str = "\x1b[0m";

/// Plain-text banner for structured logs (`info!` targets).
pub fn plain_banner(version: &str) -> String {
    format!("SessionLedger sl-daemon {version} — session ingest → distill → OKF")
}

/// Emit a colored banner to stderr when attached to a TTY and JSON logs are off.
pub fn emit_interactive_banner(version: &str) {
    if !std::io::stderr().is_terminal() {
        return;
    }
    #[cfg(feature = "json-logs")]
    if std::env::var("SL_LOG_FORMAT").is_ok_and(|value| value.eq_ignore_ascii_case("json")) {
        return;
    }

    let banner = format!(
        "{COBALT}╔══════════════════════════════════════╗{RESET}\n\
         {COBALT}║{RESET} {TEAL}Session{ORANGE}Ledger{RESET} {SLATE}sl-daemon{RESET} {COBALT}v{version}{RESET} {COBALT}║{RESET}\n\
         {COBALT}║{RESET} {SLATE}session ingest → distill → OKF{RESET} {COBALT}║{RESET}\n\
         {COBALT}╚══════════════════════════════════════╝{RESET}\n"
    );
    let _ = std::io::stderr().write_all(banner.as_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plain_banner_includes_version() {
        let text = plain_banner("0.1.0-test");
        assert!(text.contains("0.1.0-test"));
        assert!(text.contains("SessionLedger"));
    }
}
