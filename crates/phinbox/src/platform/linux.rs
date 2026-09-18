//! Linux popup renderer — tries `zenity`, `kdialog`, then `tkinter`,
//! then falls back to the TUI renderer.

use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::error::ElicitError;
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
    let timeout = opts
        .timeout
        .unwrap_or(Duration::from_secs(u64::from(spec.timeout_secs)));

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
    let outcome = match &spec.field {
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

    parse_zenity_outcome(outcome, spec)
}

/// Turn a finished zenity invocation into a response.
///
/// zenity signals the *outcome* through the exit code and the *value*
/// through stdout. Reading only the exit code (as this used to) discards
/// whatever the user typed and hands back a placeholder instead.
fn parse_zenity_outcome(outcome: Outcome, spec: &PromptSpec) -> Result<ElicitResponse, ElicitError> {
    let code = outcome.status.code().unwrap_or(-1);
    match code {
        0 => Ok(ElicitResponse::Answered {
            value: crate::spec::FieldValue::Text(answer_text(&outcome, spec)),
            notes: None,
        }),
        // 1 = cancel/No. With `--ok-label`/`--cancel-label` this is the
        // cancel button, so it maps to Cancelled rather than a false answer.
        1 => Ok(ElicitResponse::Cancelled { notes: None }),
        5 => Ok(ElicitResponse::TimedOut {
            elapsed_secs: outcome.elapsed.as_secs_f64(),
        }),
        _ => Ok(ElicitResponse::Failed {
            reason: format!("zenity exited {code}"),
        }),
    }
}

/// The value a confirm-style dialog implies when it prints nothing.
///
/// `--question` has no output field: OK means "yes" (or the first option).
/// Everything else (`--entry`, `--calendar`, `--list`) prints the value.
fn answer_text(outcome: &Outcome, spec: &PromptSpec) -> String {
    if !outcome.stdout.is_empty() {
        return outcome.stdout.clone();
    }
    match &spec.field {
        FieldSpec::Boolean { .. } => "yes".to_string(),
        FieldSpec::Choice { options, .. } => options
            .first()
            .map_or_else(String::new, |o| o.value.clone()),
        _ => String::new(),
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

    let outcome = match &spec.field {
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

    // Like zenity: exit code = outcome, stdout = value. `--yesno` prints
    // nothing, so a Boolean falls back to "yes" on success.
    let code = outcome.status.code().unwrap_or(-1);
    match code {
        0 => Ok(ElicitResponse::Answered {
            value: crate::spec::FieldValue::Text(answer_text(&outcome, spec)),
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

/// A finished dialog invocation: how it exited *and* what it printed.
///
/// Both matter — zenity/kdialog report success or cancellation through the
/// exit code and the user's actual answer through stdout. Capturing only the
/// exit code silently discards every text, choice and date the user entered.
#[derive(Debug)]
struct Outcome {
    status: std::process::ExitStatus,
    stdout: String,
    elapsed: Duration,
}

/// Run a command with a timeout, capturing its stdout.
///
/// Returns the [`Outcome`] on completion, or [`ElicitError::Timeout`] if it
/// exceeds `timeout` (the dispatcher converts that into
/// [`crate::spec::ElicitResponse::TimedOut`]).
fn run_with_timeout(cmd: &mut Command, timeout: Duration) -> Result<Outcome, ElicitError> {
    let start = Instant::now();
    let mut child = cmd
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| ElicitError::RendererFailed(format!("spawn: {e}")))?;

    loop {
        match child.try_wait() {
            Ok(Some(_)) => {
                let out = child.wait_with_output().map_err(ElicitError::Io)?;
                return Ok(Outcome {
                    status: out.status,
                    // Trim the trailing newline the tools append.
                    stdout: String::from_utf8_lossy(&out.stdout).trim().to_string(),
                    elapsed: start.elapsed(),
                });
            }
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
    use crate::spec::{ChoiceOption, FieldSpec};

    fn spec_with_field(field: FieldSpec) -> PromptSpec {
        PromptSpec {
            details: None,
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

    fn boolean_spec() -> PromptSpec {
        spec_with_field(FieldSpec::Boolean {
            label: "?".into(),
            default: None,
        })
    }

    #[test]
    fn python_check_does_not_panic() {
        let _ = python_tkinter_available();
    }

    #[test]
    fn run_with_timeout_captures_stdout() {
        // Regression: the old helper returned only ExitStatus and threw away
        // stdout, so every typed answer was replaced by a placeholder.
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "printf 'hello\\n'"]);
        let outcome = run_with_timeout(&mut cmd, Duration::from_secs(5)).unwrap();
        assert_eq!(outcome.stdout, "hello", "trailing newline should be trimmed");
        assert!(outcome.status.success());
    }

    #[test]
    fn answered_uses_the_captured_stdout() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "printf 'typed-by-user\\n'"]);
        let outcome = run_with_timeout(&mut cmd, Duration::from_secs(5)).unwrap();
        let r = parse_zenity_outcome(outcome, &boolean_spec()).unwrap();
        match r {
            ElicitResponse::Answered { value, .. } => {
                assert!(
                    matches!(value, crate::spec::FieldValue::Text(ref s) if s == "typed-by-user"),
                    "must carry the real value, got {value:?}"
                );
            }
            other => panic!("expected Answered, got {other:?}"),
        }
    }

    #[test]
    fn confirm_dialogs_without_stdout_fall_back_sensibly() {
        // `--question`/`--yesno` print nothing: OK means yes.
        let mut cmd = Command::new("true");
        let outcome = run_with_timeout(&mut cmd, Duration::from_secs(5)).unwrap();
        assert_eq!(answer_text(&outcome, &boolean_spec()), "yes");

        // A Choice with no stdout falls back to its first option's value.
        let choice = spec_with_field(FieldSpec::Choice {
            label: "p".into(),
            options: vec![
                ChoiceOption {
                    value: "staging".into(),
                    label: "Staging".into(),
                    description: None,
                },
                ChoiceOption {
                    value: "prod".into(),
                    label: "Production".into(),
                    description: None,
                },
            ],
            default_index: None,
        });
        assert_eq!(answer_text(&outcome, &choice), "staging");
    }

    #[test]
    fn nonzero_exit_is_cancelled_not_answered() {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", "exit 1"]);
        let outcome = run_with_timeout(&mut cmd, Duration::from_secs(5)).unwrap();
        assert!(parse_zenity_outcome(outcome, &boolean_spec())
            .unwrap()
            .is_cancelled());
    }

    #[test]
    fn exceeding_the_timeout_yields_timeout_not_status() {
        // The dispatcher turns ElicitError::Timeout into ElicitResponse::TimedOut.
        let mut cmd = Command::new("sleep");
        cmd.arg("5");
        let err = run_with_timeout(&mut cmd, Duration::from_millis(200)).unwrap_err();
        assert!(
            matches!(err, ElicitError::Timeout(_)),
            "expected Timeout, got {err:?}"
        );
    }
}
