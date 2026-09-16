//! Integration tests for the phinbox library.

use phinbox::spec::{
    ButtonSpec, ChoiceOption, DateTimeKind, ElicitResponse, FieldSpec, FieldValue, NotesSpec,
    PromptSpec, Urgency,
};
use phinbox::{ElicitOptions, RendererPreference};

fn bool_spec(label: &str, default: Option<bool>) -> PromptSpec {
    PromptSpec {
        title: "T".into(),
        question: "Q".into(),
        field: FieldSpec::Boolean {
            label: label.into(),
            default,
        },
        notes: None,
        buttons: None,
        urgency: Urgency::Info,
        timeout_secs: 5,
        request_id: None,
    }
}

#[test]
fn schema_roundtrip_simple_boolean() {
    let spec = bool_spec("yes?", Some(true));
    let json = serde_json::to_string(&spec).unwrap();
    let back: PromptSpec = serde_json::from_str(&json).unwrap();
    assert_eq!(back.title, "T");
}

#[test]
fn schema_roundtrip_choice() {
    let spec = PromptSpec {
        title: "pick".into(),
        question: "?".into(),
        field: FieldSpec::Choice {
            label: "target".into(),
            options: vec![ChoiceOption {
                value: "a".into(),
                label: "A".into(),
                description: None,
            }],
            default_index: Some(0),
        },
        notes: Some(NotesSpec {
            label: "why".into(),
            default: None,
            max_length: None,
            required: false,
        }),
        buttons: Some(ButtonSpec {
            cancel: "Cancel".into(),
            confirm: "OK".into(),
            default_is_cancel: false,
        }),
        urgency: Urgency::Warning,
        timeout_secs: 60,
        request_id: None,
    };
    let json = serde_json::to_string(&spec).unwrap();
    let back: PromptSpec = serde_json::from_str(&json).unwrap();
    if let FieldSpec::Choice { options, .. } = &back.field {
        assert_eq!(options.len(), 1);
    } else {
        panic!("lost variant");
    }
}

#[test]
fn schema_roundtrip_datetime() {
    let spec = PromptSpec {
        title: "when".into(),
        question: "?".into(),
        field: FieldSpec::DateTime {
            label: "at".into(),
            default: Some("2026-07-21T10:00:00Z".into()),
            picker_kind: DateTimeKind::DateTime,
        },
        notes: None,
        buttons: None,
        urgency: Urgency::Info,
        timeout_secs: 60,
        request_id: None,
    };
    let json = serde_json::to_string(&spec).unwrap();
    let back: PromptSpec = serde_json::from_str(&json).unwrap();
    if let FieldSpec::DateTime { picker_kind, .. } = &back.field {
        assert!(matches!(picker_kind, DateTimeKind::DateTime));
    } else {
        panic!("lost variant");
    }
}

#[test]
fn response_predicates_work() {
    let r1 = ElicitResponse::Answered {
        value: FieldValue::Boolean(true),
        notes: None,
    };
    assert!(r1.is_answered());
    assert!(!r1.is_cancelled());

    let r2 = ElicitResponse::Cancelled { notes: None };
    assert!(r2.is_cancelled());

    let r3 = ElicitResponse::TimedOut { elapsed_secs: 1.0 };
    assert!(r3.is_timed_out());

    let r4 = ElicitResponse::Failed {
        reason: "x".into(),
    };
    assert!(r4.is_failed());
}

#[test]
fn fixture_files_parse() {
    let dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures");
    for entry in std::fs::read_dir(&dir).unwrap() {
        let entry = entry.unwrap();
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) != Some("json") {
            continue;
        }
        let text = std::fs::read_to_string(&path).unwrap();
        let spec: PromptSpec = serde_json::from_str(&text)
            .unwrap_or_else(|e| panic!("failed to parse {}: {e}", path.display()));
        spec.validate().unwrap_or_else(|e| {
            panic!("invalid spec in {}: {e}", path.display())
        });
    }
}

#[test]
fn options_default_renderer_is_auto_gui() {
    let o = ElicitOptions::default();
    assert!(matches!(o.renderer, RendererPreference::AutoGui));
}