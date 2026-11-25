//! helios-tui — minimal ratatui-based terminal UI scaffold for Helios CLI.
//!
//! Provides a [`Tui`] struct that renders a chat view, status bar, and input area.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};
use std::io;
use thiserror::Error;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum TuiError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    #[error("event read cancelled")]
    Cancelled,
}

// ---------------------------------------------------------------------------
// Chat message
// ---------------------------------------------------------------------------

/// A single message in the chat history.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChatMessage {
    pub role: Role,
    pub text: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    User,
    Assistant,
    System,
}

impl Role {
    pub fn label(self) -> &'static str {
        match self {
            Role::User => "You",
            Role::Assistant => "Helios",
            Role::System => "System",
        }
    }
}

// ---------------------------------------------------------------------------
// Tui
// ---------------------------------------------------------------------------

/// Top-level TUI state holder.
pub struct Tui {
    /// Chat history displayed in the scrollable area.
    messages: Vec<ChatMessage>,
    /// Current input buffer (user is typing).
    input: String,
    /// Whether the TUI should keep running.
    running: bool,
    /// Status message shown in the bottom bar.
    status: String,
}

impl Tui {
    /// Create a new [`Tui`] instance with an empty chat and default status.
    pub fn new() -> Self {
        Self { messages: Vec::new(), input: String::new(), running: true, status: "Ready".into() }
    }

    /// Push a new message into the chat history.
    pub fn push_message(&mut self, msg: ChatMessage) {
        self.messages.push(msg);
    }

    /// Replace the status bar text.
    pub fn set_status(&mut self, s: impl Into<String>) {
        self.status = s.into();
    }

    /// Return `false` once the user has signalled they want to quit.
    pub fn is_running(&self) -> bool {
        self.running
    }

    // -- rendering ----------------------------------------------------------

    /// Render the full UI into the given frame.
    pub fn draw(&self, frame: &mut Frame) {
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Min(3),    // chat view (flexible)
                Constraint::Length(1), // status bar
                Constraint::Length(3), // input area
            ])
            .split(frame.area());

        self.render_chat(frame, chunks[0]);
        self.render_status_bar(frame, chunks[1]);
        self.render_input_area(frame, chunks[2]);
    }

    /// Render the scrollable chat view.
    fn render_chat(&self, frame: &mut Frame, area: Rect) {
        let lines: Vec<Line> = self
            .messages
            .iter()
            .map(|m| {
                let role_style = match m.role {
                    Role::User => Style::default().fg(Color::Cyan),
                    Role::Assistant => Style::default().fg(Color::Green),
                    Role::System => Style::default().fg(Color::Yellow),
                };
                Line::from(vec![
                    Span::styled(format!("[{}] ", m.role.label()), role_style),
                    Span::raw(&m.text),
                ])
            })
            .collect();

        let paragraph = Paragraph::new(lines).block(
            Block::default()
                .title(" Chat ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::DarkGray)),
        );
        frame.render_widget(paragraph, area);
    }

    /// Render the bottom status bar.
    fn render_status_bar(&self, frame: &mut Frame, area: Rect) {
        let status = Paragraph::new(Line::from(vec![
            Span::styled(
                " helios-tui ",
                Style::default().fg(Color::Black).bg(Color::Cyan).add_modifier(Modifier::BOLD),
            ),
            Span::raw("  "),
            Span::styled(&self.status, Style::default().fg(Color::DarkGray)),
            Span::raw("  "),
            Span::styled("Ctrl+C to quit", Style::default().fg(Color::DarkGray)),
        ]));
        frame.render_widget(status, area);
    }

    /// Render the text input area at the bottom.
    fn render_input_area(&self, frame: &mut Frame, area: Rect) {
        let input_display = if self.input.is_empty() {
            Span::styled("Type a message...", Style::default().fg(Color::DarkGray))
        } else {
            Span::raw(&self.input)
        };

        let input = Paragraph::new(Line::from(vec![
            Span::styled("> ", Style::default().fg(Color::Cyan)),
            input_display,
        ]))
        .block(
            Block::default()
                .title(" Input ")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::DarkGray)),
        );
        frame.render_widget(Clear, area);
        frame.render_widget(input, area);
    }

    // -- event handling -----------------------------------------------------

    /// Handle a single key event. Returns `true` if the event was consumed.
    #[allow(dead_code)]
    fn handle_key(&mut self, key: KeyEvent) -> bool {
        match (key.modifiers, key.code) {
            (KeyModifiers::CONTROL, KeyCode::Char('c'))
            | (KeyModifiers::CONTROL, KeyCode::Char('C')) => {
                self.running = false;
                true
            }
            (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c)) => {
                self.input.push(c);
                true
            }
            (KeyModifiers::NONE, KeyCode::Backspace) => {
                self.input.pop();
                true
            }
            (KeyModifiers::NONE, KeyCode::Enter) => {
                if !self.input.is_empty() {
                    let text = std::mem::take(&mut self.input);
                    self.push_message(ChatMessage { role: Role::User, text });
                }
                true
            }
            _ => false,
        }
    }
}

impl Default for Tui {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn tui_new_has_default_state() {
        let tui = Tui::new();
        assert!(tui.is_running());
        assert!(tui.messages.is_empty());
        assert!(tui.input.is_empty());
        assert_eq!(tui.status, "Ready");
    }

    #[test]
    fn push_message_adds_to_history() {
        let mut tui = Tui::new();
        tui.push_message(ChatMessage { role: Role::User, text: "hello".into() });
        assert_eq!(tui.messages.len(), 1);
        assert_eq!(tui.messages[0].text, "hello");
    }

    #[test]
    fn handle_enter_submits_input() {
        let mut tui = Tui::new();
        tui.input = "test message".into();

        let consumed = tui.handle_key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE));
        assert!(consumed);
        assert!(tui.input.is_empty());
        assert_eq!(tui.messages.len(), 1);
        assert_eq!(tui.messages[0].role, Role::User);
        assert_eq!(tui.messages[0].text, "test message");
    }

    #[test]
    fn handle_ctrl_c_sets_running_false() {
        let mut tui = Tui::new();
        assert!(tui.is_running());

        let consumed = tui.handle_key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL));
        assert!(consumed);
        assert!(!tui.is_running());
    }

    #[test]
    fn handle_backspace_removes_last_char() {
        let mut tui = Tui::new();
        tui.input = "abc".into();
        tui.handle_key(KeyEvent::new(KeyCode::Backspace, KeyModifiers::NONE));
        assert_eq!(tui.input, "ab");
    }

    #[test]
    fn handle_char_appends_to_input() {
        let mut tui = Tui::new();
        tui.handle_key(KeyEvent::new(KeyCode::Char('h'), KeyModifiers::NONE));
        tui.handle_key(KeyEvent::new(KeyCode::Char('i'), KeyModifiers::NONE));
        assert_eq!(tui.input, "hi");
    }

    #[test]
    fn role_label_is_correct() {
        assert_eq!(Role::User.label(), "You");
        assert_eq!(Role::Assistant.label(), "Helios");
        assert_eq!(Role::System.label(), "System");
    }

    #[test]
    fn set_status_updates_text() {
        let mut tui = Tui::new();
        tui.set_status("Working...");
        assert_eq!(tui.status, "Working...");
    }
}
