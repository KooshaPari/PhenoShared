//! OKF export adapter — compiles a [`ContinuationBundle`] into an [`OkfDocument`].
//!
//! This adapter implements the [`OkfExporter`] port as `JsonOkfExporter`,
//! which serialises a compiled [`ContinuationBundle`] into the OKF knowledge-graph
//! format (entities + relations + provenance).
//!
//! # Mapping
//!
//! See [`crate::ports::okf`] for the full bundle-to-OKF mapping table. In brief:
//!
//! | Bundle kind        | OKF entity(s)             | Relation                    |
//! |--------------------|---------------------------|-----------------------------|
//! | `Intent`           | `intent`, `acceptance*`, `constraint*` | `asserts`, `verified_by`, `bounded_by` |
//! | `Context`          | `resource`, `state`       | `grounds`                   |
//! | `Contract`         | `criteria`                | `requires`                  |
//! | `Acceptance`       | `gate`                    | — (document-level)          |
//!
//! A free-standing convenience function [`export_to_okf`] is also provided for
//! direct use without going through the trait (analogous to how
//! [`crate::distill::extractor::HeuristicIntentExtractor::extract_intent`]
//! works alongside the trait impl).

use crate::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use crate::ports::okf::{OkfDocument, OkfEntity, OkfExporter, OkfRelation};
use crate::ports::PortError;

// ---------------------------------------------------------------------------
// Free-standing convenience: the `--okf` export entry point.
// ---------------------------------------------------------------------------

/// Export a compiled continuation bundle into an [`OkfDocument`].
///
/// This is the main entry point analogous to a CLI `--okf` flag: given a
/// compiled bundle, produce the OKF knowledge-graph representation.
///
/// `corpus` identifies the source corpus (e.g. `"forge"`, `"codex"`).
#[must_use]
pub fn export_to_okf(bundle: &ContinuationBundle, corpus: &str) -> OkfDocument {
    let mut doc = OkfDocument::new(bundle, corpus);

    let mut entity_counter: usize = 0;
    let mut next_id = || -> String {
        let id = entity_counter.to_string();
        entity_counter += 1;
        id
    };

    for b in &bundle.bundles {
        match b.kind {
            BundleKind::Intent => {
                translate_intent(&mut doc, b, &mut next_id);
            }
            BundleKind::Context => {
                translate_context(&mut doc, b, &mut next_id);
            }
            BundleKind::Contract => {
                translate_contract(&mut doc, b, &mut next_id);
            }
            BundleKind::Acceptance => {
                translate_acceptance(&mut doc, b, &mut next_id);
            }
            BundleKind::Provenance | BundleKind::Worklog | BundleKind::Dedup => {
                // These are folded into relation provenance or document metadata
                // rather than producing independent entity nodes.
            }
        }
    }

    doc
}

// ---------------------------------------------------------------------------
// Bundle-kind translators
// ---------------------------------------------------------------------------

/// Translate an `Intent` bundle into OKF intent/acceptance/constraint entities
/// with appropriate relations.
fn translate_intent(doc: &mut OkfDocument, b: &Bundle, next_id: &mut impl FnMut() -> String) {
    let goal = b.body.get("goal").and_then(|v| v.as_str()).unwrap_or("");
    let acceptance_signals: Vec<&str> = b.body["acceptance_signals"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_default();
    let constraints: Vec<&str> = b.body["constraints"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect())
        .unwrap_or_default();

    let user_turn_count = b.body["user_turn_count"].as_u64().unwrap_or(0);

    // Goal entity
    let goal_id = format!("intent-{}", next_id());
    doc.entities.push(OkfEntity {
        id: goal_id.clone(),
        r#type: "intent".into(),
        label: goal.to_string(),
        properties: serde_json::json!({ "user_turn_count": user_turn_count }),
    });

    // Acceptance entities + verified_by edges
    for signal in &acceptance_signals {
        let cnt = next_id();
        let acc_id = format!("acceptance-{cnt}");
        doc.entities.push(OkfEntity {
            id: acc_id.clone(),
            r#type: "acceptance".into(),
            label: signal.to_string(),
            properties: serde_json::Value::Null,
        });
        doc.relations.push(OkfRelation {
            source: goal_id.clone(),
            target: acc_id,
            r#type: "verified_by".into(),
            provenance: doc.provenance.clone(),
        });
    }

    // Constraint entities + bounded_by edges
    for constraint in &constraints {
        let cnt = next_id();
        let con_id = format!("constraint-{cnt}");
        doc.entities.push(OkfEntity {
            id: con_id.clone(),
            r#type: "constraint".into(),
            label: constraint.to_string(),
            properties: serde_json::Value::Null,
        });
        doc.relations.push(OkfRelation {
            source: goal_id.clone(),
            target: con_id,
            r#type: "bounded_by".into(),
            provenance: doc.provenance.clone(),
        });
    }
}

/// Translate a `Context` bundle into resource/state OKF entities.
fn translate_context(doc: &mut OkfDocument, b: &Bundle, next_id: &mut impl FnMut() -> String) {
    let cwd = b.body.get("cwd").and_then(|v| v.as_str()).unwrap_or("");
    let title = b.body.get("title").and_then(|v| v.as_str()).unwrap_or("");

    if !cwd.is_empty() {
        let cnt = next_id();
        let id = format!("resource-{cnt}");
        doc.entities.push(OkfEntity {
            id: id.clone(),
            r#type: "resource".into(),
            label: "working-directory".into(),
            properties: serde_json::json!({ "cwd": cwd }),
        });
    }
    if !title.is_empty() {
        let cnt = next_id();
        let id = format!("state-{cnt}");
        doc.entities.push(OkfEntity {
            id: id.clone(),
            r#type: "state".into(),
            label: "session-title".into(),
            properties: serde_json::json!({ "title": title }),
        });
    }
}

/// Translate a `Contract` bundle into criteria OKF entities.
fn translate_contract(doc: &mut OkfDocument, b: &Bundle, next_id: &mut impl FnMut() -> String) {
    let criteria = b
        .body
        .get("criteria")
        .and_then(|v| v.as_str())
        .or_else(|| {
            // Support both string and array-of-strings formats
            b.body
                .get("criteria")
                .and_then(|v| v.as_array())
                .and_then(|arr| arr.first())
                .and_then(|v| v.as_str())
        })
        .unwrap_or("");

    let cnt = next_id();
    let id = format!("criteria-{cnt}");
    doc.entities.push(OkfEntity {
        id: id.clone(),
        r#type: "criteria".into(),
        label: criteria.to_string(),
        properties: b.body.clone(),
    });
}

/// Translate an `Acceptance` bundle into a gate OKF entity (document-level).
fn translate_acceptance(doc: &mut OkfDocument, b: &Bundle, next_id: &mut impl FnMut() -> String) {
    let ready = b.body["ready"].as_bool().unwrap_or(false);
    let scope_sized = b.body["scope_sized"].as_bool().unwrap_or(false);
    let user_turns = b.body["user_turns"].as_u64().unwrap_or(0);

    let cnt = next_id();
    let id = format!("gate-{cnt}");
    doc.entities.push(OkfEntity {
        id,
        r#type: "gate".into(),
        label: "resume-gate".into(),
        properties: serde_json::json!({
            "ready": ready,
            "scope_sized": scope_sized,
            "user_turns": user_turns,
        }),
    });
}

// ---------------------------------------------------------------------------
// OkfExporter trait adapter
// ---------------------------------------------------------------------------

/// JSON-based OKF exporter.
///
/// Produces a [`serde_json::Value`] representation of the OKF document,
/// which can then be serialized to a JSON string.
#[derive(Debug, Default, Clone, Copy)]
pub struct JsonOkfExporter;

impl JsonOkfExporter {
    #[must_use]
    pub fn new() -> Self {
        Self
    }
}

impl OkfExporter for JsonOkfExporter {
    type Output = serde_json::Value;

    fn export(&self, bundle: &ContinuationBundle) -> Result<Self::Output, PortError> {
        // Infer a corpus from the provenance bundle if present.
        let corpus = bundle
            .bundles
            .iter()
            .find(|b| b.kind == BundleKind::Provenance)
            .and_then(|b| b.body.get("corpus"))
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        let doc = export_to_okf(bundle, corpus);
        serde_json::to_value(doc).map_err(|e| PortError::Backend(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill;
    use crate::domain::bundle::Bundle;
    use crate::domain::session::{Corpus, Message, Role, Session};

    fn sample_bundle() -> ContinuationBundle {
        let mut s = Session::new("sess-okf-1", Corpus::Forge);
        s.cwd = Some("/home/user/proj".into());
        s.title = Some("fix pagination".into());
        s.messages.push(Message::new(
            Role::User,
            "fix the pagination bug but don't change the db schema",
        ));
        s.messages.push(Message::new(Role::Assistant, "on it"));
        s.messages.push(Message::new(Role::User, "looks good, tests pass now"));

        distill::compile(&s)
    }

    // ------------------------------------------------------------------
    // Test 1: OKF document has correct version, source_id, provenance
    // ------------------------------------------------------------------
    #[test]
    fn okf_document_has_correct_metadata() {
        let bundle = sample_bundle();
        let doc = export_to_okf(&bundle, "forge");

        assert_eq!(doc.okf, "1.0");
        assert_eq!(doc.source_id, "sess-okf-1");
        assert_eq!(doc.provenance.corpus, "forge");
        assert_eq!(doc.provenance.source_id, "sess-okf-1");
    }

    // ------------------------------------------------------------------
    // Test 2: All expected entity kinds are present
    // ------------------------------------------------------------------
    #[test]
    fn okf_contains_expected_entity_kinds() {
        let bundle = sample_bundle();
        let doc = export_to_okf(&bundle, "forge");

        let kinds: Vec<&str> = doc.entities.iter().map(|e| e.r#type.as_str()).collect();

        assert!(kinds.contains(&"intent"), "should have intent entity");
        assert!(kinds.contains(&"acceptance"), "should have acceptance entity");
        assert!(kinds.contains(&"constraint"), "should have constraint entity");
        assert!(kinds.contains(&"resource"), "should have resource entity");
        assert!(kinds.contains(&"state"), "should have state entity");
        assert!(kinds.contains(&"gate"), "should have gate entity");

        // Verify gate properties
        let gate = doc.entities.iter().find(|e| e.r#type == "gate").unwrap();
        assert_eq!(gate.properties["ready"], true);
        assert_eq!(gate.properties["scope_sized"], true);
    }

    // ------------------------------------------------------------------
    // Test 3: Relations connect entities correctly with provenance
    // ------------------------------------------------------------------
    #[test]
    fn okf_relations_have_correct_types_and_provenance() {
        let bundle = sample_bundle();
        let doc = export_to_okf(&bundle, "forge");

        assert!(!doc.relations.is_empty(), "should have relations");

        // Every relation should carry provenance matching the document
        for rel in &doc.relations {
            assert_eq!(rel.provenance.corpus, "forge");
            assert_eq!(rel.provenance.source_id, "sess-okf-1");
        }

        // Should have verified_by and bounded_by relations
        let types: Vec<&str> = doc.relations.iter().map(|r| r.r#type.as_str()).collect();
        assert!(types.contains(&"verified_by"), "should have verified_by edges");
        assert!(types.contains(&"bounded_by"), "should have bounded_by edges");
    }

    // ------------------------------------------------------------------
    // Test 4: OkfExporter trait produces valid JSON
    // ------------------------------------------------------------------
    #[test]
    fn json_okf_exporter_produces_valid_value() {
        let bundle = sample_bundle();
        let exporter = JsonOkfExporter::new();
        let value = exporter.export(&bundle).expect("export should succeed");

        // Round-trip through OkfDocument
        let doc: OkfDocument = serde_json::from_value(value).expect("valid OkfDocument");
        assert_eq!(doc.okf, "1.0");
        assert!(doc.entities.len() >= 5); // intent + acceptance + constraint + resource + gate
    }

    // ------------------------------------------------------------------
    // Test 5: Empty session produces minimal OKF
    // ------------------------------------------------------------------
    #[test]
    fn empty_bundle_produces_minimal_okf() {
        let mut bundle = ContinuationBundle::new("empty-sess");
        // Add an acceptance bundle so the export has something
        bundle.push(Bundle::new(
            BundleKind::Acceptance,
            serde_json::json!({
                "ready": false,
                "scope_sized": false,
                "user_turns": 0,
            }),
        ));

        let doc = export_to_okf(&bundle, "test");

        // Should have 1 entity: the gate
        assert_eq!(doc.entities.len(), 1);
        assert_eq!(doc.entities[0].r#type, "gate");
        assert_eq!(doc.entities[0].properties["ready"], false);
    }

    // ------------------------------------------------------------------
    // Test 6: OKF document round-trips through JSON
    // ------------------------------------------------------------------
    #[test]
    fn okf_document_round_trips_through_json() {
        let bundle = sample_bundle();
        let doc = export_to_okf(&bundle, "forge");

        let json_str = serde_json::to_string_pretty(&doc).expect("serialize");
        let back: OkfDocument = serde_json::from_str(&json_str).expect("deserialize");

        assert_eq!(doc, back);
    }
}
