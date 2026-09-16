//! JSON Schema definitions for manifest and pillar configs
use jsonschema::Validator;
use serde_json::{json, Value};
use std::sync::OnceLock;

pub fn manifest_schema_for(url: &str) -> Option<&'static Validator> {
    // We currently only have a single schema. If the URL matches the default,
    // return it; otherwise return None (skip validation rather than fail).
    let _ = url;
    Some(manifest_schema())
}

pub fn manifest_schema() -> &'static Validator {
    static SCHEMA: OnceLock<Validator> = OnceLock::new();
    SCHEMA.get_or_init(|| {
        let schema = manifest_schema_value();
        jsonschema::options()
            .with_draft(jsonschema::Draft::Draft202012)
            .build(&schema)
            .expect("Invalid manifest schema")
    })
}

pub fn pillar_schema() -> &'static Validator {
    static SCHEMA: OnceLock<Validator> = OnceLock::new();
    SCHEMA.get_or_init(|| {
        let schema = pillar_schema_value();
        jsonschema::options()
            .with_draft(jsonschema::Draft::Draft202012)
            .build(&schema)
            .expect("Invalid pillar schema")
    })
}

pub fn validate_manifest(value: &Value, schema_url: &str) -> Result<(), Vec<String>> {
    if let Some(schema) = manifest_schema_for(schema_url) {
        if !schema.is_valid(value) {
            let errors: Vec<String> = schema
                .validate(value)
                .err()
                .map(|it| it.map(|e| e.to_string()).collect())
                .unwrap_or_default();
            return Err(errors);
        }
    }
    Ok(())
}

pub fn validate_pillar(value: &Value) -> Result<(), Vec<String>> {
    let schema = pillar_schema();
    if !schema.is_valid(value) {
        let errors: Vec<String> = schema
            .validate(value)
            .err()
            .map(|it| it.map(|e| e.to_string()).collect())
            .unwrap_or_default();
        Err(errors)
    } else {
        Ok(())
    }
}

fn manifest_schema_value() -> Value {
    json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://phenotype.dev/schemas/manifest-1.0.json",
        "title": "Phenotype Attestation Manifest",
        "type": "object",
        "additionalProperties": false,
        "required": ["schema_version", "generated_at", "commit_sha", "tree_sha", "pillars", "health_score", "expires_at", "signature", "public_key"],
        "properties": {
            "schema_version": { "type": "integer", "const": 1 },
            "generated_at": { "type": "string", "format": "date-time" },
            "commit_sha": { "type": "string", "pattern": "^[a-f0-9]{40}$" },
            "tree_sha": { "type": "string", "pattern": "^[a-f0-9]{40}$" },
            "pillars": { "type": "object", "additionalProperties": false, "required": ["quality", "security", "perf", "compliance", "docs"] },
            "health_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "expires_at": { "type": "string", "format": "date-time" },
            "signature": { "type": "string" },
            "public_key": { "type": "string" },
            "generator": { "type": "object" }
        }
    })
}

fn pillar_schema_value() -> Value {
    json!({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://phenotype.dev/schemas/pillar-1.0.json",
        "title": "Phenotype Pillar Check Definition",
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "version", "pillar", "checks"],
        "properties": {
            "name": { "type": "string" },
            "version": { "type": "string" },
            "pillar": { "type": "string", "enum": ["quality", "security", "perf", "compliance", "docs"] },
            "checks": { "type": "array", "items": { "type": "object" } }
        }
    })
}
