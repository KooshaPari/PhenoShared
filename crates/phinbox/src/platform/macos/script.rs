use crate::error::ElicitError;
use crate::escape::applescript_escape;
use crate::spec::{FieldSpec, PromptSpec, Urgency};

/// Build the `AppleScript` source for a `display dialog` call.
pub(super) fn build_script(spec: &PromptSpec) -> Result<String, ElicitError> {
    let body = applescript_escape(&spec.question)?;
    let title = applescript_escape(&format!("phinbox · {}", spec.title))?;

    let default = match &spec.field {
        FieldSpec::Text { default, .. } => default.clone().unwrap_or_default(),
        FieldSpec::LongText { default, .. } => default.clone().unwrap_or_default(),
        FieldSpec::Integer { default, .. } => default.map(|v| v.to_string()).unwrap_or_default(),
        _ => String::new(),
    };
    // Text-bearing fields always render an answer box so `text returned`
    // exists; Boolean/Choice are button-only and must not pass `default answer`.
    let has_answer_box = matches!(
        &spec.field,
        FieldSpec::Text { .. }
            | FieldSpec::LongText { .. }
            | FieldSpec::Integer { .. }
            | FieldSpec::DateTime { .. }
    );
    let default_arg = if has_answer_box {
        if default.is_empty() {
            " default answer \"\"".to_string()
        } else {
            format!(" default answer {}", applescript_escape(&default)?)
        }
    } else {
        String::new()
    };

    let icon = match spec.urgency {
        Urgency::Info => "note",
        Urgency::Warning => "caution",
        Urgency::Error => "stop",
        Urgency::Secret => "caution",
    };

    let (cancel_label, confirm_label) = spec
        .buttons
        .as_ref().map_or_else(|| ("Cancel".to_string(), "OK".to_string()), |b| (b.cancel.clone(), b.confirm.clone()));

    let timeout_clause = if spec.timeout_secs == 0 {
        String::new()
    } else {
        format!(" giving up after {}", spec.timeout_secs)
    };

    let hidden_clause = match &spec.field {
        FieldSpec::Text { secret: true, .. } => " with hidden answer",
        _ => "",
    };

    // `display dialog` only has a `text returned` property when it was
    // invoked with `default answer` (see has_answer_box above). Reading it
    // on a button-only dialog raises "Can't get text returned".
    let text_extract = if has_answer_box {
        "set theText to text returned of theResponse"
    } else {
        "set theText to \"\""
    };

    let script = format!(
        r#"
try
    set theResponse to display dialog {body} with title {title}{default_arg} with icon {icon}{hidden_clause} buttons {{{cancel_q}, {confirm_q}}} default button {default_btn}{timeout_clause}
    if gave up of theResponse then
        return "timed_out|||"
    end if
    set theButton to button returned of theResponse
    {text_extract}
    if theButton is {confirm_q} then
        return "answered|" & theButton & "|" & theText & "|"
    else
        return "cancelled|" & theButton & "|" & theText & "|"
    end if
on error errMsg number errNum
    if errNum is -128 then
        return "cancelled|Cancel|||"
    else
        return "failed|Error|" & errMsg & "|"
    end if
end try
"#,
        body = body,
        title = title,
        default_arg = default_arg,
        icon = icon,
        hidden_clause = hidden_clause,
        text_extract = text_extract,
        cancel_q = applescript_escape(&cancel_label)?,
        confirm_q = applescript_escape(&confirm_label)?,
        default_btn = if spec
            .buttons
            .as_ref()
            .is_some_and(|b| b.default_is_cancel)
        {
            applescript_escape(&cancel_label)?
        } else {
            applescript_escape(&confirm_label)?
        },
        timeout_clause = timeout_clause,
    );

    Ok(script)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::{FieldSpec, PromptSpec, Urgency};

    #[test]
    fn script_guards_gave_up_before_reading_button() {
        // On AppleScript timeout the response record has `gave up:true`
        // and no `button returned`; reading it would throw. The guard must
        // come first and map to the "timed_out" wire status.
        let spec = PromptSpec {
            details: None,
            title: "T".into(),
            question: "?".into(),
            field: FieldSpec::Boolean {
                label: "b".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Info,
            timeout_secs: 5,
            request_id: None,
        };
        let s = build_script(&spec).unwrap();
        let guard = s.find("if gave up of theResponse").expect("gave-up guard");
        let btn = s
            .find("set theButton to button returned")
            .expect("button read");
        assert!(guard < btn, "gave-up guard must precede button read: {s}");
        assert!(s.contains(r#"return "timed_out|||""#));
    }

    #[test]
    fn button_only_dialog_does_not_read_text_returned() {
        // Regression: `text returned` only exists when `default answer`
        // is passed. On a Boolean/Choice dialog (no answer box) reading it
        // raised "Can't get text returned" and failed the whole popup.
        let spec = PromptSpec {
            details: None,
            title: "Approve".into(),
            question: "OK to proceed?".into(),
            field: FieldSpec::Boolean {
                label: "yes?".into(),
                default: Some(false),
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Error,
            timeout_secs: 60,
            request_id: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(
            !s.contains("text returned"),
            "button-only dialog must not reference 'text returned': {s}"
        );
        assert!(s.contains("set theText to \"\""));

        // Text-field dialogs keep reading the answer box.
        let text_spec = PromptSpec {
            details: None,
            title: "Name".into(),
            question: "Who?".into(),
            field: FieldSpec::Text {
                label: "name".into(),
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
        };
        let s2 = build_script(&text_spec).unwrap();
        assert!(s2.contains("text returned of theResponse"));
    }

    #[test]
    fn script_includes_title_and_question() {
        let spec = PromptSpec {
            details: None,
            title: "Test".into(),
            question: "What?".into(),
            field: FieldSpec::Boolean {
                label: "yes?".into(),
                default: Some(true),
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Warning,
            timeout_secs: 60,
            request_id: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(s.contains("display dialog"));
        assert!(s.contains("Test"));
        assert!(s.contains("What?"));
        assert!(s.contains("caution"));
    }

    #[test]
    fn script_uses_hidden_answer_for_secret() {
        let spec = PromptSpec {
            details: None,
            title: "Token".into(),
            question: "Enter token".into(),
            field: FieldSpec::Text {
                label: "token".into(),
                default: None,
                placeholder: None,
                max_length: None,
                secret: true,
                pattern: None,
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Secret,
            timeout_secs: 60,
            request_id: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(s.contains("with hidden answer"));
    }

    #[test]
    fn script_includes_timeout_clause() {
        let spec = PromptSpec {
            details: None,
            title: "t".into(),
            question: "q".into(),
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
            timeout_secs: 30,
            request_id: None,
        };
        let s = build_script(&spec).unwrap();
        assert!(s.contains("giving up after 30"));
    }
}
