//! Capability detection via env vars + optional TTY query.

use crossterm::tty::IsTty;
use serde::{Deserialize, Serialize};
use std::env;
use std::io::{self, Write};
use std::time::Duration;

/// What the attached terminal can render.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Capabilities {
    /// Supports kitty-graphics-protocol APC _G sequences.
    pub graphics: bool,
    /// Supports sixel (DECSIXEL).
    pub sixel: bool,
    /// Supports 24-bit truecolor SGR.
    pub truecolor: bool,
    /// Assumed unicode column width support (1 = ASCII only, 2 = full unicode/wide).
    pub unicode_width: u16,
    /// Human-readable name of the detected terminal.
    pub terminal: String,
    /// Whether stdout is a TTY at detection time.
    pub is_tty: bool,
    /// Supports OSC 8 hyperlinks.
    pub hyperlinks: bool,
    /// Supports OSC 52 clipboard write.
    pub clipboard: bool,
    /// Supports OSC 133 semantic prompt markers.
    pub task_markers: bool,
    /// Supports kitty keyboard protocol progressive flags.
    pub kitty_keyboard: bool,
    /// Running inside tmux (DCS-passthrough wrapping applies).
    pub in_tmux: bool,
}

impl Capabilities {
    pub fn plain() -> Self {
        Capabilities {
            graphics: false,
            sixel: false,
            truecolor: false,
            unicode_width: 1,
            terminal: "unknown".into(),
            is_tty: false,
            hyperlinks: false,
            clipboard: false,
            task_markers: false,
            kitty_keyboard: false,
            in_tmux: false,
        }
    }
}

/// Detect capabilities. Runs synchronously; TTY query has a 150ms timeout.
pub fn detect() -> Capabilities {
    let is_tty = io::stdout().is_tty();
    let term = env::var("TERM").unwrap_or_default();
    let term_program = env::var("TERM_PROGRAM").unwrap_or_default();
    let colorterm = env::var("COLORTERM").unwrap_or_default();
    let wezterm = env::var("WEZTERM_EXECUTABLE").is_ok();
    let kitty = env::var("KITTY_WINDOW_ID").is_ok();
    let konsole = env::var("KONSOLE_VERSION").is_ok();

    let terminal =
        if term_program == "ghostty" || term_program == "Ghostty" || term == "xterm-ghostty" {
            "ghostty"
        } else if kitty || term.contains("kitty") {
            "kitty"
        } else if wezterm || term_program == "WezTerm" {
            "wezterm"
        } else if term_program == "iTerm.app" {
            "iterm2"
        } else if konsole {
            "konsole"
        } else if !term.is_empty() {
            term.as_str()
        } else {
            "unknown"
        }
        .to_string();

    // Env-based inference first (these are known-good).
    let mut graphics = matches!(terminal.as_str(), "ghostty" | "kitty" | "wezterm");
    let sixel = matches!(terminal.as_str(), "konsole" | "iterm2" | "wezterm");
    let truecolor = colorterm == "truecolor" || colorterm == "24bit" || graphics;
    let unicode_width: u16 = if term == "dumb" || term.is_empty() {
        1
    } else {
        2
    };

    // If TTY and not yet confirmed, try the kitty-graphics query.
    if is_tty && !graphics {
        if let Ok(true) = query_kitty_graphics(Duration::from_millis(150)) {
            graphics = true;
        }
    }

    // If stdout is not a TTY, force graphics off (no point writing APC to a pipe).
    if !is_tty {
        graphics = false;
    }

    // Modern-terminal OSC features: hyperlinks (OSC 8), task markers (OSC 133),
    // kitty-kbd are supported by the same family as graphics. Apple Terminal
    // supports NONE of them. OSC 52 clipboard is more widely supported.
    let modern = matches!(
        terminal.as_str(),
        "ghostty" | "kitty" | "wezterm" | "iterm2"
    );
    let apple = term_program == "Apple_Terminal";
    let hyperlinks = modern && !apple;
    let task_markers = modern && !apple;
    let kitty_keyboard = matches!(terminal.as_str(), "ghostty" | "kitty" | "wezterm");
    // Clipboard write is broadly supported — add konsole + Apple Terminal (with a tiny limit).
    let clipboard = modern || matches!(terminal.as_str(), "konsole") || apple;

    let in_tmux = std::env::var("TMUX").is_ok();

    Capabilities {
        graphics,
        sixel,
        truecolor,
        unicode_width,
        terminal,
        is_tty,
        hyperlinks,
        clipboard,
        task_markers,
        kitty_keyboard,
        in_tmux,
    }
}

/// Send a minimal kitty-graphics query and look for the `OK` / error response.
///
/// Sequence (per kitty spec):
///   ESC _ G i=31,s=1,v=1,a=q,t=d,f=24 ; AAAA ESC \  ESC [c
///
/// We expect either `ESC _ G i=31;OK ESC \` (graphics supported) or just the
/// primary-DA response (no graphics).
#[cfg(unix)]
fn query_kitty_graphics(timeout: Duration) -> io::Result<bool> {
    use std::os::fd::AsRawFd;

    let stdin_fd = io::stdin().as_raw_fd();
    let stdout_fd = io::stdout().as_raw_fd();

    // Enable raw mode on stdin so the response isn't echoed / line-buffered.
    let termios_orig = match get_termios(stdin_fd) {
        Ok(t) => t,
        Err(_) => return Ok(false),
    };
    if set_raw(stdin_fd).is_err() {
        return Ok(false);
    }

    let restore = |_| {
        let _ = set_termios(stdin_fd, &termios_orig);
    };

    // Write the query.
    let query = b"\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\\x1b[c";
    if unsafe { libc_write(stdout_fd, query) }.is_err() {
        restore(());
        return Ok(false);
    }

    // Poll stdin for up to `timeout`, collect bytes.
    let mut buf = Vec::with_capacity(128);
    let deadline = std::time::Instant::now() + timeout;
    while std::time::Instant::now() < deadline {
        let remaining = deadline.saturating_duration_since(std::time::Instant::now());
        if !poll_readable(stdin_fd, remaining)? {
            break;
        }
        let mut chunk = [0u8; 64];
        let n = unsafe { libc_read(stdin_fd, &mut chunk) }.unwrap_or(0);
        if n == 0 {
            break;
        }
        buf.extend_from_slice(&chunk[..n]);
        // Stop once we see the primary-DA terminator `c` after `ESC [`.
        if buf.windows(2).any(|w| w == b"[?") && buf.contains(&b'c') {
            break;
        }
    }

    restore(());

    // If response contains `_Gi=31;OK` kitty graphics is supported.
    let s = String::from_utf8_lossy(&buf);
    Ok(s.contains("_Gi=31;OK") || s.contains("_Gi=31;ok"))
}

// --- minimal libc shims (avoid adding the `libc` crate as a dependency) ---

#[cfg(unix)]
unsafe fn libc_write(fd: i32, buf: &[u8]) -> io::Result<usize> {
    extern "C" {
        fn write(fd: i32, buf: *const u8, count: usize) -> isize;
    }
    let n = write(fd, buf.as_ptr(), buf.len());
    if n < 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(n as usize)
    }
}

#[cfg(unix)]
unsafe fn libc_read(fd: i32, buf: &mut [u8]) -> io::Result<usize> {
    extern "C" {
        fn read(fd: i32, buf: *mut u8, count: usize) -> isize;
    }
    let n = read(fd, buf.as_mut_ptr(), buf.len());
    if n < 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(n as usize)
    }
}

#[cfg(unix)]
#[repr(C)]
#[derive(Clone)]
struct Termios([u8; 256]); // oversized opaque buffer; we only round-trip it.

#[cfg(unix)]
fn get_termios(fd: i32) -> io::Result<Termios> {
    extern "C" {
        fn tcgetattr(fd: i32, termios: *mut u8) -> i32;
    }
    let mut t = Termios([0u8; 256]);
    let rc = unsafe { tcgetattr(fd, t.0.as_mut_ptr()) };
    if rc != 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(t)
    }
}

#[cfg(unix)]
fn set_termios(fd: i32, t: &Termios) -> io::Result<()> {
    extern "C" {
        fn tcsetattr(fd: i32, actions: i32, termios: *const u8) -> i32;
    }
    let rc = unsafe {
        tcsetattr(fd, 0 /* TCSANOW */, t.0.as_ptr())
    };
    if rc != 0 {
        Err(io::Error::last_os_error())
    } else {
        Ok(())
    }
}

#[cfg(unix)]
fn set_raw(fd: i32) -> io::Result<()> {
    // Use crossterm's helper: it enables raw mode globally on the current TTY,
    // not per-fd, but it is sufficient for our short query.
    crossterm::terminal::enable_raw_mode().map_err(|e| io::Error::other(format!("{e}")))?;
    // We don't actually need the fd here; kept for symmetry.
    let _ = fd;
    Ok(())
}

#[cfg(unix)]
fn poll_readable(fd: i32, timeout: Duration) -> io::Result<bool> {
    extern "C" {
        fn poll(fds: *mut PollFd, nfds: u64, timeout: i32) -> i32;
    }
    #[repr(C)]
    struct PollFd {
        fd: i32,
        events: i16,
        revents: i16,
    }
    let mut pfd = PollFd {
        fd,
        events: 0x0001, /* POLLIN */
        revents: 0,
    };
    let ms = timeout.as_millis().min(i32::MAX as u128) as i32;
    let rc = unsafe { poll(&mut pfd as *mut PollFd, 1, ms) };
    Ok(rc > 0)
}

#[cfg(not(unix))]
fn query_kitty_graphics(_timeout: Duration) -> io::Result<bool> {
    Ok(false)
}

#[allow(dead_code)]
fn _touch_write_import(w: &mut dyn Write) {
    let _ = w;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plain_is_safe_default() {
        let c = Capabilities::plain();
        assert!(!c.graphics);
        assert!(!c.sixel);
        assert!(!c.hyperlinks);
        assert!(!c.clipboard);
        assert!(!c.task_markers);
        assert!(!c.kitty_keyboard);
        assert!(!c.in_tmux);
        assert_eq!(c.unicode_width, 1);
    }

    #[test]
    fn detect_returns_a_value() {
        // We can't assert specific flags (depends on env), but it must not panic.
        let c = detect();
        // terminal name is never empty.
        assert!(!c.terminal.is_empty());
    }
}
