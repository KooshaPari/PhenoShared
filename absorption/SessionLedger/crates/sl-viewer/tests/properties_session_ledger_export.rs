//! Property evidence for `session_ledger::export_to_okf`
//! (the OKF export adapter that compiles a `ContinuationBundle`
//! into an `OkfDocument`).
//!
//! `export_to_okf` is the main entry point for the OKF v1 export
//! pipeline (CLI `--okf`, wiki writer, search index publisher). The
//! output must always pass `validate_okf_document` so downstream
//! consumers can rely on it.

use proptest::prelude::*;
use session_ledger::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use session_ledger::export::okf::export_to_okf;
use session_ledger::validate_okf_document;

const CORPORA: &[&str] = &["forge", "codex", "claude-code", "cursor", "factory-droid"];

proptest! {
    /// `export_to_okf` always produces an OKF v1 document (okf = "1.0")
    /// carrying the originating bundle `source_id`.
    #[test]
    fn export_carries_source_id_and_version(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let doc = export_to_okf(&bundle, corpus);
        prop_assert_eq!(doc.okf, "1.0");
        prop_assert_eq!(doc.source_id, bundle.source_id);
        prop_assert_eq!(doc.provenance.corpus, corpus);
        prop_assert_eq!(doc.provenance.source_id, source_id);
    }

    /// `export_to_okf` on an empty bundle produces zero entities,
    /// zero relations, and zero tags.
    #[test]
    fn export_empty_bundle_is_empty_graph(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        corpus_idx in 0..CORPORA.len(),
    ) {
        let corpus = CORPORA[corpus_idx];
        let bundle = ContinuationBundle::new(&source_id);
        let doc = export_to_okf(&bundle, corpus);
        prop_assert!(doc.entities.is_empty());
        prop_assert!(doc.relations.is_empty());
        prop_assert!(doc.tags.is_empty());
    }

    /// Every exported document passes `validate_okf_document`
    /// (the validator contract for downstream consumers).
    #[test]
    fn export_output_always_validates(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        n_intent in 0_usize..3,
        n_context in 0_usize..3,
        n_acceptance in 0_usize..3,
        n_contract in 0_usize..3,
    ) {
        let mut bundle = ContinuationBundle::new(&source_id);
        for i in 0..n_intent {
            bundle.push(Bundle::new(
                BundleKind::Intent,
                serde_json::json!({
                    "goal": format!("goal-{i}"),
                    "acceptance_signals": ["looks good"],
                    "constraints": ["do not break the schema"],
                    "user_turn_count": 2_u64,
                }),
            ));
        }
        for i in 0..n_context {
            bundle.push(Bundle::new(
                BundleKind::Context,
                serde_json::json!({
                    "cwd": format!("/work/{i}"),
                    "title": format!("ctx-{i}"),
                }),
            ));
        }
        for i in 0..n_acceptance {
            bundle.push(Bundle::new(
                BundleKind::Acceptance,
                serde_json::json!({
                    "ready": true,
                    "scope_sized": true,
                    "label": format!("accept-{i}"),
                }),
            ));
        }
        for i in 0..n_contract {
            bundle.push(Bundle::new(
                BundleKind::Contract,
                serde_json::json!({
                    "criteria": [format!("criterion-{i}")],
                }),
            ));
        }
        let doc = export_to_okf(&bundle, "forge");
        let errors = validate_okf_document(&doc);
        prop_assert!(errors.is_empty(),
            "exported OKF document has validator errors: {errors:?}");
    }

    /// `export_to_okf` is deterministic: two calls on the same bundle
    /// produce byte-equal documents.
    #[test]
    fn export_is_deterministic(
        source_id in "[a-zA-Z0-9_-]{1,16}",
        n_bundles in 0_usize..4,
    ) {
        let mut bundle = ContinuationBundle::new(&source_id);
        for i in 0..n_bundles {
            bundle.push(Bundle::new(
                BundleKind::Intent,
                serde_json::json!({
                    "goal": format!("goal-{i}"),
                    "acceptance_signals": ["looks good"],
                    "constraints": [],
                    "user_turn_count": i as u64,
                }),
            ));
        }
        let a = export_to_okf(&bundle, "forge");
        let b = export_to_okf(&bundle, "forge");
        prop_assert_eq!(a, b);
    }

    /// Every Intent bundle contributes at least one entity
    /// (the goal entity) and the goal's label is the bundle's goal.
    #[test]
    fn intent_bundle_emits_goal_entity(
        goal in "[a-zA-Z0-9 .,!?-]{1,40}",
        n_signals in 0_usize..4,
        n_constraints in 0_usize..4,
    ) {
        let signals: Vec<String> = (0..n_signals).map(|i| format!("signal-{i}")).collect();
        let constraints: Vec<String> = (0..n_constraints).map(|i| format!("constraint-{i}")).collect();
        let mut bundle = ContinuationBundle::new("intent-test");
        bundle.push(Bundle::new(
            BundleKind::Intent,
            serde_json::json!({
                "goal": goal,
                "acceptance_signals": signals,
                "constraints": constraints,
                "user_turn_count": 1_u64,
            }),
        ));
        let doc = export_to_okf(&bundle, "forge");
        let intent_entities: Vec<&session_ledger::OkfEntity> = doc
            .entities
            .iter()
            .filter(|e| e.r#type == "intent")
            .collect();
        prop_assert_eq!(intent_entities.len(), 1);
        prop_assert_eq!(&intent_entities[0].label, &goal);
        // acceptance + constraint entity counts match.
        let acceptance_count = doc.entities.iter().filter(|e| e.r#type == "acceptance").count();
        let constraint_count = doc.entities.iter().filter(|e| e.r#type == "constraint").count();
        prop_assert_eq!(acceptance_count, n_signals);
        prop_assert_eq!(constraint_count, n_constraints);
    }

    /// Every Context bundle contributes at least one resource entity
    /// when `cwd` is present.
    #[test]
    fn context_bundle_emits_resource_entity(
        cwd in "/[a-zA-Z0-9_./-]{1,40}",
    ) {
        let mut bundle = ContinuationBundle::new("ctx-test");
        bundle.push(Bundle::new(
            BundleKind::Context,
            serde_json::json!({ "cwd": cwd, "title": "ctx" }),
        ));
        let doc = export_to_okf(&bundle, "forge");
        let resource_entities: Vec<&session_ledger::OkfEntity> = doc
            .entities
            .iter()
            .filter(|e| e.r#type == "resource")
            .collect();
        prop_assert_eq!(resource_entities.len(), 1);
    }

    /// Every Acceptance bundle contributes exactly one gate entity
    /// with `ready` and `scope_sized` properties.
    #[test]
    fn acceptance_bundle_emits_gate_entity(
        _seed in any::<u32>(),
    ) {
        let mut bundle = ContinuationBundle::new("acc-test");
        bundle.push(Bundle::new(
            BundleKind::Acceptance,
            serde_json::json!({
                "ready": true,
                "scope_sized": true,
                "label": "resume",
            }),
        ));
        let doc = export_to_okf(&bundle, "forge");
        let gates: Vec<&session_ledger::OkfEntity> = doc
            .entities
            .iter()
            .filter(|e| e.r#type == "gate")
            .collect();
        prop_assert_eq!(gates.len(), 1);
        // The gate entity's label is fixed ("resume-gate") regardless
        // of the input `label` field — it's a gate, not a per-input
        // accept signal.
        prop_assert_eq!(gates[0].label.as_str(), "resume-gate");
        prop_assert_eq!(&gates[0].properties["ready"], &serde_json::json!(true));
        prop_assert_eq!(&gates[0].properties["scope_sized"], &serde_json::json!(true));
    }

    /// `export_to_okf` never produces duplicate entity ids across
    /// multiple intents / contexts / acceptances / contracts.
    #[test]
    fn export_entity_ids_unique(
        n_intent in 1_usize..3,
        n_context in 1_usize..3,
        n_acceptance in 1_usize..3,
        n_contract in 1_usize..3,
    ) {
        let mut bundle = ContinuationBundle::new("dup-id-test");
        for i in 0..n_intent {
            bundle.push(Bundle::new(
                BundleKind::Intent,
                serde_json::json!({ "goal": format!("g-{i}") }),
            ));
        }
        for i in 0..n_context {
            bundle.push(Bundle::new(
                BundleKind::Context,
                serde_json::json!({ "cwd": format!("/d/{i}"), "title": format!("t-{i}") }),
            ));
        }
        for _ in 0..n_acceptance {
            bundle.push(Bundle::new(
                BundleKind::Acceptance,
                serde_json::json!({ "ready": true, "scope_sized": true }),
            ));
        }
        for _ in 0..n_contract {
            bundle.push(Bundle::new(
                BundleKind::Contract,
                serde_json::json!({ "criteria": ["criterion"] }),
            ));
        }
        let doc = export_to_okf(&bundle, "forge");
        let mut ids: Vec<&str> = doc.entities.iter().map(|e| e.id.as_str()).collect();
        ids.sort();
        let original_len = ids.len();
        ids.dedup();
        let dup_count = original_len - ids.len();
        prop_assert_eq!(dup_count, 0, "export_to_okf produced duplicate entity ids");
    }
}
