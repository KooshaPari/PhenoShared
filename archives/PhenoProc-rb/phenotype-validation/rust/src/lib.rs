use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub mod error;
pub use error::ValidationError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub is_valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

impl ValidationResult {
    pub fn success() -> Self {
        Self {
            is_valid: true,
            errors: vec![],
            warnings: vec![],
        }
    }

    pub fn failure(errors: Vec<String>) -> Self {
        Self {
            is_valid: false,
            errors,
            warnings: vec![],
        }
    }
}

pub struct JsonSchemaValidator {
    schemas: HashMap<String, serde_json::Value>,
}

impl JsonSchemaValidator {
    pub fn new() -> Self {
        Self {
            schemas: HashMap::new(),
        }
    }

    pub fn validate(&self, schema_json: &str, document_json: &str) -> Result<ValidationResult, ValidationError> {
        let schema: serde_json::Value = serde_json::from_str(schema_json)
            .map_err(|e| ValidationError::SchemaError(e.to_string()))?;
        
        let document: serde_json::Value = serde_json::from_str(document_json)
            .map_err(|e| ValidationError::DocumentError(e.to_string()))?;

        // Basic type check
        if let (Some(schema_type), Some(doc_type)) = (
            schema.get("type").and_then(|v| v.as_str()),
            document.get("type").and_then(|v| v.as_str())
        ) {
            if schema_type != doc_type {
                return Ok(ValidationResult::failure(vec![
                    format!("Type mismatch: expected {}, got {}", schema_type, doc_type)
                ]));
            }
        }

        Ok(ValidationResult::success())
    }

    pub fn add_schema(&mut self, name: &str, schema_content: &str) -> Result<(), ValidationError> {
        let schema: serde_json::Value = serde_json::from_str(schema_content)
            .map_err(|e| ValidationError::SchemaError(e.to_string()))?;
        self.schemas.insert(name.to_string(), schema);
        Ok(())
    }

    pub fn validate_against_named_schema(&self, document_json: &str, schema_name: &str) -> Result<ValidationResult, ValidationError> {
        let schema = self.schemas.get(schema_name)
            .ok_or_else(|| ValidationError::SchemaNotFound(schema_name.to_string()))?;
        
        self.validate(&serde_json::to_string(schema).unwrap(), document_json)
    }
}
