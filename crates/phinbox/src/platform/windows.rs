//! Windows popup renderer via PowerShell + Win32 Forms.
//!
//! PowerShell on Windows can instantiate `System.Windows.Forms.Form` —
//! a managed wrapper over `USER32.dll`'s `CreateWindowEx`. We shell out
//! to `powershell.exe` rather than calling Win32 directly because:
//!
//! 1. PowerShell ships with every supported Windows version (10/11/Server).
//! 2. Direct Win32 calls from Rust are fragile across OS patches.
//! 3. The popup is rendered out-of-process, so the MCP server is not
//!    blocked on a UI thread.
//!
//! Wire format: the PowerShell script prints
//! `STATUS|BUTTON|TEXT|NOTES` to stdout, which we parse identically to
//! the macOS renderer.

use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::error::ElicitError;
use crate::escape::powershell_escape;
use crate::options::ElicitOptions;
use crate::spec::{ElicitResponse, FieldSpec, PromptSpec, Urgency};

#[cfg(target_os = "windows")]
const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;

/// Render the popup on Windows.
pub fn render(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    spec.validate().map_err(ElicitError::InvalidSpec)?;

    let script = build_script(spec)?;
    // `None` = wait forever (timeout_secs 0 is documented as "no timeout").
    let timeout = super::deadline_for(spec, opts);

    let start = Instant::now();
    let mut command = Command::new("powershell.exe");
    command
        .arg("-NoProfile")
        .arg("-NonInteractive")
        .arg("-ExecutionPolicy")
        .arg("Bypass")
        .arg("-Command")
        .arg(&script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NEW_PROCESS_GROUP);
    }

    let mut child = command
        .spawn()
        .map_err(|e| ElicitError::RendererFailed(format!("spawn powershell: {e}")))?;

    let output = loop {
        match child.try_wait() {
            Ok(Some(_status)) => {
                let out = child.wait_with_output().map_err(ElicitError::Io)?;
                break out;
            }
            Ok(None) => {
                if timeout.is_some_and(|t| start.elapsed() >= t) {
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

/// Build the PowerShell source.
fn build_script(spec: &PromptSpec) -> Result<String, ElicitError> {
    let title = powershell_escape(&format!("phinbox · {}", spec.title))?;
    let question = powershell_escape(&spec.question)?;
    let (cancel_label, confirm_label) = spec
        .buttons
        .as_ref()
        .map(|b| (b.cancel.clone(), b.confirm.clone()))
        .unwrap_or_else(|| ("Cancel".to_string(), "OK".to_string()));
    let cancel_q = powershell_escape(&cancel_label)?;
    let confirm_q = powershell_escape(&confirm_label)?;

    // A custom `Form` has no MessageBox icon, so urgency is expressed as
    // the question label's colour instead. (The previous `MessageBoxIcon`
    // expression was interpolated nowhere: the format! arg was unused.)
    let urgency_clause = match spec.urgency {
        Urgency::Error | Urgency::Secret => {
            "$lblQuestion.ForeColor = [System.Drawing.Color]::FromArgb(180, 0, 0)\n"
        }
        Urgency::Warning => "$lblQuestion.ForeColor = [System.Drawing.Color]::FromArgb(150, 90, 0)\n",
        Urgency::Info => "",
    };

    // For text fields with defaults, pass the default through
    let default_expr = match &spec.field {
        FieldSpec::Text { default, .. } => powershell_escape(default.as_deref().unwrap_or(""))?,
        FieldSpec::LongText { default, .. } => {
            powershell_escape(default.as_deref().unwrap_or(""))?
        }
        _ => powershell_escape("")?,
    };

    let notes_block = if spec.notes.is_some() {
        r#"
    # Notes box (RichTextBox)
    $lblNotes = New-Object System.Windows.Forms.Label
    $lblNotes.Text = "Why? (optional)"
    $lblNotes.Location = New-Object System.Drawing.Point(20, 140)
    $lblNotes.AutoSize = $true
    $form.Controls.Add($lblNotes)
    $txtNotes = New-Object System.Windows.Forms.RichTextBox
    $txtNotes.Location = New-Object System.Drawing.Point(20, 160)
    $txtNotes.Size = New-Object System.Drawing.Size(440, 120)
    $form.Controls.Add($txtNotes)
"#
    } else {
        ""
    };

    // Secret field uses a TextBox with PasswordChar
    let (input_kind, secret_clause) = match &spec.field {
        FieldSpec::Text { secret: true, .. } => ("TextBox", "    $txtField.PasswordChar = '*'\n"),
        FieldSpec::Text { .. } | FieldSpec::LongText { .. } => ("TextBox", ""),
        FieldSpec::Integer { .. } => {
            ("NumericUpDown", "    $txtField.Minimum = -2147483648\n    $txtField.Maximum = 2147483647\n")
        }
        FieldSpec::Choice { .. } | FieldSpec::Boolean { .. } => ("ComboBox", ""),
        FieldSpec::DateTime { .. } => ("DateTimePicker", ""),
    };

    let placeholder_expr = match &spec.field {
        FieldSpec::Text { placeholder, .. } => {
            powershell_escape(placeholder.as_deref().unwrap_or(""))?
        }
        _ => powershell_escape("")?,
    };

    let script = format!(
        r#"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = {title}
$form.Size = New-Object System.Drawing.Size(500, 350)
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.TopMost = $true
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$form.MaximizeBox = $false

$lblQuestion = New-Object System.Windows.Forms.Label
$lblQuestion.Text = {question}
$lblQuestion.Location = New-Object System.Drawing.Point(20, 20)
$lblQuestion.Size = New-Object System.Drawing.Size(440, 100)
$lblQuestion.AutoSize = $false
{urgency_clause}$form.Controls.Add($lblQuestion)

$txtField = New-Object System.Windows.Forms.{input_kind}
$txtField.Location = New-Object System.Drawing.Point(20, 110)
$txtField.Size = New-Object System.Drawing.Size(440, 25)
$fieldDefault = {default}
if ($fieldDefault -ne "") {{ $txtField.Text = $fieldDefault }}
$fieldPlaceholder = {placeholder}
if ($fieldPlaceholder -ne "") {{
    try {{ $txtField.PlaceholderText = $fieldPlaceholder }} catch {{ }}
}}
{secret_clause}$form.Controls.Add($txtField)
{notes_block}

$btnOk = New-Object System.Windows.Forms.Button
$btnOk.Text = {confirm_q}
$btnOk.Location = New-Object System.Drawing.Point(290, 290)
$btnOk.Size = New-Object System.Drawing.Size(80, 30)
$btnOk.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.Controls.Add($btnOk)
$form.AcceptButton = $btnOk

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = {cancel_q}
$btnCancel.Location = New-Object System.Drawing.Point(380, 290)
$btnCancel.Size = New-Object System.Drawing.Size(80, 30)
$btnCancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($btnCancel)
$form.CancelButton = $btnCancel

$dialogResult = $form.ShowDialog()
$fieldText = $txtField.Text
$notesText = if ($txtNotes) {{ $txtNotes.Text }} else {{ "" }}

if ($dialogResult -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output ("answered|" + {confirm_q} + "|" + $fieldText + "|" + $notesText)
}} else {{
    Write-Output ("cancelled|" + {cancel_q} + "|" + $fieldText + "|" + $notesText)
}}
"#,
        title = title,
        question = question,
        default = default_expr,
        placeholder = placeholder_expr,
        input_kind = input_kind,
        secret_clause = secret_clause,
        notes_block = notes_block,
        confirm_q = confirm_q,
        cancel_q = cancel_q,
        urgency_clause = urgency_clause,
    );

    Ok(script)
}

/// Parse PowerShell's stdout/stderr into an [`ElicitResponse`].
fn parse_output(
    stdout: &[u8],
    _stderr: &[u8],
    elapsed: Duration,
) -> Result<ElicitResponse, ElicitError> {
    let text = std::str::from_utf8(stdout)
        .map_err(|e| ElicitError::RendererFailed(format!("non-utf8 stdout: {e}")))?
        .trim();

    if text.is_empty() {
        return Ok(ElicitResponse::Failed {
            reason: "powershell produced no stdout".into(),
        });
    }

    let parts: Vec<&str> = text.splitn(4, '|').collect();
    if parts.len() < 3 {
        return Ok(ElicitResponse::Failed {
            reason: format!("unexpected powershell output: {text:?}"),
        });
    }

    let status = parts[0];
    let entered = parts[2];
    let notes = parts.get(3).map(|s| s.to_string());

    match status {
        "answered" => {
            // `display`-style dialogs hand back text; the typed coercion into
            // the spec's FieldSpec kind happens centrally in
            // `render::dispatch` (this function has no access to the spec).
            Ok(ElicitResponse::Answered {
                value: crate::spec::FieldValue::Text(entered.to_string()),
                notes,
            })
        }
        "cancelled" => Ok(ElicitResponse::Cancelled {
            notes: if notes.as_ref().is_some_and(|s| !s.is_empty()) {
                notes
            } else {
                None
            },
        }),
        "timed_out" => Ok(ElicitResponse::TimedOut {
            elapsed_secs: elapsed.as_secs_f64(),
        }),
        "failed" => Ok(ElicitResponse::Failed {
            reason: entered.to_string(),
        }),
        other => Ok(ElicitResponse::Failed {
            reason: format!("unknown status '{other}' in powershell output"),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::{FieldSpec, Urgency};

    fn spec_text() -> PromptSpec {
        PromptSpec {
            details: None,
            title: "T".into(),
            question: "Q".into(),
            field: FieldSpec::Text {
                label: "l".into(),
                default: None,
                placeholder: None,
                max_length: None,
                secret: false,
                pattern: None,
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Info,
            timeout_secs: 60,
            request_id: None,
        }
    }

    #[test]
    fn build_includes_assemblies() {
        let s = build_script(&spec_text()).unwrap();
        assert!(s.contains("Add-Type -AssemblyName System.Windows.Forms"));
        assert!(s.contains("ShowDialog"));
    }

    #[test]
    fn build_uses_passwordchar_for_secret() {
        let mut spec = spec_text();
        spec.field = FieldSpec::Text {
            label: "tok".into(),
            default: None,
            placeholder: None,
            max_length: None,
            secret: true,
            pattern: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(s.contains("PasswordChar"));
    }

    #[test]
    fn parse_output_answered() {
        let r = parse_output(b"answered|OK|hello|", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_answered());
    }

    #[test]
    fn parse_output_cancelled() {
        let r = parse_output(b"cancelled|Cancel|||", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_cancelled());
    }

    #[test]
    fn parse_output_timeout_and_failure() {
        let t = parse_output(b"timed_out|||", b"", Duration::from_secs(2)).unwrap();
        assert!(t.is_timed_out());

        let f = parse_output(b"failed|Error|boom|", b"", Duration::from_secs(1)).unwrap();
        assert!(f.is_failed());

        let unknown = parse_output(b"weird|a|b|", b"", Duration::from_secs(1)).unwrap();
        assert!(unknown.is_failed(), "unknown status must not be treated as success");
    }

    #[test]
    fn parse_output_handles_malformed_without_panicking() {
        for raw in [&b""[..], b"onlyonefield", b"answered", b"answered|OK"] {
            let r = parse_output(raw, b"", Duration::from_secs(1)).unwrap();
            assert!(r.is_failed(), "expected Failed for {raw:?}");
        }
        // Non-utf8 stdout is an error, never a panic.
        assert!(parse_output(&[0xff, 0xfe, 0xfd], b"", Duration::from_secs(1)).is_err());
    }

    #[test]
    fn build_interpolates_default_and_placeholder() {
        // Regression: `default`, `placeholder` and the icon expression were
        // passed to format! but referenced nowhere in the template, which is a
        // hard error — the crate had never compiled for Windows. The values
        // were also silently dropped from the dialog.
        let mut spec = spec_text();
        spec.field = FieldSpec::Text {
            label: "l".into(),
            default: Some("prefilled".into()),
            placeholder: Some("hint".into()),
            max_length: None,
            secret: false,
            pattern: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(s.contains(r#""prefilled""#), "default must reach the script");
        assert!(s.contains(r#""hint""#), "placeholder must reach the script");
        assert!(s.contains("$txtField.Text = $fieldDefault"));
        assert!(s.contains("$txtField.PlaceholderText = $fieldPlaceholder"));
    }

    #[test]
    fn build_renders_urgency_as_label_colour() {
        let mut spec = spec_text();
        spec.urgency = Urgency::Error;
        let s = build_script(&spec).unwrap();
        assert!(s.contains("$lblQuestion.ForeColor"), "urgency must render");

        spec.urgency = Urgency::Info;
        let s = build_script(&spec).unwrap();
        assert!(!s.contains("$lblQuestion.ForeColor"), "info adds no colour");
    }

    #[test]
    fn build_escapes_button_labels_into_the_output_line() {
        let mut spec = spec_text();
        spec.buttons = Some(crate::spec::ButtonSpec {
            cancel: "Deny".into(),
            confirm: "Approve \"it\"".into(),
            default_is_cancel: false,
            defer_label: None,
        });
        let s = build_script(&spec).unwrap();
        // PowerShell escapes a double quote by doubling it.
        assert!(
            s.contains(r#""Approve ""it""""#),
            "button label must be escaped into the script: {s}"
        );
    }

    /// The Windows renderer cannot execute on this host, but its generated
    /// PowerShell is still text we can syntax-check wherever `pwsh` exists.
    /// `pwsh` cannot resolve WinForms types here, and that is fine: this
    /// asserts *parseability*, which is exactly the class of break the
    /// unused-argument bug lived in.
    #[test]
    fn generated_script_parses_under_powershell() {
        if std::process::Command::new("pwsh")
            .arg("-v")
            .output()
            .is_err()
        {
            eprintln!("SKIP: pwsh not installed; cannot syntax-check the script");
            return;
        }

        let script = build_script(&spec_text()).unwrap();
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("phinbox.ps1");
        std::fs::write(&path, &script).unwrap();

        let check = format!(
            "$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('{}',[ref]$null,[ref]$e); \
             if($e){{ $e | ForEach-Object {{ Write-Output $_.Message }}; exit 1 }}",
            path.display()
        );
        let out = std::process::Command::new("pwsh")
            .args(["-NoProfile", "-NonInteractive", "-Command", &check])
            .output()
            .expect("run pwsh");

        assert!(
            out.status.success(),
            "generated PowerShell has parse errors: {}\n{script}",
            String::from_utf8_lossy(&out.stdout)
        );
    }
}