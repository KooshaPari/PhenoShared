//! OKF (Open Knowledge Format) port — entity/relation/provenance model.
//!
//! # OKF mapping
//!
//! Open Knowledge Format models knowledge as a directed graph of typed
//! [`OkfEntity`] nodes connected by [`OkfRelation`] edges, each carrying a
//! [`OkfProvenance`] record that traces back to the source session.
//!
//! ## Bundle → OKF mapping
//!
//! | Bundle kind        | OKF entity type       | OKF entity label                        |
//! |--------------------|-----------------------|-----------------------------------------|
//! | `Intent` (goal)    | `intent`              | The user's goal string                  |
//! | `Intent` (accept.) | `acceptance`          | Each acceptance signal                  |
//! | `Intent` (constr.) | `constraint`          | Each constraint string                  |
//! | `Context`          | `resource` / `state`  | cwd, title properties                   |
//! | `Contract`         | `criteria`            | Named success criterion                 |
//! | `Acceptance`       | `gate`                | "resume-gate" label                     |
//! | `Provenance`       | provenance edge       | Carried as relation provenance          |
//!
//! ## Example OKF document
//!
//! ```json
//! {
//!   "okf": "1.0",
//!   "source_id": "sess-abc",
//!   "entities": [
//!     { "id": "intent-0", "type": "intent",
//!       "label": "fix the pagination bug",
//!       "properties": { "user_turn_count": 3 } },
//!     { "id": "acceptance-0", "type": "acceptance",
//!       "label": "looks good" },
//!     { "id": "constraint-0", "type": "constraint",
//!       "label": "don't change the database schema" },
//!     { "id": "resource-0", "type": "resource",
//!       "label": "working-directory",
//!       "properties": { "cwd": "/home/user/proj" } },
//!     { "id": "gate-0", "type": "gate",
//!       "label": "resume-gate",
//!       "properties": { "ready": true, "scope_sized": true } }
//!   ],
//!   "relations": [
//!     { "source": "intent-0", "target": "acceptance-0",
//!       "type": "verified_by",
//!       "provenance": { "corpus": "forge", "source_id": "sess-abc" } },
//!     { "source": "intent-0", "target": "constraint-0",
//!       "type": "bounded_by",
//!       "provenance": { "corpus": "forge", "source_id": "sess-abc" } }
//!   ],
//!   "provenance": {
//!     "corpus": "forge",
//!     "source_id": "sess-abc"
//!   }
//! }
//! ```
//!
//! The OKF version string `"1.0"` identifies this dialect. Consumers that
//! encounter a newer major version SHOULD reject the document or fall back
//! gracefully.

use crate::domain::bundle::ContinuationBundle;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// OKF data model
// ---------------------------------------------------------------------------

/// A single knowledge entity (typed node) in the OKF graph.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OkfEntity {
    /// Unique id within the document (e.g. `"intent-0"`, `"resource-1"`).
    pub id: String,
    /// Entity type — mirrors the source [`BundleKind`](crate::domain::bundle::BundleKind) role.
    pub r#type: String,
    /// Human-readable label for the entity.
    pub label: String,
    /// Optional structured properties.
    #[serde(default, skip_serializing_if = "serde_json::Value::is_null")]
    pub properties: serde_json::Value,
}

/// A typed relation between two entities in the OKF graph.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OkfRelation {
    /// Source entity id.
    pub source: String,
    /// Target entity id.
    pub target: String,
    /// Relationship type (e.g. `"verified_by"`, `"bounded_by"`, `"grounds"`).
    pub r#type: String,
    /// Provenance for this relation.
    pub provenance: OkfProvenance,
}

/// Provenance metadata tracing an entity or relation back to its origin.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OkfProvenance {
    /// Source corpus (forge, codex, claude-code, cursor).
    pub corpus: String,
    /// Source session id.
    pub source_id: String,
}

/// A complete OKF document.
///
/// This is the top-level container: a knowledge graph with entities, relations,
/// and document-level provenance.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OkfDocument {
    /// Format version identifier (`"1.0"`).
    pub okf: String,
    /// Source session id.
    pub source_id: String,
    /// Knowledge entities (nodes).
    pub entities: Vec<OkfEntity>,
    /// Typed relations between entities (edges).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub relations: Vec<OkfRelation>,
    /// Document-level provenance.
    pub provenance: OkfProvenance,
    /// User-defined tags for filtering and searching bundles.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
}

/// A structural violation in an [`OkfDocument`].
///
/// This validates the exported OKF graph, not the separate HTTP ingest
/// payload used to create a session. In particular, OKF entity types such as
/// `intent` and `gate` are graph node types, not chat-message roles.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct OkfValidationError {
    /// JSON-like location of the invalid field.
    pub field: String,
    /// Stable machine-readable classification.
    pub code: String,
    /// Human-readable explanation of the violation.
    pub message: String,
}

impl OkfDocument {
    /// Create a bare OKF document with provenance derived from `bundle`.
    #[must_use]
    pub fn new(bundle: &ContinuationBundle, corpus: &str) -> Self {
        Self {
            okf: "1.0".into(),
            source_id: bundle.source_id.clone(),
            entities: Vec::new(),
            relations: Vec::new(),
            provenance: OkfProvenance {
                corpus: corpus.into(),
                source_id: bundle.source_id.clone(),
            },
            tags: Vec::new(),
        }
    }

    /// Serialize to pretty-printed JSON.
    ///
    /// # Errors
    /// Returns [`serde_json::Error`] if the writer fails.
    pub fn to_json_pretty<W: std::io::Write>(&self, writer: W) -> serde_json::Result<()> {
        serde_json::to_writer_pretty(writer, self)
    }
}

/// Validate the structural invariants of an exported OKF v1 document.
///
/// The validator intentionally does not require ingest-only fields such as
/// `created_at`, `messages`, or chat roles: canonical OKF documents are
/// knowledge graphs containing entities, relations, and provenance.
#[must_use]
pub fn validate_okf_document(document: &OkfDocument) -> Vec<OkfValidationError> {
    let mut errors = Vec::new();

    if document.okf != "1.0" {
        errors.push(OkfValidationError {
            field: "okf".into(),
            code: "unsupported_version".into(),
            message: format!("expected OKF version \"1.0\", got {:?}", document.okf),
        });
    }

    if document.provenance.source_id != document.source_id {
        errors.push(OkfValidationError {
            field: "provenance.source_id".into(),
            code: "source_id_mismatch".into(),
            message: format!(
                "provenance.source_id {:?} does not match source_id {:?}",
                document.provenance.source_id, document.source_id
            ),
        });
    }

    let mut entity_ids = std::collections::HashSet::with_capacity(document.entities.len());
    for (index, entity) in document.entities.iter().enumerate() {
        if !entity_ids.insert(entity.id.as_str()) {
            errors.push(OkfValidationError {
                field: format!("entities[{index}].id"),
                code: "duplicate_entity_id".into(),
                message: format!("entity id {:?} is duplicated", entity.id),
            });
        }
    }

    for (index, relation) in document.relations.iter().enumerate() {
        if !entity_ids.contains(relation.source.as_str()) {
            errors.push(OkfValidationError {
                field: format!("relations[{index}].source"),
                code: "dangling_relation_source".into(),
                message: format!("relation source {:?} is not an entity id", relation.source),
            });
        }
        if !entity_ids.contains(relation.target.as_str()) {
            errors.push(OkfValidationError {
                field: format!("relations[{index}].target"),
                code: "dangling_relation_target".into(),
                message: format!("relation target {:?} is not an entity id", relation.target),
            });
        }
    }

    errors
}

// ---------------------------------------------------------------------------
// Port trait
// ---------------------------------------------------------------------------

/// Port: OKF exporter.
///
/// Converts a compiled [`ContinuationBundle`] into the Open Knowledge Format
/// (entities + relations + provenance). Implementations MAY target JSON, YAML,
/// or any other concrete serialization.
///
/// # Errors
///
/// Returns [`super::PortError::Backend`] if serialization fails.
pub trait OkfExporter {
    /// The concrete output type (e.g. `String`, `serde_json::Value`).
    type Output;

    /// Export a continuation bundle into the OKF representation.
    ///
    /// # Errors
    ///
    /// Returns [`super::PortError::Backend`] if the export cannot be produced.
    fn export(&self, bundle: &ContinuationBundle) -> Result<Self::Output, super::PortError>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Error, Write};

    fn valid_document() -> OkfDocument {
        OkfDocument::new(&ContinuationBundle::new("session-42"), "forge")
    }

    #[test]
    fn validation_rejects_unsupported_version() {
        let mut document = valid_document();
        document.okf = "2.0".into();
        let errors = validate_okf_document(&document);
        assert!(errors
            .iter()
            .any(|error| { error.code == "unsupported_version" && error.field == "okf" }));
    }

    #[test]
    fn validation_rejects_provenance_source_mismatch() {
        let mut document = valid_document();
        document.provenance.source_id = "other-session".into();
        let errors = validate_okf_document(&document);
        assert!(errors.iter().any(|error| {
            error.code == "source_id_mismatch" && error.field == "provenance.source_id"
        }));
    }

    #[test]
    fn validation_rejects_duplicate_entity_ids() {
        let mut document = valid_document();
        let entity = OkfEntity {
            id: "entity-0".into(),
            r#type: "intent".into(),
            label: "goal".into(),
            properties: serde_json::Value::Null,
        };
        document.entities = vec![entity.clone(), entity];
        let errors = validate_okf_document(&document);
        assert!(errors.iter().any(|error| {
            error.code == "duplicate_entity_id" && error.field == "entities[1].id"
        }));
    }

    #[test]
    fn validation_rejects_dangling_relation_source() {
        let mut document = valid_document();
        document.relations.push(OkfRelation {
            source: "missing".into(),
            target: "present".into(),
            r#type: "grounds".into(),
            provenance: document.provenance.clone(),
        });
        let errors = validate_okf_document(&document);
        assert!(errors.iter().any(|error| {
            error.code == "dangling_relation_source" && error.field == "relations[0].source"
        }));
    }

    #[test]
    fn validation_rejects_dangling_relation_target() {
        let mut document = valid_document();
        document.relations.push(OkfRelation {
            source: "present".into(),
            target: "missing".into(),
            r#type: "grounds".into(),
            provenance: document.provenance.clone(),
        });
        let errors = validate_okf_document(&document);
        assert!(errors.iter().any(|error| {
            error.code == "dangling_relation_target" && error.field == "relations[0].target"
        }));
    }

    #[test]
    fn new_document_copies_source_provenance_and_starts_empty() {
        let bundle = ContinuationBundle::new("session-42");

        let document = OkfDocument::new(&bundle, "cursor");

        assert_eq!(document.okf, "1.0");
        assert_eq!(document.source_id, "session-42");
        assert_eq!(document.provenance.corpus, "cursor");
        assert_eq!(document.provenance.source_id, "session-42");
        assert!(document.entities.is_empty());
        assert!(document.relations.is_empty());
        assert!(document.tags.is_empty());
    }

    #[test]
    fn pretty_json_omits_empty_optional_collections() {
        let bundle = ContinuationBundle::new("session-42");
        let document = OkfDocument::new(&bundle, "codex");
        let mut output = Vec::new();

        document.to_json_pretty(&mut output).expect("serialize OKF document");
        let value: serde_json::Value =
            serde_json::from_slice(&output).expect("parse serialized document");

        assert_eq!(value["source_id"], "session-42");
        assert_eq!(value["provenance"]["corpus"], "codex");
        assert!(value.get("relations").is_none());
        assert!(value.get("tags").is_none());
    }

    #[test]
    fn pretty_json_surfaces_writer_failures() {
        struct FailingWriter;

        impl Write for FailingWriter {
            fn write(&mut self, _buffer: &[u8]) -> std::io::Result<usize> {
                Err(Error::other("fixture writer failure"))
            }

            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }

        let bundle = ContinuationBundle::new("session-42");
        let document = OkfDocument::new(&bundle, "forge");

        assert!(document.to_json_pretty(FailingWriter).is_err());
    }
}
