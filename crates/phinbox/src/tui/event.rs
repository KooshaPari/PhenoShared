//! TUI event handling and terminal mode management.

use std::io::{stdout, Write};
use std::path::Path;
use std::time::{Duration, Instant};

use crossterm::event::{
    self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEvent, KeyEventKind,
    KeyModifiers,
};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

use crate::inbox::change::InboxWatcher;

use super::state::{snapshot_inbox, ViewerState, TuiOutcome, POLL_INTERVAL};

/// Try to set the terminal into raw mode. On failure (e.g. CI without TTY),
/// we return `Ok(false)` so the caller can render a plain-text fallback.
pub(crate) fn enter_raw_mode() -> Result<bool, String> {
    enable_raw_mode().map_err(|e| format!("enable_raw_mode: {e}"))?;
    let mut out = stdout();
    if execute!(out, EnterAlternateScreen, EnableMouseCapture).is_err() {
        let _ = disable_raw_mode();
        return Ok(false);
    }
    Ok(true)
}

/// Restore the terminal to its normal mode.
pub(crate) fn leave_raw_mode() {
    let mut out = stdout();
    let _ = execute!(out, LeaveAlternateScreen, DisableMouseCapture);
    let _ = disable_raw_mode();
}

/// Handle a single key event, returning an outcome if the TUI should exit.
pub(crate) fn handle_key(key: KeyEvent, state: &mut ViewerState) -> Option<TuiOutcome> {
    // Ignore key release events (some terminals emit press+release).
    if key.kind != KeyEventKind::Press {
        return None;
    }
    match key.code {
        KeyCode::Char('q') | KeyCode::Esc => Some(TuiOutcome::Quit),
        KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => {
            Some(TuiOutcome::Quit)
        }
        KeyCode::Char('j') | KeyCode::Down => {
            state.move_down(1);
            None
        }
        KeyCode::Char('k') | KeyCode::Up => {
            state.move_up(1);
            None
        }
        KeyCode::Char('g') => {
            state.jump_top();
            None
        }
        KeyCode::Char('G') => {
            state.jump_bottom();
            None
        }
        KeyCode::Tab => {
            state.toggle_focus();
            None
        }
        KeyCode::Char('a' | 'd') => {
            // Answer / Dismiss — pop the selected entry and record the ID.
            let entry = state.selected_entry()?.clone();
            let id = entry.request_id.clone();
            if key.code == KeyCode::Char('a') {
                Some(TuiOutcome::Answered(id))
            } else {
                Some(TuiOutcome::Dismissed(id))
            }
        }
        KeyCode::Char('o') | KeyCode::Enter => {
            // Open in browser — fire-and-forget.
            if let Some(entry) = state.selected_entry() {
                let url = format!(
                    "http://127.0.0.1:7117/inbox/{}",
                    entry.request_id
                );
                let _ = crate::inbox::daemon::notifier::open_in_default_browser(&url);
            }
            None
        }
        KeyCode::Char('r') | KeyCode::F(5) => {
            // Force refresh is implicit — the next poll cycle will pick up changes.
            state.status_message = "refreshed".into();
            None
        }
        _ => None,
    }
}

/// Run the main TUI event loop.
pub(crate) fn run_loop(
    terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>,
    inbox_root: &Path,
    watcher: Option<InboxWatcher>,
) -> Result<TuiOutcome, String> {
    let mut state = ViewerState::default();
    let mut last_poll = Instant::now().checked_sub(POLL_INTERVAL).unwrap();
    let mut last_change_gen = 0u64;
    let mut stdout_handle = stdout();

    loop {
        let elapsed_ok = last_poll.elapsed() >= POLL_INTERVAL;
        let changed = watcher.as_ref().is_some_and(|w| {
            let gen = w.last_seen();
            let has = gen != last_change_gen;
            if has {
                last_change_gen = gen;
            }
            has
        });

        if elapsed_ok || changed {
            match snapshot_inbox(inbox_root) {
                Ok(entries) => {
                    if entries.len() != state.entries.len() {
                        state.status_message =
                            format!("refreshed · {} pending", entries.len());
                    }
                    state.entries = entries;
                    if state.selected >= state.entries.len() {
                        state.jump_bottom();
                    }
                }
                Err(e) => {
                    state.status_message = format!("poll error: {e}");
                }
            }
            last_poll = Instant::now();
        }

        super::render::render(terminal, &state, inbox_root)?;
        stdout_handle.flush().ok();

        if event::poll(Duration::from_millis(200))
            .map_err(|e| format!("event::poll: {e}"))?
        {
            match event::read().map_err(|e| format!("event::read: {e}"))? {
                Event::Key(key) => {
                    if let Some(outcome) = handle_key(key, &mut state) {
                        return Ok(outcome);
                    }
                }
                Event::Resize(_, _) => {}
                _ => {}
            }
        }
    }
}
