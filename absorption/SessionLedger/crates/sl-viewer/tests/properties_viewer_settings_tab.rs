//! Property evidence for sl-viewer's `settings_tab::HealthStatus` enum
//! and `settings_tab::THEME_RADIO_GROUP_ID` DOM-id constant.
//!
//! The settings tab is the persistence-backed operator preference
//! surface. If `HealthStatus::label()` drifts or the radio-group DOM id
//! changes, the in-app "Focus theme toggle" button and the
//! `data-testid` lookups for the daemon probe stop working. Every
//! visible property is pinned here.
//!
//! `settings_tab::HealthStatus` invariants:
//!  * Every variant has a non-empty `label()`.
//!  * Every `label()` is distinct across variants so the UI can
//!    decide between healthy / unreachable / checking without
//!    ambiguity.
//!  * `label()` is deterministic across calls.
//!  * The labels are kebab-case-ish (lowercase ASCII letters, no
//!    whitespace, no tabs / newlines) so they render as a single
//!    `data-testid` / aria-label.
//!
//! `settings_tab::THEME_RADIO_GROUP_ID` invariants:
//!  * Non-empty.
//!  * Kebab-case ASCII (DOM id + JS selector).
//!  * Distinct from the `FORGE_DB_HINT_STORAGE_KEY` SSOT.

use proptest::prelude::*;
use sl_viewer::corpus_cta::FORGE_DB_HINT_STORAGE_KEY;
use sl_viewer::settings_tab::{HealthStatus, THEME_RADIO_GROUP_ID};

// ── HealthStatus ────────────────────────────────────────────────────────────

proptest! {
    /// `HealthStatus::Unknown.label()` is `"checking"`.
    #[test]
    fn health_status_unknown_label(_seed in any::<u32>()) {
        prop_assert_eq!(HealthStatus::Unknown.label(), "checking");
    }

    /// `HealthStatus::Healthy.label()` is `"healthy"`.
    #[test]
    fn health_status_healthy_label(_seed in any::<u32>()) {
        prop_assert_eq!(HealthStatus::Healthy.label(), "healthy");
    }

    /// `HealthStatus::Unreachable.label()` is `"unreachable"`.
    #[test]
    fn health_status_unreachable_label(_seed in any::<u32>()) {
        prop_assert_eq!(HealthStatus::Unreachable.label(), "unreachable");
    }

    /// Every variant's label is non-empty.
    #[test]
    fn health_status_labels_nonempty(variant in prop::sample::select(vec![
        HealthStatus::Unknown,
        HealthStatus::Healthy,
        HealthStatus::Unreachable,
    ])) {
        let label = variant.label();
        prop_assert!(!label.is_empty(), "{variant:?} label is empty");
    }

    /// Every variant's label is distinct across variants so the UI
    /// can branch on the label without ambiguity.
    #[test]
    fn health_status_labels_distinct(_seed in any::<u32>()) {
        let labels = [
            HealthStatus::Unknown.label(),
            HealthStatus::Healthy.label(),
            HealthStatus::Unreachable.label(),
        ];
        let mut deduped = labels.to_vec();
        deduped.sort();
        deduped.dedup();
        prop_assert_eq!(deduped.len(), labels.len());
    }

    /// Every label is single-line (no tabs / newlines).
    #[test]
    fn health_status_labels_singleline(variant in prop::sample::select(vec![
        HealthStatus::Unknown,
        HealthStatus::Healthy,
        HealthStatus::Unreachable,
    ])) {
        let label = variant.label();
        prop_assert!(!label.contains('\n'));
        prop_assert!(!label.contains('\t'));
    }

    /// Every label is lowercase ASCII letters (matches the
    /// `data-testid` contract).
    #[test]
    fn health_status_labels_kebab_case(variant in prop::sample::select(vec![
        HealthStatus::Unknown,
        HealthStatus::Healthy,
        HealthStatus::Unreachable,
    ])) {
        let label = variant.label();
        let valid = label.chars().all(|ch| ch.is_ascii_lowercase());
        prop_assert!(valid, "label {label:?} is not lowercase ASCII");
    }

    /// `label()` is deterministic across calls.
    #[test]
    fn health_status_label_deterministic(variant in prop::sample::select(vec![
        HealthStatus::Unknown,
        HealthStatus::Healthy,
        HealthStatus::Unreachable,
    ])) {
        prop_assert_eq!(variant.label(), variant.label());
    }
}

// ── THEME_RADIO_GROUP_ID ────────────────────────────────────────────────────

proptest! {
    /// `THEME_RADIO_GROUP_ID` is non-empty.
    #[test]
    fn theme_radio_group_id_nonempty(_seed in any::<u32>()) {
        prop_assert!(!THEME_RADIO_GROUP_ID.is_empty());
    }

    /// `THEME_RADIO_GROUP_ID` is kebab-case ASCII so the
    /// `getElementById` /
    /// `document.querySelector("#…")` paths always resolve.
    #[test]
    fn theme_radio_group_id_is_kebab_case(_seed in any::<u32>()) {
        let valid = THEME_RADIO_GROUP_ID
            .chars()
            .all(|ch| ch.is_ascii_lowercase() || ch.is_ascii_digit() || ch == '-');
        prop_assert!(valid, "id {:?} is not kebab-case ASCII", THEME_RADIO_GROUP_ID);
    }

    /// `THEME_RADIO_GROUP_ID` is distinct from the `FORGE_DB_HINT_STORAGE_KEY`
    /// SSOT so the picker never confuses the two storage keys.
    #[test]
    fn theme_radio_group_id_distinct_from_storage_key(_seed in any::<u32>()) {
        prop_assert_ne!(THEME_RADIO_GROUP_ID, FORGE_DB_HINT_STORAGE_KEY);
    }
}
