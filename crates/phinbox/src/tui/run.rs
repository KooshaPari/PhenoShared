//! TUI run loop entry point, plain-text fallback, and outcome helpers.

use std::io::stdout;
use std::path::Path;

use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

use super::event;
use super::state::{snapshot_inbox, TuiOutcome};

/// Run the TUI viewer to completion. Returns the outcome (quit / answered /
/// dismissed) or `TuiOutcome::NoTty` if the terminal refused raw mode.
pub fn run(inbox_root: &Path, follow: bool) -> Result<TuiOutcome, String> {
    let raw_ok = event::enter_raw_mode()?;
    if !raw_ok {
        return Ok(TuiOutcome::NoTty);
    }
    let backend = CrosstermBackend::new(stdout());
    let mut terminal = match Terminal::new(backend) {
        Ok(t) => t,
        Err(e) => {
            event::leave_raw_mode();
            return Err(format!("Terminal::new: {e}"));
        }
    };

    let watcher = if follow {
        Some(crate::inbox::change::InboxChangeBus::global().subscribe())
    } else {
        None
    };

    let result = event::run_loop(&mut terminal, inbox_root, watcher);
    event::leave_raw_mode();
    result
}

/// Plain-text fallback used when no TTY is available. Renders a numbered
/// list of pending requests to stdout so the user can still see what was
/// queued, and prints a hint to invoke `phinbox inbox --tui` on a TTY.
pub fn render_plain(inbox_root: &Path) -> Result<usize, String> {
    let entries = snapshot_inbox(inbox_root)?;
    let count = entries.len();
    println!("phinbox inbox (plain-text mode \u{2014} no TTY)");
    println!("hint: run `phinbox inbox --tui` on a terminal for the full UI");
    println!();
    if entries.is_empty() {
        println!("(no pending requests)");
        return Ok(count);
    }
    for (i, e) in entries.iter().enumerate() {
        println!(
            "  {:>3}. [{}] {:<14}  {:<40}  ({})",
            i + 1,
            e.state_badge,
            super::state::truncate(&e.request_id, 14),
            e.title,
            e.age_label
        );
    }
    println!();
    println!("open a request:  phinbox inbox --open --show <id>");
    Ok(count)
}

/// Build a `TuiOutcome::Answered` for the given `request_id` -- exposed so the
/// CLI can construct the outcome after an external answer step.
#[must_use]
pub fn outcome_answered(id: impl Into<String>) -> TuiOutcome {
    TuiOutcome::Answered(id.into())
}
