//! The continuation bundle model.
//!
//! A [`ContinuationBundle`] is the canonical, injectable artifact for lossless
//! resume of an agent session in a NEW session. It is an ordered set of typed
//! [`Bundle`]s plus an `Acceptance` gate.
//!
//! Bundle kinds (owner's four + three proposed extensions, justified in
//! `docs/DESIGN.md`):
//! - `Acceptance`  — the resume gate: scope sized + ready-to-continue assertion.
//! - `Contract`    — invariants/constraints the continuation MUST honor.
//! - `Context`     — distilled state needed to act (files, decisions, environment).
//! - `Intent`      — the goal/intent DAG (what the operator is trying to achieve).
//! - `Provenance`  — where each fact came from (corpus, session id, message
//!   span) so a resumed session can cite/trust its inputs. *(proposed)*
//! - `Worklog`     — diff/worklog: what was done vs. still outstanding; feeds
//!   the in-progress / unfinished localization. *(proposed)*
//! - `Dedup`       — the merge key + merged-session manifest for collapsing
//!   duplicate-scoped chats into one resumable chat. *(proposed)*

use serde::{Deserialize, Serialize};

/// The kind of a [`Bundle`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum BundleKind {
    Acceptance,
    Contract,
    Context,
    Intent,
    Provenance,
    Worklog,
    Dedup,
}

/// A single typed slice of a continuation bundle.
///
/// `body` is opaque structured JSON so each kind can evolve its own schema
/// without a breaking change to the envelope.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Bundle {
    pub kind: BundleKind,
    /// Estimated token budget this slice consumes when injected.
    pub token_estimate: u32,
    pub body: serde_json::Value,
}

impl Bundle {
    #[must_use]
    pub fn new(kind: BundleKind, body: serde_json::Value) -> Self {
        Self { kind, token_estimate: 0, body }
    }
}

/// The canonical continuation artifact injected into a NEW session.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContinuationBundle {
    /// Source session id (or merged dedup key) this bundle resumes.
    pub source_id: String,
    pub bundles: Vec<Bundle>,
}

impl ContinuationBundle {
    #[must_use]
    pub fn new(source_id: impl Into<String>) -> Self {
        Self { source_id: source_id.into(), bundles: Vec::new() }
    }

    /// A bundle is *injectable* only when it carries an `Acceptance` gate —
    /// the operator-sized scope assertion that resume is safe.
    #[must_use]
    pub fn is_injectable(&self) -> bool {
        self.has(BundleKind::Acceptance)
    }

    #[must_use]
    pub fn has(&self, kind: BundleKind) -> bool {
        self.bundles.iter().any(|b| b.kind == kind)
    }

    /// Total injected token budget across all slices.
    #[must_use]
    pub fn total_token_estimate(&self) -> u32 {
        self.bundles.iter().map(|b| b.token_estimate).sum()
    }

    pub fn push(&mut self, bundle: Bundle) {
        self.bundles.push(bundle);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_bundle(kind: BundleKind) -> Bundle {
        Bundle::new(kind, json!({}))
    }

    fn make_bundle_tokens(kind: BundleKind, tokens: u32) -> Bundle {
        Bundle { kind, token_estimate: tokens, body: json!({}) }
    }

    // ── is_injectable ────────────────────────────────────────────────────────

    #[test]
    fn empty_bundle_is_not_injectable() {
        let cb = ContinuationBundle::new("s1");
        assert!(!cb.is_injectable());
    }

    #[test]
    fn bundle_with_only_intent_is_not_injectable() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Intent));
        assert!(!cb.is_injectable());
    }

    #[test]
    fn bundle_with_acceptance_is_injectable() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Acceptance));
        assert!(cb.is_injectable());
    }

    #[test]
    fn bundle_with_acceptance_and_others_is_injectable() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Intent));
        cb.push(make_bundle(BundleKind::Acceptance));
        cb.push(make_bundle(BundleKind::Contract));
        assert!(cb.is_injectable());
    }

    // ── has ──────────────────────────────────────────────────────────────────

    #[test]
    fn has_returns_false_for_missing_kind() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Intent));
        assert!(!cb.has(BundleKind::Contract));
    }

    #[test]
    fn has_returns_true_for_present_kind() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Contract));
        assert!(cb.has(BundleKind::Contract));
    }

    #[test]
    fn has_all_bundle_kinds() {
        let kinds = [
            BundleKind::Acceptance,
            BundleKind::Contract,
            BundleKind::Context,
            BundleKind::Intent,
            BundleKind::Provenance,
            BundleKind::Worklog,
            BundleKind::Dedup,
        ];
        let mut cb = ContinuationBundle::new("s1");
        for k in kinds {
            cb.push(make_bundle(k));
        }
        for k in kinds {
            assert!(cb.has(k), "missing {k:?}");
        }
    }

    // ── total_token_estimate ─────────────────────────────────────────────────

    #[test]
    fn empty_bundle_total_tokens_is_zero() {
        let cb = ContinuationBundle::new("s1");
        assert_eq!(cb.total_token_estimate(), 0);
    }

    #[test]
    fn single_bundle_total_tokens() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle_tokens(BundleKind::Intent, 42));
        assert_eq!(cb.total_token_estimate(), 42);
    }

    #[test]
    fn multiple_bundles_total_tokens_sum() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle_tokens(BundleKind::Intent, 100));
        cb.push(make_bundle_tokens(BundleKind::Contract, 200));
        cb.push(make_bundle_tokens(BundleKind::Context, 300));
        assert_eq!(cb.total_token_estimate(), 600);
    }

    #[test]
    fn zero_token_bundles_sum_to_zero() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle_tokens(BundleKind::Intent, 0));
        cb.push(make_bundle_tokens(BundleKind::Contract, 0));
        assert_eq!(cb.total_token_estimate(), 0);
    }

    // ── push / ordering ──────────────────────────────────────────────────────

    #[test]
    fn push_appends_in_order() {
        let mut cb = ContinuationBundle::new("s1");
        cb.push(make_bundle(BundleKind::Intent));
        cb.push(make_bundle(BundleKind::Contract));
        assert_eq!(cb.bundles[0].kind, BundleKind::Intent);
        assert_eq!(cb.bundles[1].kind, BundleKind::Contract);
    }

    // ── Bundle::new defaults ─────────────────────────────────────────────────

    #[test]
    fn bundle_new_token_estimate_is_zero() {
        let b = Bundle::new(BundleKind::Intent, json!({"k": "v"}));
        assert_eq!(b.token_estimate, 0);
    }
}
