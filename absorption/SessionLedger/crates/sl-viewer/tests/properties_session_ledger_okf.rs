//! Property evidence for `session_ledger::validate_okf_document` and
//! `session_ledger::OkfDocument::new` (OKF v1 graph validation).
//!
//! The OKF validator is the single source of truth for whether an exported
//! document is well-formed before it is published to downstream consumers
//! (search index, wiki, replay). Any drift between the validator and the
//! exporter surfaces as a `Vec<OkfValidationError>` whose shape is pinned
//! here.
//!
//! `OkfDocument::new` invariants:
//!  * `okf` is always `"1.0"`.
//!  * `source_id` matches the input `bundle.source_id`.
//!  * `provenance.corpus` matches the corpus arg.
//!  * `provenance.source_id` matches the bundle `source_id`.
//!  * `entities`, `relations`, `tags` start empty.
//!
//! `validate_okf_document` invariants:
//!  * A freshly-constructed `OkfDocument::new(b, c)` is valid (zero errors).
//!  * Bumping `okf` to anything other than `"1.0"` produces exactly one
//!    `unsupported_version` error with field `"okf"`.
//!  * `provenance.source_id != source_id` produces exactly one
//!    `source_id_mismatch` error with field `"provenance.source_id"`.
//!  * Duplicated entity ids each surface a `duplicate_entity_id` error.
//!  * Dangling relation source/target each surface their respective error.
//!  * Each error has non-empty `field` / `code` / `message`.

use proptest::prelude::*;
use session_ledger::{
    validate_okf_document, ContinuationBundle, OkfDocument, OkfEntity, OkfProvenance, OkfRelation,
    OkfValidationError,
};

// ── Strategies ─────────────────────────────────────────────────────────────

const CORPORA: &[&str] = &["forge", "codex", "claude-code", "cursor"];

// ── OkfDocument::new ───────────────────────────────────────────────────────

proptest! {
    /// `OkfDocument::new(b, c)` always carries `okf = "1.0"`.
    #[test]
    fn new_document_okf_version_is_one_zero(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        prop_assert_eq!(document.okf, "1.0");
    }

    /// `OkfDocument::new(b, c)` propagates `bundle.source_id`.
    #[test]
    fn new_document_source_id_matches_bundle(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        prop_assert_eq!(document.source_id, bundle.source_id);
    }

    /// `OkfDocument::new(b, c)` propagates `c` into `provenance.corpus`.
    #[test]
    fn new_document_provenance_corpus_matches_arg(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        prop_assert_eq!(document.provenance.corpus, corpus);
    }

    /// `OkfDocument::new(b, c)` propagates `bundle.source_id` into
    /// `provenance.source_id`.
    #[test]
    fn new_document_provenance_source_id_matches_bundle(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        prop_assert_eq!(document.provenance.source_id, bundle.source_id);
    }

    /// `OkfDocument::new(b, c)` starts with empty entities, relations, tags.
    #[test]
    fn new_document_collections_start_empty(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        prop_assert!(document.entities.is_empty());
        prop_assert!(document.relations.is_empty());
        prop_assert!(document.tags.is_empty());
    }
}

// ── validate_okf_document ──────────────────────────────────────────────────

proptest! {
    /// A freshly-constructed OKF document validates with zero errors.
    #[test]
    fn fresh_document_validates_clean(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let document = OkfDocument::new(&bundle, corpus);
        let errors = validate_okf_document(&document);
        prop_assert!(errors.is_empty(), "expected no errors, got {errors:?}");
    }

    /// Bumping `okf` to anything other than `"1.0"` produces exactly one
    /// `unsupported_version` error with field `"okf"`.
    #[test]
    fn wrong_okf_version_produces_one_unsupported_version_error(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        bad_version in "[0-9A-Za-z.]{1,8}",
    ) {
        let bundle = ContinuationBundle::new(&source_id);
        let mut document = OkfDocument::new(&bundle, "forge");
        // Filter out the trivial case where the random string happens to
        // equal "1.0" — we want a strictly-non-"1.0" version.
        prop_assume!(bad_version != "1.0");
        document.okf = bad_version.clone();
        let errors = validate_okf_document(&document);
        let matching: Vec<&OkfValidationError> = errors
            .iter()
            .filter(|e| e.code == "unsupported_version" && e.field == "okf")
            .collect();
        prop_assert_eq!(matching.len(), 1);
        // The message must mention the offending version.
        prop_assert!(matching[0].message.contains(&bad_version));
    }

    /// `provenance.source_id != source_id` produces exactly one
    /// `source_id_mismatch` error.
    #[test]
    fn provenance_source_mismatch_produces_one_error(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        other_id in "[a-zA-Z0-9_-]{1,16}",
    ) {
        prop_assume!(source_id != other_id);
        let bundle = ContinuationBundle::new(&source_id);
        let mut document = OkfDocument::new(&bundle, "forge");
        document.provenance = OkfProvenance {
            corpus: "forge".into(),
            source_id: other_id.clone(),
        };
        let errors = validate_okf_document(&document);
        let matching: Vec<&OkfValidationError> = errors
            .iter()
            .filter(|e| e.code == "source_id_mismatch" && e.field == "provenance.source_id")
            .collect();
        prop_assert_eq!(matching.len(), 1);
    }

    /// Duplicate entity ids surface a `duplicate_entity_id` error per
    /// offending id (one per duplicate occurrence).
    #[test]
    fn duplicate_entity_ids_surface_errors(
        n in 2_usize..6,
    ) {
        let bundle = ContinuationBundle::new("dup-session");
        let mut document = OkfDocument::new(&bundle, "forge");
        let entity = OkfEntity {
            id: "dup-entity".into(),
            r#type: "intent".into(),
            label: "shared".into(),
            properties: serde_json::Value::Null,
        };
        document.entities = (0..n).map(|_| entity.clone()).collect();
        let errors = validate_okf_document(&document);
        let dups: Vec<&OkfValidationError> = errors
            .iter()
            .filter(|e| e.code == "duplicate_entity_id")
            .collect();
        // The validator reports the *second* (and subsequent) occurrences.
        prop_assert_eq!(dups.len(), n - 1);
    }

    /// Dangling relation source surfaces a `dangling_relation_source` error.
    #[test]
    fn dangling_relation_source_surfaces_error(
        source_id in "[a-zA-Z0-9_-]{1,16}",
    ) {
        let bundle = ContinuationBundle::new(&source_id);
        let mut document = OkfDocument::new(&bundle, "forge");
        document.entities = vec![OkfEntity {
            id: "present".into(),
            r#type: "intent".into(),
            label: "p".into(),
            properties: serde_json::Value::Null,
        }];
        document.relations = vec![OkfRelation {
            source: "missing-source".into(),
            target: "present".into(),
            r#type: "grounds".into(),
            provenance: document.provenance.clone(),
        }];
        let errors = validate_okf_document(&document);
        prop_assert!(errors.iter().any(|e| e.code == "dangling_relation_source"
            && e.field == "relations[0].source"));
    }

    /// Dangling relation target surfaces a `dangling_relation_target` error.
    #[test]
    fn dangling_relation_target_surfaces_error(
        source_id in "[a-zA-Z0-9_-]{1,16}",
    ) {
        let bundle = ContinuationBundle::new(&source_id);
        let mut document = OkfDocument::new(&bundle, "forge");
        document.entities = vec![OkfEntity {
            id: "present".into(),
            r#type: "intent".into(),
            label: "p".into(),
            properties: serde_json::Value::Null,
        }];
        document.relations = vec![OkfRelation {
            source: "present".into(),
            target: "missing-target".into(),
            r#type: "grounds".into(),
            provenance: document.provenance.clone(),
        }];
        let errors = validate_okf_document(&document);
        prop_assert!(errors.iter().any(|e| e.code == "dangling_relation_target"
            && e.field == "relations[0].target"));
    }

    /// Every `OkfValidationError` carries non-empty `field`, `code`,
    /// `message` so callers can render an actionable diagnostic.
    #[test]
    fn every_error_has_nonempty_components(_seed in any::<u32>()) {
        let bundle = ContinuationBundle::new("err-shape");
        let mut document = OkfDocument::new(&bundle, "forge");
        // Force every error class at once.
        document.okf = "2.0".into();
        document.provenance.source_id = "other".into();
        document.entities = vec![
            OkfEntity {
                id: "x".into(),
                r#type: "intent".into(),
                label: "x".into(),
                properties: serde_json::Value::Null,
            },
            OkfEntity {
                id: "x".into(),
                r#type: "intent".into(),
                label: "x".into(),
                properties: serde_json::Value::Null,
            },
        ];
        let errors = validate_okf_document(&document);
        prop_assert!(!errors.is_empty());
        for err in &errors {
            prop_assert!(!err.field.is_empty(), "error has empty field");
            prop_assert!(!err.code.is_empty(), "error has empty code");
            prop_assert!(!err.message.is_empty(), "error has empty message");
        }
    }
}
