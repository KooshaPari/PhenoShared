//! TUI rendering logic — builds ratatui widgets from `ViewerState`.

use std::path::Path;

use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph};
use ratatui::Terminal;

use crate::inbox::{load as inbox_load, RequestOrigin};
use crate::spec::{FieldSpec, PromptSpec};

use super::state::ViewerState;
use super::state::truncate;

/// Build the lines that should appear in the detail pane for a given request.
pub(crate) fn render_detail_lines(
    spec: &PromptSpec,
    origin: &RequestOrigin,
) -> Vec<Line<'static>> {
    let mut out: Vec<Line<'static>> = Vec::new();
    out.push(Line::from(vec![
        Span::styled("title    ", Style::default().fg(Color::DarkGray)),
        Span::raw(spec.title.clone()),
    ]));
    out.push(Line::from(vec![
        Span::styled("question ", Style::default().fg(Color::DarkGray)),
        Span::raw(spec.question.clone()),
    ]));
    out.push(Line::from(vec![
        Span::styled("urgency  ", Style::default().fg(Color::DarkGray)),
        Span::raw(format!("{:?}", spec.urgency)),
    ]));
    out.push(Line::from(vec![
        Span::styled("ttl      ", Style::default().fg(Color::DarkGray)),
        Span::raw(if spec.timeout_secs == 0 {
            "none".to_string()
        } else {
            format!("{}s", spec.timeout_secs)
        }),
    ]));
    out.push(Line::from(vec![
        Span::styled("field    ", Style::default().fg(Color::DarkGray)),
        Span::raw(field_summary(&spec.field)),
    ]));
    out.push(Line::from(vec![
        Span::styled("notes    ", Style::default().fg(Color::DarkGray)),
        Span::raw(if spec.notes.is_some() {
            "(yes)"
        } else {
            "(no)"
        }),
    ]));
    out.push(Line::from(vec![
        Span::styled("origin   ", Style::default().fg(Color::DarkGray)),
        Span::raw(format!(
            "{}@{} (pid {})",
            origin.process, origin.hostname, origin.pid
        )),
    ]));
    out
}

/// Map `FieldSpec` to a short human-readable summary (e.g. "boolean — Ready?").
pub(crate) fn field_summary(field: &FieldSpec) -> String {
    match field {
        FieldSpec::Text {
            label,
            secret,
            pattern,
            ..
        } => {
            let kind = if *secret {
                "secret"
            } else {
                pattern.as_ref().map_or("text", |_| "text (pattern)")
            };
            format!("{kind} — {label}")
        }
        FieldSpec::LongText { label, .. } => format!("long text — {label}"),
        FieldSpec::Integer {
            label,
            min,
            max,
            ..
        } => {
            let range = match (min, max) {
                (Some(a), Some(b)) => format!(" [{a}..{b}]"),
                (Some(a), None) => format!(" [>={a}]"),
                (None, Some(b)) => format!(" [<={b}]"),
                (None, None) => String::new(),
            };
            format!("integer{range} — {label}")
        }
        FieldSpec::Choice { label, options, .. } => {
            let labels: Vec<&str> = options.iter().map(|o| o.label.as_str()).collect();
            format!("choice [{}] — {label}", labels.join(", "))
        }
        FieldSpec::Boolean { label, default } => {
            let def = default.map_or(String::new(), |d| {
                format!(" (default {})", if d { "yes" } else { "no" })
            });
            format!("boolean — {label}{def}")
        }
        FieldSpec::DateTime {
            label,
            picker_kind,
            ..
        } => format!("{picker_kind:?} — {label}"),
    }
}

/// Build the status bar paragraph.
pub(crate) fn render_status_bar(state: &ViewerState) -> Paragraph<'_> {
    let pending = state
        .entries
        .iter()
        .filter(|e| !e.is_terminal)
        .count();
    let total = state.entries.len();
    let msg = format!(" {} pending · {} total · {}", pending, total, state.status_message);
    Paragraph::new(msg).style(
        Style::default()
            .fg(Color::White)
            .bg(Color::DarkGray),
    )
}

/// Build the list pane widget and its state.
pub(crate) fn render_list_pane(state: &ViewerState) -> (List<'_>, ListState) {
    let items: Vec<ListItem> = state
        .entries
        .iter()
        .enumerate()
        .map(|(i, e)| {
            let selected = i == state.selected && state.focus_on_list;
            let style = if selected {
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD)
            } else if e.is_terminal {
                Style::default().fg(Color::DarkGray)
            } else {
                Style::default()
            };
            let marker = if selected { "▶" } else { " " };
            let line = Line::from(vec![
                Span::styled(format!("{marker} "), style),
                Span::styled(
                    truncate(&e.request_id, 14),
                    style,
                ),
                Span::styled(
                    format!(" ({})", e.age_label),
                    style.fg(Color::DarkGray),
                ),
                Span::styled(
                    format!("  {:<40}", truncate(&e.title, 40)),
                    style,
                ),
                Span::styled(
                    format!("{} {}", e.state_badge, e.urgency_label),
                    style,
                ),
            ]);
            ListItem::new(line)
        })
        .collect();

    let list = List::new(items).block(
        Block::default()
            .title(" inbox ")
            .borders(Borders::ALL)
            .border_style(Style::default().fg(Color::DarkGray)),
    );

    let mut list_state = ListState::default();
    if state.focus_on_list {
        list_state.select(Some(state.selected));
    }
    (list, list_state)
}

/// Build the detail pane for the currently selected request.
pub(crate) fn render_detail_pane(
    state: &ViewerState,
    inbox_root: &Path,
) -> (Paragraph<'static>, bool) {
    let Some(entry) = state.selected_entry() else {
        return (
            Paragraph::new("(no selection)").block(
                Block::default()
                    .title(" detail ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(Color::DarkGray)),
            ),
            false,
        );
    };

    match inbox_load(inbox_root, &entry.request_id) {
        Ok(req) => {
            let lines = render_detail_lines(&req.spec, &req.origin);
            let block = Block::default()
                .title(format!(" {} ", truncate(&entry.title, 50)))
                .borders(Borders::ALL)
                .border_style(Style::default().fg(if state.focus_on_list {
                    Color::DarkGray
                } else {
                    Color::Cyan
                }));
            (Paragraph::new(lines).block(block), false)
        }
        Err(e) => (
            Paragraph::new(format!("error loading request: {e}")).block(
                Block::default()
                    .title(" detail ")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(Color::Red)),
            ),
            false,
        ),
    }
}

/// Build the help line at the bottom.
pub(crate) fn render_help_line() -> Paragraph<'static> {
    Paragraph::new(" [a] answer · [o] open · [d] dismiss · [Tab] focus · [j/k] navigate · [q] quit")
        .style(Style::default().fg(Color::DarkGray))
}

/// Render the current state to the terminal.
pub(crate) fn render(
    terminal: &mut Terminal<CrosstermBackend<std::io::Stdout>>,
    state: &ViewerState,
    inbox_root: &Path,
) -> Result<(), String> {
    terminal
        .draw(|f| {
            let chunks = Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Min(3),
                    Constraint::Length(1),
                    Constraint::Length(1),
                ])
                .split(f.area());
            let (list, mut list_state) = render_list_pane(state);
            f.render_stateful_widget(list, chunks[0], &mut list_state);
            let (detail, _) = render_detail_pane(state, inbox_root);
            f.render_widget(detail, chunks[1]);
            f.render_widget(render_help_line(), chunks[1]);
            f.render_widget(render_status_bar(state), chunks[2]);
        })
        .map_err(|e| format!("terminal.draw: {e}"))?;
    Ok(())
}
