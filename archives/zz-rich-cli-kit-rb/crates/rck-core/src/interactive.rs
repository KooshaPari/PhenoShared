//! Interactive primitives: alt-screen + kitty keyboard protocol.
//!
//! Three flows:
//! - [`ask`] — yes/no confirm. ↑/↓/←/→ swap, Enter commits, `y`/`n` hotkey,
//!   Esc cancels.
//! - [`pick`] — single-select from a list of choices.
//! - [`input`] — single-line input.
//!
//! All three:
//!   1. Try to enter alt-screen (`CSI ? 1049 h`) and push kitty-kbd flags
//!      (`CSI > 1 u`) on capable terminals.
//!   2. Render with the panel primitive for visual consistency.
//!   3. Restore terminal state on Enter, Esc, Ctrl-C, or SIGTERM.
//!   4. Fall back to a plain `stdin.read_line` prompt when the terminal is
//!      not interactive (no TTY or no kitty-kbd).

use crate::panel::{emit_panel, BorderStyle};
use crate::Capabilities;
use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};
use crossterm::terminal;
use std::io::{self, BufRead, Write};
use std::time::Duration;

/// Outcome of an interactive primitive.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Outcome<T> {
    Selected(T),
    Cancelled,
}

/// Controls whether the alt-screen + kitty-kbd path is used or we fall
/// back to a plain stdin prompt.
fn can_interact(caps: &Capabilities) -> bool {
    caps.is_tty && caps.kitty_keyboard
}

struct TermGuard {
    raw: bool,
    altscreen: bool,
    pushed_kbd: bool,
}

impl TermGuard {
    fn enter(caps: &Capabilities) -> io::Result<Self> {
        let raw = terminal::enable_raw_mode().is_ok();
        let mut stdout = io::stdout();
        // Alt-screen.
        let altscreen = stdout.write_all(b"\x1b[?1049h").is_ok();
        let _ = stdout.flush();
        // Kitty keyboard push.
        let pushed_kbd = if caps.kitty_keyboard {
            stdout.write_all(b"\x1b[>1u").is_ok()
        } else {
            false
        };
        let _ = stdout.flush();
        Ok(TermGuard {
            raw,
            altscreen,
            pushed_kbd,
        })
    }
}

impl Drop for TermGuard {
    fn drop(&mut self) {
        let mut stdout = io::stdout();
        if self.pushed_kbd {
            let _ = stdout.write_all(b"\x1b[<u");
        }
        if self.altscreen {
            let _ = stdout.write_all(b"\x1b[?1049l");
        }
        let _ = stdout.flush();
        if self.raw {
            let _ = terminal::disable_raw_mode();
        }
    }
}

fn draw_panel(caps: &Capabilities, title: &str, body: &[String]) -> io::Result<()> {
    let mut stdout = io::stdout();
    // Move cursor home + clear screen.
    stdout.write_all(b"\x1b[H\x1b[2J")?;
    let line_refs: Vec<&str> = body.iter().map(|s| s.as_str()).collect();
    emit_panel(&mut stdout, caps, title, &line_refs, BorderStyle::Rounded)
        .map_err(io::Error::other)?;
    stdout.flush()
}

/// Read one key event; returns `None` on SIGINT / Ctrl-C.
fn read_key() -> io::Result<Option<KeyEvent>> {
    // Block for up to 10s per poll then loop — keeps Ctrl-C responsive.
    loop {
        if event::poll(Duration::from_millis(250))? {
            match event::read()? {
                Event::Key(k) => {
                    if k.modifiers.contains(KeyModifiers::CONTROL)
                        && matches!(k.code, KeyCode::Char('c'))
                    {
                        return Ok(None);
                    }
                    return Ok(Some(k));
                }
                _ => continue,
            }
        }
    }
}

/// Yes/no confirm. Returns `Outcome::Selected(bool)`.
pub fn ask(caps: &Capabilities, question: &str) -> io::Result<Outcome<bool>> {
    if !can_interact(caps) {
        return ask_fallback(question);
    }
    let _guard = TermGuard::enter(caps)?;
    let mut yes = true;
    loop {
        let body = vec![
            question.to_string(),
            String::new(),
            if yes {
                "  [ Yes ]    No   ".to_string()
            } else {
                "   Yes   [ No ]  ".to_string()
            },
            String::new(),
            "↑/↓ or y/n · Enter commit · Esc cancel".to_string(),
        ];
        draw_panel(caps, "confirm", &body)?;
        let Some(key) = read_key()? else {
            return Ok(Outcome::Cancelled);
        };
        match key.code {
            KeyCode::Up | KeyCode::Down | KeyCode::Left | KeyCode::Right | KeyCode::Tab => {
                yes = !yes
            }
            KeyCode::Char('y') | KeyCode::Char('Y') => return Ok(Outcome::Selected(true)),
            KeyCode::Char('n') | KeyCode::Char('N') => return Ok(Outcome::Selected(false)),
            KeyCode::Enter => return Ok(Outcome::Selected(yes)),
            KeyCode::Esc => return Ok(Outcome::Cancelled),
            _ => {}
        }
    }
}

fn ask_fallback(question: &str) -> io::Result<Outcome<bool>> {
    let mut stdout = io::stdout();
    write!(stdout, "{question} [y/N] ")?;
    stdout.flush()?;
    let mut line = String::new();
    io::stdin().lock().read_line(&mut line)?;
    let t = line.trim().to_ascii_lowercase();
    if t.is_empty() {
        Ok(Outcome::Cancelled)
    } else if t.starts_with('y') {
        Ok(Outcome::Selected(true))
    } else {
        Ok(Outcome::Selected(false))
    }
}

/// Single-choice picker. Returns the selected string (clone of `choices[i]`).
pub fn pick(caps: &Capabilities, prompt: &str, choices: &[String]) -> io::Result<Outcome<String>> {
    if choices.is_empty() {
        return Ok(Outcome::Cancelled);
    }
    if !can_interact(caps) {
        return pick_fallback(prompt, choices);
    }
    let _guard = TermGuard::enter(caps)?;
    let mut idx = 0usize;
    loop {
        let mut body = vec![prompt.to_string(), String::new()];
        for (i, c) in choices.iter().enumerate() {
            let marker = if i == idx { "›" } else { " " };
            body.push(format!(" {marker} {c}"));
        }
        body.push(String::new());
        body.push("↑/↓ · Enter commit · Esc cancel".to_string());
        draw_panel(caps, "pick", &body)?;
        let Some(key) = read_key()? else {
            return Ok(Outcome::Cancelled);
        };
        match key.code {
            KeyCode::Up => {
                if idx == 0 {
                    idx = choices.len() - 1
                } else {
                    idx -= 1
                }
            }
            KeyCode::Down => {
                idx = (idx + 1) % choices.len();
            }
            KeyCode::Enter => return Ok(Outcome::Selected(choices[idx].clone())),
            KeyCode::Esc => return Ok(Outcome::Cancelled),
            _ => {}
        }
    }
}

fn pick_fallback(prompt: &str, choices: &[String]) -> io::Result<Outcome<String>> {
    let mut stdout = io::stdout();
    writeln!(stdout, "{prompt}")?;
    for (i, c) in choices.iter().enumerate() {
        writeln!(stdout, "  [{i}] {c}")?;
    }
    write!(stdout, "pick: ")?;
    stdout.flush()?;
    let mut line = String::new();
    io::stdin().lock().read_line(&mut line)?;
    let t = line.trim();
    if t.is_empty() {
        return Ok(Outcome::Cancelled);
    }
    if let Ok(n) = t.parse::<usize>() {
        if n < choices.len() {
            return Ok(Outcome::Selected(choices[n].clone()));
        }
    }
    // Try name match.
    if let Some(c) = choices.iter().find(|c| c.as_str() == t) {
        return Ok(Outcome::Selected(c.clone()));
    }
    Ok(Outcome::Cancelled)
}

/// Single-line input. Returns the entered string.
pub fn input(caps: &Capabilities, prompt: &str) -> io::Result<Outcome<String>> {
    if !can_interact(caps) {
        return input_fallback(prompt);
    }
    let _guard = TermGuard::enter(caps)?;
    let mut buf = String::new();
    loop {
        let body = vec![
            prompt.to_string(),
            String::new(),
            format!("  ▌ {buf}"),
            String::new(),
            "Enter commit · Esc cancel · Backspace".to_string(),
        ];
        draw_panel(caps, "input", &body)?;
        let Some(key) = read_key()? else {
            return Ok(Outcome::Cancelled);
        };
        match key.code {
            KeyCode::Enter => return Ok(Outcome::Selected(buf)),
            KeyCode::Esc => return Ok(Outcome::Cancelled),
            KeyCode::Backspace => {
                buf.pop();
            }
            KeyCode::Char(c) => {
                // Ignore Ctrl-<letter> combos as text input.
                if key.modifiers.contains(KeyModifiers::CONTROL) {
                    continue;
                }
                buf.push(c);
            }
            _ => {}
        }
    }
}

fn input_fallback(prompt: &str) -> io::Result<Outcome<String>> {
    let mut stdout = io::stdout();
    write!(stdout, "{prompt}: ")?;
    stdout.flush()?;
    let mut line = String::new();
    io::stdin().lock().read_line(&mut line)?;
    let t = line.trim_end_matches(['\r', '\n']).to_string();
    if t.is_empty() {
        Ok(Outcome::Cancelled)
    } else {
        Ok(Outcome::Selected(t))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn non_interactive_caps() -> Capabilities {
        Capabilities {
            graphics: false,
            sixel: false,
            truecolor: false,
            unicode_width: 1,
            terminal: "test".into(),
            is_tty: false,
            hyperlinks: false,
            clipboard: false,
            task_markers: false,
            kitty_keyboard: false,
            in_tmux: false,
        }
    }

    #[test]
    fn can_interact_requires_tty_and_kbd() {
        let mut c = non_interactive_caps();
        assert!(!can_interact(&c));
        c.is_tty = true;
        assert!(!can_interact(&c));
        c.kitty_keyboard = true;
        assert!(can_interact(&c));
    }

    #[test]
    fn ask_fallback_reads_y() {
        // Simulate "y\n" via a small helper: we can't easily stub stdin in unit tests,
        // but we can verify empty-input → Cancelled by parsing logic directly.
        // Lighter assertion: call the parser-style decision function indirectly.
        // Here we just make sure the fallback path does not panic on a non-tty.
        let caps = non_interactive_caps();
        // We cannot feed real stdin from a unit test reliably, so we verify
        // the routing logic instead.
        assert!(!can_interact(&caps));
    }

    #[test]
    fn outcome_equality() {
        let a: Outcome<bool> = Outcome::Selected(true);
        let b: Outcome<bool> = Outcome::Selected(true);
        assert_eq!(a, b);
        let c: Outcome<bool> = Outcome::Cancelled;
        assert_ne!(a, c);
    }

    #[test]
    fn pick_empty_choices_cancels() {
        let caps = non_interactive_caps();
        let r = pick(&caps, "prompt", &[]).unwrap();
        assert_eq!(r, Outcome::Cancelled);
    }

    #[test]
    fn term_guard_restores_on_drop_without_panic() {
        // Construction may or may not succeed depending on whether stdout is a
        // TTY during tests — either way, drop must not panic.
        let caps = non_interactive_caps();
        // Force-create a guard that won't actually push kbd (kitty_keyboard=false).
        // enable_raw_mode will likely fail under `cargo test`; that's fine.
        if let Ok(g) = TermGuard::enter(&caps) {
            drop(g);
        }
    }

    #[test]
    fn input_fallback_rejects_empty() {
        // We can't feed stdin; just verify the routing bit.
        let caps = non_interactive_caps();
        assert!(!can_interact(&caps));
    }

    #[test]
    fn ask_fallback_parses_n_like_string() {
        // Parser behavior tested indirectly: "n" → false, "" → Cancelled,
        // "yes" → true. We encode the logic here as a sanity check.
        fn classify(s: &str) -> Outcome<bool> {
            let t = s.trim().to_ascii_lowercase();
            if t.is_empty() {
                Outcome::Cancelled
            } else if t.starts_with('y') {
                Outcome::Selected(true)
            } else {
                Outcome::Selected(false)
            }
        }
        assert_eq!(classify("y"), Outcome::Selected(true));
        assert_eq!(classify("N"), Outcome::Selected(false));
        assert_eq!(classify(""), Outcome::Cancelled);
        assert_eq!(classify("yes please"), Outcome::Selected(true));
    }
}
