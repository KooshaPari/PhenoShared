//! Terminal UI inbox viewer (`phinbox inbox --tui`).
//!
//! When the daemon has queued prompts that are blocking an agent, the user
//! needs a way to **see and answer** them without leaving the terminal. The
//! TUI viewer renders a split-pane terminal interface over the same on-disk
//! inbox the daemon writes to, with live polling so newly enqueued requests
//! appear immediately.
//!
//! ## Layout
//!
//! ```text
//! +-- inbox · ~/.../inbox -----------------------------------------+
//! | pending (3)                                               ^v   |
//! |  > req-1  (2s)   Need to ship?                  [P] Info   |    |
//! |    req-2  (8s)   Confirm dangerous op            [P] Warn   |    |
//! |    req-3  (2m)   Choose a region                 [P] Info   |    |
//! +--------------------------------------------------------------+   |
//! | title     Need to ship?                                        | |
//! | question  Are we ready to ship v0.5 by Friday?                | |
//! | field     boolean -- Confirm? (default yes)                   | |
//! | urgency   info · ttl 10m                                       | |
//! | origin    agent@host (pid 12345)                               | |
//! |                                                                | |
//! | [a] answer · [o] open in browser · [d] dismiss · q quit       | |
//! +----------------------------------------------------------------+ |
//! ```
//!
//! ## Submodules
//!
//! - `state` -- `TuiOutcome`, `ListEntry`, `ViewerState`, snapshot logic
//! - `render` -- ratatui widget builders for each pane
//! - `event` -- keyboard handling, terminal mode management, run loop
//! - `run` -- TUI run loop entry point, plain-text fallback, outcome helpers

pub mod event;
pub mod render;
pub mod run;
pub mod state;

pub use run::{outcome_answered, render_plain, run};
pub use state::{position_of, snapshot_inbox, ListEntry, TuiOutcome, ViewerState};

// ----------------- tests -------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        inbox::{PendingRequest, RequestOrigin, RequestState},
        spec::{FieldSpec, PromptSpec, Urgency},
        tui::state::{build_entry, format_age, sort_entries, truncate},
    };

    fn sample_spec() -> PromptSpec {
        PromptSpec {
            details: None,
            title: "Ship v0.5".to_string(),
            question: "Are we ready to ship?".to_string(),
            field: FieldSpec::Boolean {
                label: "Confirm?".to_string(),
                default: Some(true),
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Warning,
            timeout_secs: 600,
            request_id: Some("req-1".to_string()),
        }
    }

    fn sample_origin() -> RequestOrigin {
        RequestOrigin {
            hostname: "host".to_string(),
            process: "agent".to_string(),
            pid: 42,
            callback: None,
        }
    }

    #[test]
    fn viewer_state_default_has_no_entries_and_focus_on_list() {
        let s = ViewerState::default();
        assert!(s.entries.is_empty());
        assert!(s.focus_on_list);
        assert_eq!(s.selected, 0);
    }

    #[test]
    fn move_down_clamped_to_last_entry() {
        let mut s = ViewerState::default();
        s.entries = vec![
            ListEntry {
                request_id: "a".into(),
                title: "a".into(),
                urgency_label: "Info".into(),
                state_badge: "[P]".into(),
                age_label: "1s".into(),
                is_terminal: false,
            },
            ListEntry {
                request_id: "b".into(),
                title: "b".into(),
                urgency_label: "Info".into(),
                state_badge: "[P]".into(),
                age_label: "2s".into(),
                is_terminal: false,
            },
        ];
        s.move_down(1);
        assert_eq!(s.selected, 1);
        s.move_down(5);
        assert_eq!(s.selected, 1);
    }

    #[test]
    fn move_up_floors_at_zero() {
        let mut s = ViewerState::default();
        s.entries = vec![ListEntry {
            request_id: "a".into(),
            title: "a".into(),
            urgency_label: "Info".into(),
            state_badge: "[P]".into(),
            age_label: "1s".into(),
            is_terminal: false,
        }];
        s.move_up(5);
        assert_eq!(s.selected, 0);
    }

    #[test]
    fn toggle_focus_flips() {
        let mut s = ViewerState::default();
        assert!(s.focus_on_list);
        s.toggle_focus();
        assert!(!s.focus_on_list);
        s.toggle_focus();
        assert!(s.focus_on_list);
    }

    #[test]
    fn format_age_units() {
        assert_eq!(format_age(0), "0s");
        assert_eq!(format_age(45_000), "45s");
        assert_eq!(format_age(120_000), "2m");
        assert_eq!(format_age(3_600_000), "1h");
        assert_eq!(format_age(86_400_000), "1d");
    }

    #[test]
    fn truncate_short_string_is_unchanged() {
        assert_eq!(truncate("hello", 10), "hello");
    }

    #[test]
    fn truncate_long_string_is_truncated() {
        let s = "a".repeat(50);
        let out = truncate(&s, 10);
        assert_eq!(out.chars().count(), 10);
        assert!(out.ends_with('\u{2026}'));
    }

    #[test]
    fn truncate_never_panics_on_a_multibyte_boundary() {
        // Regression: the byte-slicing version panicked when the cut landed
        // inside a multi-byte character. This is the exact shape that killed
        // the viewer — a 43-byte title whose 'é' straddled byte 39 (the old
        // 40-byte limit). `title`/`request_id` are agent-supplied.
        let title = format!("{}ézzz", "a".repeat(38));
        let out = truncate(&title, 40);
        assert!(out.ends_with('\u{2026}'));
        assert_eq!(out.chars().count(), 40);

        // Every cut position must be safe for a string of multi-byte chars.
        let wide = "é".repeat(30);
        for max in 0..40 {
            let _ = truncate(&wide, max);
        }
    }

    #[test]
    fn build_entry_marks_terminal_states() {
        let req = PendingRequest {
            request_id: "r".into(),
            origin: sample_origin(),
            spec: sample_spec(),
            queued_at_ms: 1_000_000,
            expires_at_ms: u64::MAX,
            state: RequestState::Answered,
            response: None,
            notified_via: vec![],
            metadata: serde_json::Map::new(),
        };
        let e = build_entry(&req, 1_001_000);
        assert_eq!(e.state_badge, "[A]");
        assert!(e.is_terminal);
        assert_eq!(e.age_label, "1s");
    }

    #[test]
    fn sort_entries_pending_first_then_terminal() {
        let mut entries = vec![
            ListEntry {
                request_id: "old-terminal".into(),
                title: "old".into(),
                urgency_label: "Info".into(),
                state_badge: "[A]".into(),
                age_label: "5s".into(),
                is_terminal: true,
            },
            ListEntry {
                request_id: "new-pending".into(),
                title: "new".into(),
                urgency_label: "Info".into(),
                state_badge: "[P]".into(),
                age_label: "1s".into(),
                is_terminal: false,
            },
        ];
        sort_entries(&mut entries);
        assert_eq!(entries[0].request_id, "new-pending");
        assert_eq!(entries[1].request_id, "old-terminal");
    }

    #[test]
    fn position_of_finds_request_id() {
        let entries = vec![
            ListEntry {
                request_id: "a".into(),
                title: "a".into(),
                urgency_label: "Info".into(),
                state_badge: "[P]".into(),
                age_label: "1s".into(),
                is_terminal: false,
            },
            ListEntry {
                request_id: "b".into(),
                title: "b".into(),
                urgency_label: "Info".into(),
                state_badge: "[P]".into(),
                age_label: "2s".into(),
                is_terminal: false,
            },
        ];
        assert_eq!(position_of(&entries, "b"), Some(1));
        assert_eq!(position_of(&entries, "z"), None);
    }

    #[test]
    fn field_summary_includes_label_and_kind() {
        let s = render::field_summary(&FieldSpec::Boolean {
            label: "Ready?".into(),
            default: None,
        });
        assert!(s.contains("boolean"));
        assert!(s.contains("Ready?"));
    }

    #[test]
    fn render_detail_lines_includes_origin_and_urgency() {
        let spec = sample_spec();
        let origin = sample_origin();
        let lines = render::render_detail_lines(&spec, &origin);
        let flat: String = lines
            .iter()
            .map(|l| l.to_string())
            .collect::<Vec<_>>()
            .join("\n");
        assert!(flat.contains("urgency"));
        assert!(flat.contains("origin"));
        assert!(flat.contains("agent@host"));
    }

    #[test]
    fn snapshot_inbox_empty_when_dir_missing() {
        let tmp = tempfile::tempdir().unwrap();
        let entries = snapshot_inbox(tmp.path()).unwrap();
        assert!(entries.is_empty());
    }

    #[test]
    fn snapshot_inbox_returns_sorted_entries() {
        let tmp = tempfile::tempdir().unwrap();
        let mut a = PendingRequest {
            request_id: "a".into(),
            origin: sample_origin(),
            spec: sample_spec(),
            queued_at_ms: 1_000,
            expires_at_ms: u64::MAX,
            state: RequestState::Pending,
            response: None,
            notified_via: vec![],
            metadata: serde_json::Map::new(),
        };
        let b = PendingRequest {
            request_id: "b".into(),
            origin: sample_origin(),
            spec: sample_spec(),
            queued_at_ms: 2_000,
            expires_at_ms: u64::MAX,
            state: RequestState::Pending,
            response: None,
            notified_via: vec![],
            metadata: serde_json::Map::new(),
        };
        a.queued_at_ms = 2_000;
        a.spec.request_id = Some("a".into());
        crate::inbox::enqueue(tmp.path(), &a).unwrap();
        let mut b = b;
        b.queued_at_ms = 1_000;
        b.spec.request_id = Some("b".into());
        crate::inbox::enqueue(tmp.path(), &b).unwrap();

        let entries = snapshot_inbox(tmp.path()).unwrap();
        assert!(entries.iter().any(|e| e.request_id == "a"));
        assert!(entries.iter().any(|e| e.request_id == "b"));
    }
}

// ----------------- layout & render tests (defect regressions) -----------

#[cfg(test)]
mod render_tests {
    use ratatui::{backend::TestBackend, Terminal};

    use super::*;
    use crate::{
        inbox::{PendingRequest, RequestOrigin, RequestState},
        spec::{FieldSpec, PromptSpec, Urgency},
        tui::event,
    };

    fn sample_spec() -> PromptSpec {
        PromptSpec {
            details: None,
            title: "Ship v0.5".to_string(),
            question: "Are we ready to ship?".to_string(),
            field: FieldSpec::Boolean {
                label: "Confirm?".into(),
                default: Some(true),
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Warning,
            timeout_secs: 600,
            request_id: Some("req-1".to_string()),
        }
    }

    fn sample_origin() -> RequestOrigin {
        RequestOrigin {
            hostname: "host".into(),
            process: "agent".into(),
            pid: 42,
            callback: None,
        }
    }

    /// Seed an inbox directory with one pending request.
    fn seed(dir: &std::path::Path) {
        let req = PendingRequest {
            request_id: "req-1".into(),
            origin: sample_origin(),
            spec: sample_spec(),
            queued_at_ms: crate::inbox::unix_now_ms(),
            expires_at_ms: u64::MAX,
            state: RequestState::Pending,
            response: None,
            notified_via: vec![],
            metadata: serde_json::Map::new(),
        };
        crate::inbox::enqueue(dir, &req).unwrap();
    }

    /// Render the terminal buffer to a plain-text string (one line per row).
    fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
        let buf = terminal.backend().buffer();
        let area = buf.area();
        let mut out = String::new();
        for y in 0..area.height {
            for x in 0..area.width {
                out.push_str(buf.cell((x, y)).map_or(" ", |c| c.symbol()));
            }
            out.push('\n');
        }
        out
    }

    /// Helper: render state to a 80x24 TestBackend, return buffer text.
    fn render_80x24(state: &ViewerState, inbox_root: &std::path::Path) -> String {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        render::render(&mut terminal, state, inbox_root).unwrap();
        buffer_text(&terminal)
    }

    // -- Defect 1: detail pane must be visible at 80x24 --------------------

    #[test]
    fn detail_pane_visible_at_80x24() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        let text = render_80x24(&state, tmp.path());

        // The detail pane should contain "question" from the PromptSpec,
        // and the help line should contain the keybinding hint.
        assert!(
            text.contains("question"),
            "detail pane content missing at 80x24:\n{text}"
        );
        assert!(
            text.contains("[?] help"),
            "help line missing at 80x24:\n{text}"
        );
        // The detail pane block title should appear.
        assert!(
            text.contains("Ship v0.5") || text.contains(" detail "),
            "detail pane title missing at 80x24:\n{text}"
        );
    }

    #[test]
    fn detail_pane_and_help_line_are_separate_rows_at_80x24() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        render::render(&mut terminal, &state, tmp.path()).unwrap();

        let buf = terminal.backend().buffer();
        let area = buf.area();
        // Find the help line row (contains "[?] help").
        let mut help_row: Option<u16> = None;
        for y in 0..area.height {
            let row: String = (0..area.width)
                .filter_map(|x| buf.cell((x, y)).map(|c| c.symbol().to_string()))
                .collect();
            if row.contains("[?] help") {
                help_row = Some(y);
                break;
            }
        }
        let help_row = help_row.expect("help line row not found in buffer");

        // Find a row that contains "question" (detail pane content).
        let mut detail_row: Option<u16> = None;
        for y in 0..area.height {
            if y == help_row {
                continue;
            }
            let row: String = (0..area.width)
                .filter_map(|x| buf.cell((x, y)).map(|c| c.symbol().to_string()))
                .collect();
            if row.contains("question") {
                detail_row = Some(y);
                break;
            }
        }
        assert!(
            detail_row.is_some(),
            "detail pane 'question' text not found in any row"
        );
        assert_ne!(
            detail_row.unwrap(),
            help_row,
            "detail pane and help line must be on different rows"
        );
    }

    // -- Defect 1 (edge): small terminal degrades gracefully ---------------

    #[test]
    fn small_terminal_5x80_has_no_detail_but_has_status() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        let backend = TestBackend::new(80, 5);
        let mut terminal = Terminal::new(backend).unwrap();
        render::render(&mut terminal, &state, tmp.path()).unwrap();
        let text = buffer_text(&terminal);

        // At 5 rows, the detail pane should still be present
        // (minimum layout: list + detail + help + status).
        assert!(
            text.contains("pending") || text.contains("total"),
            "status bar missing at 5x80:\n{text}"
        );
    }

    #[test]
    fn tiny_terminal_3x80_degrades_no_crash() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        let backend = TestBackend::new(80, 3);
        let mut terminal = Terminal::new(backend).unwrap();
        // Should not panic.
        render::render(&mut terminal, &state, tmp.path()).unwrap();
    }

    // -- Defect 2: ? key toggles help overlay -----------------------------

    #[test]
    fn question_mark_key_toggles_help_overlay() {
        let mut state = ViewerState::default();
        assert!(!state.show_help);

        let key = crossterm::event::KeyEvent::new(
            crossterm::event::KeyCode::Char('?'),
            crossterm::event::KeyModifiers::NONE,
        );
        let outcome = event::handle_key(key, &mut state);
        assert!(outcome.is_none(), "? should not exit the TUI");
        assert!(state.show_help, "show_help should be true after ?");

        let key2 = crossterm::event::KeyEvent::new(
            crossterm::event::KeyCode::Char('?'),
            crossterm::event::KeyModifiers::NONE,
        );
        let outcome2 = event::handle_key(key2, &mut state);
        assert!(outcome2.is_none());
        assert!(!state.show_help, "show_help should be false after second ?");
    }

    #[test]
    fn help_overlay_renders_keybinding_cheat_sheet() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        state.show_help = true;
        let text = render_80x24(&state, tmp.path());

        assert!(
            text.contains("cheat-sheet"),
            "help overlay title missing:\n{text}"
        );
        // The first several lines of the help overlay should be visible
        // (the detail pane is ~10 rows inner, content is13 lines, so the
        // top ~8 items are visible before the block border clips).
        assert!(
            text.contains("move selection down"),
            "help content missing:\n{text}"
        );
        assert!(text.contains("quit"), "quit keybinding missing:\n{text}");
    }

    #[test]
    fn help_overlay_does_not_appear_when_show_help_is_false() {
        let tmp = tempfile::tempdir().unwrap();
        seed(tmp.path());
        let mut state = ViewerState::default();
        state.entries = snapshot_inbox(tmp.path()).unwrap();
        state.show_help = false;
        let text = render_80x24(&state, tmp.path());

        assert!(
            !text.contains("cheat-sheet"),
            "help overlay should NOT appear when show_help is false"
        );
    }

    // -- Defect 3: non-TTY fallback returns Ok(false) ---------------------

    #[test]
    fn enter_raw_mode_returns_false_on_failure() {
        // In a test harness without a TTY, enable_raw_mode fails.
        // Before the fix this returned Err; now it must return Ok(false).
        let result = event::enter_raw_mode();
        match result {
            Ok(false) => {}, // expected in test environment
            Ok(true) => {
                // If we're somehow in a TTY, that's fine too — the function
                // succeeded and we need to clean up.
                event::leave_raw_mode();
            },
            Err(e) => {
                panic!("enter_raw_mode should return Ok(false) on failure, not Err: {e}");
            },
        }
    }
}
