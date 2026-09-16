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
    let default_arg = if default.is_empty() {
        String::new()
    } else {
        format!(" default answer {}", applescript_escape(&default)?)
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

    let script = format!(
        r#"
try
    set theResponse to display dialog {body} with title {title}{default_arg} with icon {icon}{hidden_clause} buttons {{{cancel_q}, {confirm_q}}} default button {default_btn}{timeout_clause}
    set theButton to button returned of theResponse
    set theText to text returned of theResponse
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
    fn script_includes_title_and_question() {
        let spec = PromptSpec {
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
