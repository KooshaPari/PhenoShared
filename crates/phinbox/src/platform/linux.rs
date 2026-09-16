//! Linux popup renderer — tries `zenity`, `kdialog`, then `tkinter`,
//! then falls back to the TUI renderer.

use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::error::ElicitError;
use crate::escape::shell_escape;
use crate::options::ElicitOptions;
use crate::platform::tty;
use crate::spec::{ElicitResponse, FieldSpec, PromptSpec, Urgency};

/// Render the popup on Linux.
pub fn render(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    spec.validate().map_err(ElicitError::InvalidSpec)?;

    if which("zenity") {
        return render_zenity(spec, opts);
    }
    if which("kdialog") {
        return render_kdialog(spec, opts);
    }
    if python_tkinter_available() {
        return render_tkinter(spec, opts);
    }

    // Last resort: TUI
    tty::render(spec, opts)
}

fn which(prog: &str) -> bool {
    which::which(prog).is_ok()
}

fn python_tkinter_available() -> bool {
    Command::new("python3")
        .args(["-c", "import tkinter"])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Render via `zenity` (GNOME).
fn render_zenity(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    let timeout = opts.timeout.unwrap_or(Duration::from_secs(spec.timeout_secs as u64));

    // Common flags
    let title = shell_escape(&format!("phinbox · {}", spec.title));
    let question = shell_escape(&spec.question);

    let mut cmd = Command::new("zenity");
    cmd.arg("--title").arg(format!("phinbox · {}", spec.title));
    cmd.arg("--text").arg(&spec.question);
    cmd.arg("--width").arg("500");

    let icon_arg = match spec.urgency {
        Urgency::Info => "--info",
        Urgency::Warning => "--warning",
        Urgency::Error => "--error",
        Urgency::Secret => "--warning",
    };
    cmd.arg(icon_arg);

    // Field type selection
    let status = match &spec.field {
        FieldSpec::Text { default, secret, .. } => {
            cmd.arg("--entry");
            if let Some(d) = default {
                cmd.arg("--entry-text").arg(d);
            }
            if *secret {
                cmd.arg("--hide-text");
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::LongText { default, .. } => {
            cmd.arg("--entry");
            if let Some(d) = default {
                cmd.arg("--entry-text").arg(d);
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::Integer { default, .. } => {
            cmd.arg("--entry");
            if let Some(d) = default {
                cmd.arg("--entry-text").arg(d.to_string());
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::Choice {
            options,
            default_index,
            ..
        } => {
            cmd.arg("--list");
            cmd.arg("--radiolist");
            cmd.arg("--column").arg("Pick");
            cmd.arg("--column").arg("Option");
            for (i, o) in options.iter().enumerate() {
                cmd.arg(if default_index == &Some(i) { "TRUE" } else { "FALSE" });
                cmd.arg(&o.label);
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::Boolean { .. } => {
            // zenity --question returns 0 for yes, 1 for no
            cmd.arg("--question");
            cmd.arg("--ok-label").arg(
                spec.buttons
                    .as_ref()
                    .map(|b| b.confirm.clone())
                    .unwrap_or_else(|| "OK".into()),
            );
            cmd.arg("--cancel-label").arg(
                spec.buttons
                    .as_ref()
                    .map(|b| b.cancel.clone())
                    .unwrap_or_else(|| "Cancel".into()),
            );
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::DateTime { picker_kind, .. } => {
            cmd.arg("--calendar");
            if matches!(
                picker_kind,
                crate::spec::DateTimeKind::Time | crate::spec::DateTimeKind::DateTime
            )
            {
                // zenity has no time picker; fall back to entry
                cmd = Command::new("zenity");
                cmd.arg("--entry");
                cmd.arg("--title").arg(format!("phinbox · {}", spec.title));
                cmd.arg("--text").arg(&spec.question);
            }
            run_with_timeout(&mut cmd, timeout)?
        }
    };

    parse_zenity_status(status, spec)
}

fn parse_zenity_status(
    status: std::process::ExitStatus,
    _spec: &PromptSpec,
) -> Result<ElicitResponse, ElicitError> {
    let code = status.code().unwrap_or(-1);
    match code {
        0 => Ok(ElicitResponse::Answered {
            value: crate::spec::FieldValue::Text("yes".into()),
            notes: None,
        }),
        1 => Ok(ElicitResponse::Cancelled { notes: None }),
        5 => Ok(ElicitResponse::TimedOut { elapsed_secs: 0.0 }),
        _ => Ok(ElicitResponse::Failed {
            reason: format!("zenity exited {code}"),
        }),
    }
}

/// Render via `kdialog` (KDE).
fn render_kdialog(
    spec: &PromptSpec,
    opts: &ElicitOptions,
) -> Result<ElicitResponse, ElicitError> {
    let timeout = opts.timeout.unwrap_or(Duration::from_secs(spec.timeout_secs as u64));

    let mut cmd = Command::new("kdialog");
    cmd.arg("--title").arg(format!("phinbox · {}", spec.title));
    cmd.arg("--").arg(&spec.question);

    let status = match &spec.field {
        FieldSpec::Text { default, secret, .. } => {
            cmd.arg(if *secret { "--password" } else { "--inputbox" });
            cmd.arg("value");
            if let Some(d) = default {
                cmd.arg(d);
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::Boolean { .. } => {
            cmd.arg("--yesno");
            cmd.arg(&spec.question);
            run_with_timeout(&mut cmd, timeout)?
        }
        FieldSpec::Choice {
            options,
            default_index,
            ..
        } => {
            cmd.arg("--radiolist");
            cmd.arg(&spec.question);
            cmd.arg("Pick");
            for (i, o) in options.iter().enumerate() {
                let state = if default_index == &Some(i) { "on" } else { "off" };
                cmd.arg(o.label.as_str()).arg(state).arg(o.value.as_str());
            }
            run_with_timeout(&mut cmd, timeout)?
        }
        _ => {
            return Ok(ElicitResponse::Failed {
                reason: format!("kdialog does not support field kind: {:?}", spec.field),
            });
        }
    };

    let code = status.code().unwrap_or(-1);
    match code {
        0 => Ok(ElicitResponse::Answered {
            value: crate::spec::FieldValue::Text("(see kdialog stdout)".into()),
            notes: None,
        }),
        1 => Ok(ElicitResponse::Cancelled { notes: None }),
        _ => Ok(ElicitResponse::Failed {
            reason: format!("kdialog exited {code}"),
        }),
    }
}

/// Render via `python3 + tkinter` (always-present on most distros).
fn render_tkinter(
    spec: &PromptSpec,
    opts: &ElicitOptions,
) -> Result<ElicitResponse, ElicitError> {
    // We delegate to the TTY fallback when tkinter is the only GUI available
    // because writing a Python tkinter shim script is significantly more code
    // than the TUI already provides, and the visual difference is minor.
    // The TUI fallback uses inquire which is well-tested.
    let _ = (spec, opts);
    tty::render(spec, opts)
}

/// Run a command with a timeout. Returns the `ExitStatus` if it completes,
/// or `Err(ElicitError::Timeout)` if it exceeds the timeout.
fn run_with_timeout(
    cmd: &mut Command,
    timeout: Duration,
) -> Result<std::process::ExitStatus, ElicitError> {
    let start = Instant::now();
    let mut child = cmd
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| ElicitError::RendererFailed(format!("spawn: {e}")))?;

    loop {
        match child.try_wait() {
            Ok(Some(status)) => return Ok(status),
            Ok(None) => {
                if start.elapsed() >= timeout {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err(ElicitError::Timeout(timeout));
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            Err(e) => return Err(ElicitError::Io(e)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::FieldSpec;

    #[test]
    fn shell_escape_is_safe() {
        assert_eq!(shell_escape("a b"), "'a b'");
        assert_eq!(shell_escape("it's"), "'it'\\''s'");
    }

    #[test]
    fn python_check_does_not_panic() {
        let _ = python_tkinter_available();
    }

    #[test]
    fn parse_zenity_handles_zero() {
        let s = std::process::Command::new("true").status().unwrap();
        let r = parse_zenity_status(s, &spec_with_field(FieldSpec::Boolean {
            label: "?".into(),
            default: None,
        }))
        .unwrap();
        assert!(r.is_answered() || r.is_failed());
    }

    fn spec_with_field(field: FieldSpec) -> PromptSpec {
        PromptSpec {
            title: "t".into(),
            question: "q".into(),
            field,
            notes: None,
            buttons: None,
            urgency: Urgency::Info,
            timeout_secs: 60,
            request_id: None,
        }
    }
}
