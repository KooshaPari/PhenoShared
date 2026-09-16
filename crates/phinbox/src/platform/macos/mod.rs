//! macOS popup renderer via `osascript`'s `display dialog` command.
//!
//! `AppleScript`'s `display dialog` is a thin wrapper over `AppKit`'s `NSAlert`,
//! which is the canonical modal native popup on macOS. We shell out to
//! `osascript` rather than linking `AppKit` because:
//!
//! 1. `osascript` is a system component on every macOS install (since OS 8).
//! 2. Linking `AppKit` requires Xcode SDK + a Cocoa build script.
//! 3. The popup is rendered out-of-process, so the MCP server is never
//!    blocked on the `AppKit` main thread.
//!
//! Wire format: we emit a single `display dialog` call with custom
//! properties (title, default answer, icon, timeout). The user-entered
//! text and button name are returned on stdout as
//! `STATUS|BUTTON|TEXT|NOTES` for easy parsing.

mod parse;
mod script;

use std::os::unix::process::CommandExt;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::spec::{ElicitResponse, PromptSpec};

use parse::parse_output;
use script::build_script;

pub use parse::coerce_value;

/// Render the popup on macOS.
pub fn render(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    spec.validate().map_err(ElicitError::InvalidSpec)?;

    let script = build_script(spec)?;
    let timeout = opts
        .timeout
        .unwrap_or(Duration::from_secs(u64::from(spec.timeout_secs)));

    let start = Instant::now();
    let mut child = Command::new("osascript")
        .arg("-e")
        .arg(&script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .process_group(0) // detach so SIGTERM to MCP server doesn't kill popup
        .spawn()
        .map_err(|e| ElicitError::RendererFailed(format!("spawn osascript: {e}")))?;

    // Wait with timeout
    let output = loop {
        match child.try_wait() {
            Ok(Some(_status)) => {
                let out = child.wait_with_output().map_err(ElicitError::Io)?;
                break out;
            }
            Ok(None) => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Ok(ElicitResponse::TimedOut {
                        elapsed_secs: start.elapsed().as_secs_f64(),
                    });
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(e) => return Err(ElicitError::Io(e)),
        }
    };

    parse_output(&output.stdout, &output.stderr, start.elapsed())
}
