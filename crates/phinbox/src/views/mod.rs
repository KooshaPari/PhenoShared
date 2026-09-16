//! HTML and plain-text renderers for the inbox web frontend.
//!
//! ## Submodules
//!
//! - `css` — compiled, minified CSS for the inbox web frontend
//! - `helpers` — HTML escape/attr utilities, format helpers, urgency/field label mappers
//! - `html` — HTML page renderers (inbox index, form detail, answer confirmation)

pub mod css;
pub mod helpers;
pub mod html;

pub use css::full_html_css;
pub use helpers::{
    field_kind_label, format_age, html_attr, html_escape, truncate, unix_now_ms_diff,
    urgency_class, urgency_label, INBOX_SLUG,
};
pub use html::{
    render_answer_html, render_expired_html, render_field_widget, render_form_html,
    render_full_html, render_inbox_index_html, render_plain_text, render_summary,
    render_summary_json,
};

// ---- tests ---------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::inbox::{PendingRequest, RequestOrigin};
    use crate::spec::{FieldSpec, PromptSpec, Urgency};

    fn sample_pending(id: &str, urgent: Urgency) -> PendingRequest {
        PendingRequest {
            request_id: id.into(),
            queued_at_ms: 1_700_000_000_000,
            expires_at_ms: 1_700_000_060_000,
            origin: RequestOrigin {
                hostname: "test-host".into(),
                process: "phinbox-test".into(),
                pid: 12345,
                callback: None,
            },
            spec: PromptSpec {
                title: "What is your favorite color?".into(),
                question: "Please answer honestly.".into(),
                field: FieldSpec::Text {
                    label: "Color".into(),
                    placeholder: None,
                    default: None,
                    secret: false,
                    pattern: None,
                    max_length: None,
                },
                notes: None,
                buttons: None,
                urgency: urgent,
                timeout_secs: 60,
                request_id: Some(id.into()),
            },
            response: None,
            state: crate::inbox::RequestState::Pending,
            notified_via: vec![],
            metadata: Default::default(),
        }
    }

    fn snapshot_contains(haystack: &str, needles: &[&str]) -> bool {
        needles.iter().all(|n| haystack.contains(n))
    }

    #[test]
    fn index_empty() {
        let html = render_inbox_index_html(&[]);
        assert!(snapshot_contains(
            &html,
            &["No pending requests", "phinbox",]
        ));
        assert!(html.contains("</html>"));
    }

    #[test]
    fn index_with_pending() {
        let reqs = vec![sample_pending("r1", Urgency::Info)];
        let html = render_inbox_index_html(&reqs);
        assert!(snapshot_contains(
            &html,
            &[
                "r1",
                "What is your favorite color?",
                "Info",
            ]
        ));
        assert!(html.contains("</html>"));
    }

    #[test]
    fn index_multiple_requests() {
        let reqs = vec![
            sample_pending("a", Urgency::Info),
            sample_pending("b", Urgency::Warning),
            sample_pending("c", Urgency::Error),
        ];
        let html = render_inbox_index_html(&reqs);
        assert!(html.matches("<a href=").count() >= 3);
        assert!(html.contains("class=card warn"));
        assert!(html.contains("urgent"));
    }

    #[test]
    fn form_detail_has_nav() {
        let req = sample_pending("det1", Urgency::Info);
        let html = render_form_html(&req);
        assert!(html.contains("&larr;"));
        assert!(html.contains("href=/inbox"));
        assert!(html.contains("What is your favorite color?"));
    }

    #[test]
    fn answer_success() {
        let html = render_answer_html("r99", true, "Your answer was recorded.");
        assert!(html.contains("Answer received"));
        assert!(html.contains("Your answer was recorded."));
        assert!(html.contains("Return to inbox"));
    }

    #[test]
    fn answer_failure() {
        let html = render_answer_html("r99", false, "Invalid value.");
        assert!(html.contains("Failed to record answer"));
        assert!(html.contains("\u{274C}"));
    }

    #[test]
    fn css_dark_mode_prefers() {
        let css = full_html_css();
        assert!(css.contains("prefers-color-scheme:dark"));
        assert!(css.contains("background:#1c1c1e"));
        assert!(css.contains("color:#f5f5f7"));
    }

    #[test]
    fn css_responsive() {
        let css = full_html_css();
        assert!(css.contains("max-width:720px"));
        assert!(css.contains("max-width:480px"));
    }

    #[test]
    fn form_emits_post_action() {
        let req = sample_pending("rid-form-post", Urgency::Info);
        let html = render_form_html(&req);
        assert!(
            html.contains(r#"<form method=POST action=/inbox/rid-form-post/answer"#),
            "form must post to /inbox/{{rid}}/answer, got: {html}"
        );
        assert!(html.contains(r#"name=confirm value=ok"#));
        assert!(html.contains(r#"name=cancel value=1"#));
    }

    #[test]
    fn text_field_renders_input() {
        let mut req = sample_pending("rid-text", Urgency::Info);
        req.spec.field = FieldSpec::Text {
            label: "Color".into(),
            placeholder: Some("e.g. blue".into()),
            default: Some("blue".into()),
            max_length: Some(64),
            secret: false,
            pattern: None,
        };
        let html = render_form_html(&req);
        assert!(
            html.contains(r#"<input id=eli-field type=text name=value"#),
            "Text must emit <input type=text name=value ...>: {html}"
        );
        assert!(html.contains(r#"placeholder="e.g. blue""#));
        assert!(html.contains(r#"value="blue""#));
        assert!(html.contains(r#"maxlength="64""#));
        req.spec.field = FieldSpec::Text {
            label: "PIN".into(),
            placeholder: None,
            default: None,
            max_length: None,
            secret: true,
            pattern: None,
        };
        let html_secret = render_form_html(&req);
        assert!(
            html_secret.contains(r#"type=password"#),
            "secret=true must emit type=password: {html_secret}"
        );
    }

    #[test]
    fn choice_field_renders_select() {
        let mut req = sample_pending("rid-choice", Urgency::Info);
        req.spec.field = FieldSpec::Choice {
            label: "Environment".into(),
            options: vec![
                crate::spec::ChoiceOption {
                    value: "staging".into(),
                    label: "Staging".into(),
                    description: None,
                },
                crate::spec::ChoiceOption {
                    value: "prod".into(),
                    label: "Production".into(),
                    description: None,
                },
            ],
            default_index: Some(1),
        };
        let html = render_form_html(&req);
        assert!(
            html.contains(r#"<select id=eli-field name=value required>"#),
            "Choice must emit <select name=value>: {html}"
        );
        assert!(html.contains(r#"<option value="staging""#));
        assert!(html.contains(r#"<option value="prod" selected"#));
        assert!(html.contains(r#"<option value="staging">Staging</option>"#));
        assert!(html.contains(
            r#"<option value="prod" selected>Production</option>"#
        ));
    }

    #[test]
    fn boolean_field_renders_checkbox() {
        let mut req = sample_pending("rid-bool", Urgency::Info);
        req.spec.field = FieldSpec::Boolean {
            label: "Proceed?".into(),
            default: Some(true),
        };
        let html = render_form_html(&req);
        assert!(
            html.contains(r#"<input type=checkbox name=boolean value=on checked>"#),
            "Boolean default=true must emit checked: {html}"
        );
        assert!(html.contains("Proceed?"));
        req.spec.field = FieldSpec::Boolean {
            label: "Proceed?".into(),
            default: Some(false),
        };
        let html_false = render_form_html(&req);
        assert!(
            html_false.contains(r#"<input type=checkbox name=boolean value=on>"#),
            "Boolean default=false must not be checked: {html_false}"
        );
        assert!(!html_false.contains("checked"));
    }
}
