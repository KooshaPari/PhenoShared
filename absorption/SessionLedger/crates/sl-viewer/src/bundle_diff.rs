//! Bundle diff panel — compare two OKF bundles side-by-side.
//!
//! The [`diff_fields`] function is a pure function that can be unit-tested
//! independently of Dioxus.  The [`BundleDiff`] component consumes its output
//! and renders a split-pane view with highlighted differences.

use dioxus::prelude::*;
use session_ledger::domain::bundle::{BundleKind, ContinuationBundle};

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// Lightweight flat representation of key OKF fields.
#[derive(Debug, Clone, PartialEq)]
pub struct OkfBundle {
    pub source_id: String,
    /// Total token estimate (sum of `user_turn_count` across Intent bundles).
    pub token_count: u64,
    /// Number of raw sub-bundles (slices) in the continuation bundle.
    pub message_count: usize,
    /// Wall-clock duration in ms if stored in Context; 0 if absent.
    pub duration_ms: u64,
    /// Model name from Context body, if present.
    pub model: Option<String>,
    /// ISO-8601 created_at from Context body, if present.
    pub created_at: Option<String>,
    /// Primary goal string from Intent bundle.
    pub goal: Option<String>,
    /// Whether an Acceptance slice is present.
    pub has_acceptance: bool,
    /// Whether a Contract slice is present.
    pub has_contract: bool,
}

impl OkfBundle {
    /// Derive an [`OkfBundle`] from a compiled [`ContinuationBundle`].
    #[must_use]
    pub fn from_bundle(cb: &ContinuationBundle) -> Self {
        let intent = cb.bundles.iter().find(|b| b.kind == BundleKind::Intent);
        let context = cb.bundles.iter().find(|b| b.kind == BundleKind::Context);

        let token_count = intent
            .and_then(|b| b.body.get("user_turn_count"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0);

        let goal =
            intent.and_then(|b| b.body.get("goal")).and_then(|v| v.as_str()).map(str::to_owned);

        let duration_ms =
            context.and_then(|b| b.body.get("duration_ms")).and_then(|v| v.as_u64()).unwrap_or(0);

        let model =
            context.and_then(|b| b.body.get("model")).and_then(|v| v.as_str()).map(str::to_owned);

        let created_at = context
            .and_then(|b| b.body.get("created_at"))
            .and_then(|v| v.as_str())
            .map(str::to_owned);

        OkfBundle {
            source_id: cb.source_id.clone(),
            token_count,
            message_count: cb.bundles.len(),
            duration_ms,
            model,
            created_at,
            goal,
            has_acceptance: cb.has(BundleKind::Acceptance),
            has_contract: cb.has(BundleKind::Contract),
        }
    }
}

// ---------------------------------------------------------------------------
// Diff logic (pure, testable)
// ---------------------------------------------------------------------------

/// One compared field.
#[derive(Debug, Clone, PartialEq)]
pub struct FieldDiff {
    pub name: &'static str,
    pub value_a: String,
    pub value_b: String,
    /// `true` when the two values differ.
    pub differs: bool,
}

impl FieldDiff {
    fn new(name: &'static str, a: impl ToString, b: impl ToString) -> Self {
        let value_a = a.to_string();
        let value_b = b.to_string();
        let differs = value_a != value_b;
        FieldDiff { name, value_a, value_b, differs }
    }
}

/// Produce a field-by-field diff of two [`OkfBundle`]s.
///
/// Pure function — no I/O, no Dioxus.
#[must_use]
pub fn diff_fields(a: &OkfBundle, b: &OkfBundle) -> Vec<FieldDiff> {
    vec![
        FieldDiff::new("source_id", &a.source_id, &b.source_id),
        FieldDiff::new("token_count", a.token_count, b.token_count),
        FieldDiff::new("message_count", a.message_count, b.message_count),
        FieldDiff::new("duration_ms", a.duration_ms, b.duration_ms),
        FieldDiff::new(
            "model",
            a.model.as_deref().unwrap_or("—"),
            b.model.as_deref().unwrap_or("—"),
        ),
        FieldDiff::new(
            "created_at",
            a.created_at.as_deref().unwrap_or("—"),
            b.created_at.as_deref().unwrap_or("—"),
        ),
        FieldDiff::new("goal", a.goal.as_deref().unwrap_or("—"), b.goal.as_deref().unwrap_or("—")),
        FieldDiff::new("has_acceptance", a.has_acceptance, b.has_acceptance),
        FieldDiff::new("has_contract", a.has_contract, b.has_contract),
    ]
}

// ---------------------------------------------------------------------------
// Dioxus component
// ---------------------------------------------------------------------------

/// Props for [`BundleDiff`].
#[derive(Props, Clone, PartialEq)]
pub struct BundleDiffProps {
    pub bundle_a: OkfBundle,
    pub bundle_b: OkfBundle,
    /// Called when the user dismisses the diff panel.
    pub on_close: EventHandler<()>,
}

/// Split-pane diff panel comparing two OKF bundles.
///
/// Rows with differing values are highlighted.
#[component]
pub fn BundleDiff(props: BundleDiffProps) -> Element {
    let diffs = diff_fields(&props.bundle_a, &props.bundle_b);
    let diff_count = diffs.iter().filter(|d| d.differs).count();

    rsx! {
        div {
            class: "diff-panel",
            onkeydown: move |evt: Event<KeyboardData>| {
                if evt.key() == Key::Escape {
                    evt.prevent_default();
                    props.on_close.call(());
                }
            },
            div { class: "diff-header",
                span { class: "diff-title",
                    "Comparing bundles"
                    if diff_count > 0 {
                        span { class: "diff-badge", " {diff_count} changed" }
                    } else {
                        span { class: "diff-badge diff-badge-same", " identical" }
                    }
                }
                button {
                    class: "diff-close",
                    r#type: "button",
                    "aria-label": "Close bundle comparison",
                    style: "border:0;background:transparent;",
                    onclick: move |_| props.on_close.call(()),
                    "✕"
                }
            }
            div { class: "diff-col-headers",
                div { class: "diff-field-label", "Field" }
                div { class: "diff-col-a", "A · {props.bundle_a.source_id}" }
                div { class: "diff-col-b", "B · {props.bundle_b.source_id}" }
            }
            div { class: "diff-rows",
                for field in diffs.iter() {
                    div {
                        class: if field.differs { "diff-row diff-row-changed" } else { "diff-row" },
                        div { class: "diff-field-label", "{field.name}" }
                        div { class: "diff-col-a", "{field.value_a}" }
                        div { class: "diff-col-b", "{field.value_b}" }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_bundle(source_id: &str, token_count: u64, model: Option<&str>) -> OkfBundle {
        OkfBundle {
            source_id: source_id.to_owned(),
            token_count,
            message_count: 3,
            duration_ms: 0,
            model: model.map(str::to_owned),
            created_at: None,
            goal: Some("test goal".to_owned()),
            has_acceptance: true,
            has_contract: false,
        }
    }

    #[test]
    fn diff_identical_bundles_has_no_differences() {
        let a = make_bundle("sess-001", 100, Some("claude-3-5-sonnet"));
        let b = a.clone();
        let diffs = diff_fields(&a, &b);
        assert!(
            diffs.iter().all(|d| !d.differs),
            "expected 0 differences, got: {:?}",
            diffs.iter().filter(|d| d.differs).collect::<Vec<_>>()
        );
    }

    #[test]
    fn diff_detects_token_count_change() {
        let a = make_bundle("sess-001", 100, Some("gpt-4o"));
        let b = make_bundle("sess-001", 200, Some("gpt-4o"));
        let diffs = diff_fields(&a, &b);
        let token_diff = diffs.iter().find(|d| d.name == "token_count").unwrap();
        assert!(token_diff.differs);
        assert_eq!(token_diff.value_a, "100");
        assert_eq!(token_diff.value_b, "200");
    }

    #[test]
    fn diff_detects_model_change() {
        let a = make_bundle("sess-001", 50, Some("claude-3-5-sonnet"));
        let b = make_bundle("sess-001", 50, Some("gpt-4o"));
        let diffs = diff_fields(&a, &b);
        let model_diff = diffs.iter().find(|d| d.name == "model").unwrap();
        assert!(model_diff.differs);
        assert_eq!(model_diff.value_a, "claude-3-5-sonnet");
        assert_eq!(model_diff.value_b, "gpt-4o");
    }

    #[test]
    fn diff_absent_model_shown_as_dash() {
        let a = make_bundle("sess-001", 50, None);
        let b = make_bundle("sess-001", 50, None);
        let diffs = diff_fields(&a, &b);
        let model_diff = diffs.iter().find(|d| d.name == "model").unwrap();
        assert!(!model_diff.differs);
        assert_eq!(model_diff.value_a, "—");
    }

    #[test]
    fn diff_detects_source_id_change() {
        let a = make_bundle("sess-A", 50, None);
        let b = make_bundle("sess-B", 50, None);
        let diffs = diff_fields(&a, &b);
        let id_diff = diffs.iter().find(|d| d.name == "source_id").unwrap();
        assert!(id_diff.differs);
    }

    #[test]
    fn from_bundle_derives_token_count_from_intent() {
        use session_ledger::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
        let cb = ContinuationBundle {
            source_id: "test-123".into(),
            bundles: vec![
                Bundle::new(
                    BundleKind::Intent,
                    serde_json::json!({"goal": "do work", "user_turn_count": 7}),
                ),
                Bundle::new(BundleKind::Acceptance, serde_json::json!({"ready": true})),
            ],
        };
        let okf = OkfBundle::from_bundle(&cb);
        assert_eq!(okf.token_count, 7);
        assert_eq!(okf.message_count, 2);
        assert!(okf.has_acceptance);
        assert!(!okf.has_contract);
    }
}
