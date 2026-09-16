//! The agent-authored prompt spec and the human-returned response.
//!
//! These types are the **contract** between the agent and the popup.
//! Both surfaces serialize via serde; the JSON Schema is exported by
//! [`crate::schema`] for the MCP server's `inputSchema` / `outputSchema`.

mod types;
mod validate;

pub use types::*;

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_text() -> PromptSpec {
        PromptSpec {
            title: "Test".into(),
            question: "?".into(),
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
            urgency: Urgency::default(),
            timeout_secs: default_timeout_secs(),
            request_id: None,
        }
    }

    #[test]
    fn validate_accepts_minimal() {
        assert!(minimal_text().validate().is_ok());
    }

    #[test]
    fn validate_rejects_empty_title() {
        let mut s = minimal_text();
        s.title = String::new();
        assert!(s.validate().is_err());
    }

    #[test]
    fn validate_rejects_long_title() {
        let mut s = minimal_text();
        s.title = "x".repeat(81);
        assert!(s.validate().is_err());
    }

    #[test]
    fn validate_rejects_empty_choice() {
        let mut s = minimal_text();
        s.field = FieldSpec::Choice {
            label: "pick".into(),
            options: vec![],
            default_index: None,
        };
        assert!(s.validate().is_err());
    }

    #[test]
    fn validate_rejects_bad_default_index() {
        let mut s = minimal_text();
        s.field = FieldSpec::Choice {
            label: "pick".into(),
            options: vec![ChoiceOption {
                value: "a".into(),
                label: "A".into(),
                description: None,
            }],
            default_index: Some(5),
        };
        assert!(s.validate().is_err());
    }

    #[test]
    fn validate_rejects_bad_regex() {
        let mut s = minimal_text();
        s.field = FieldSpec::Text {
            label: "x".into(),
            default: None,
            placeholder: None,
            max_length: None,
            secret: false,
            pattern: Some("[unclosed".into()),
        };
        assert!(s.validate().is_err());
    }

    #[test]
    fn response_predicates() {
        let ans = ElicitResponse::Answered {
            value: FieldValue::Text("hi".into()),
            notes: None,
        };
        assert!(ans.is_answered());
        assert!(!ans.is_cancelled());

        let can = ElicitResponse::Cancelled { notes: None };
        assert!(can.is_cancelled());
        assert!(!can.is_answered());

        let to = ElicitResponse::TimedOut { elapsed_secs: 1.0 };
        assert!(to.is_timed_out());

        let f = ElicitResponse::Failed { reason: "x".into() };
        assert!(f.is_failed());
    }

    #[test]
    fn serde_roundtrip_text() {
        let s = minimal_text();
        let json = serde_json::to_string(&s).unwrap();
        let back: PromptSpec = serde_json::from_str(&json).unwrap();
        assert_eq!(back.title, s.title);
    }

    #[test]
    fn serde_roundtrip_choice() {
        let s = PromptSpec {
            field: FieldSpec::Choice {
                label: "target".into(),
                options: vec![
                    ChoiceOption {
                        value: "staging".into(),
                        label: "Staging".into(),
                        description: Some("preprod".into()),
                    },
                    ChoiceOption {
                        value: "prod".into(),
                        label: "Production".into(),
                        description: None,
                    },
                ],
                default_index: Some(0),
            },
            ..minimal_text()
        };
        let json = serde_json::to_string(&s).unwrap();
        let back: PromptSpec = serde_json::from_str(&json).unwrap();
        if let FieldSpec::Choice { options, .. } = &back.field {
            assert_eq!(options.len(), 2);
            assert_eq!(options[0].value, "staging");
        } else {
            panic!("round-trip lost choice variant");
        }
    }
}
