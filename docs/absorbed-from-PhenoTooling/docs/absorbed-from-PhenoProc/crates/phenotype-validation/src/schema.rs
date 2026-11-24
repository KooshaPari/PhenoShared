//! Schema validation

use std::collections::HashMap;

/// Schema validation error
#[derive(Debug, thiserror::Error)]
pub enum SchemaValidationError {
    #[error("Missing required field: {0}")]
    MissingField(String),
    #[error("Invalid type for field: {0}")]
    InvalidType(String),
    #[error("Field validation failed: {0} - {1}")]
    FieldError(String, String),
}

/// Schema definition for validation
#[derive(Clone, Debug)]
pub struct Schema {
    fields: HashMap<String, FieldType>,
    required: Vec<String>,
}

impl Schema {
    pub fn new() -> Self {
        Self {
            fields: HashMap::new(),
            required: Vec::new(),
        }
    }

    pub fn with_field(mut self, name: &str, field_type: FieldType) -> Self {
        self.fields.insert(name.to_string(), field_type);
        self
    }

    pub fn with_required(mut self, name: &str) -> Self {
        self.required.push(name.to_string());
        self
    }

    /// Validate data against schema
    pub fn validate(
        &self,
        data: &HashMap<String, serde_json::Value>,
    ) -> Result<(), SchemaValidationError> {
        for field in &self.required {
            if !data.contains_key(field) {
                return Err(SchemaValidationError::MissingField(field.clone()));
            }
        }
        Ok(())
    }
}

impl Default for Schema {
    fn default() -> Self {
        Self::new()
    }
}

/// Field types for schema
#[derive(Debug, Clone)]
pub enum FieldType {
    String,
    Integer,
    Boolean,
    Array(Box<FieldType>),
    Object(Box<Schema>),
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn schema_new_is_empty() {
        let s: Schema = Schema::new();
        // Validate an empty map against the empty schema — should pass.
        let data: HashMap<String, serde_json::Value> = HashMap::new();
        assert!(s.validate(&data).is_ok());
    }

    #[test]
    fn schema_default_matches_new() {
        let a: Schema = Schema::default();
        let b: Schema = Schema::new();
        // Both have no required fields and no field metadata, so they validate
        // the same input identically.
        let data: HashMap<String, serde_json::Value> = HashMap::new();
        assert!(a.validate(&data).is_ok());
        assert!(b.validate(&data).is_ok());
    }

    #[test]
    fn schema_with_field_and_required_validates() {
        let s: Schema = Schema::new()
            .with_field("name", FieldType::String)
            .with_field("age", FieldType::Integer)
            .with_required("name");
        let mut data = HashMap::new();
        data.insert("name".to_string(), json!("alice"));
        assert!(s.validate(&data).is_ok());
    }

    #[test]
    fn schema_missing_required_field_errors() {
        let s: Schema = Schema::new()
            .with_field("name", FieldType::String)
            .with_required("name");
        let data: HashMap<String, serde_json::Value> = HashMap::new();
        let err = s.validate(&data).unwrap_err();
        match err {
            SchemaValidationError::MissingField(f) => assert_eq!(f, "name"),
            other => panic!("unexpected error: {:?}", other),
        }
    }

    #[test]
    fn schema_validation_error_display() {
        let m = SchemaValidationError::MissingField("x".into());
        assert_eq!(m.to_string(), "Missing required field: x");
        let t = SchemaValidationError::InvalidType("y".into());
        assert_eq!(t.to_string(), "Invalid type for field: y");
        let fe = SchemaValidationError::FieldError("z".into(), "too short".into());
        assert_eq!(fe.to_string(), "Field validation failed: z - too short");
    }

    #[test]
    fn schema_validate_multiple_required() {
        let s: Schema = Schema::new()
            .with_field("a", FieldType::String)
            .with_field("b", FieldType::Integer)
            .with_required("a")
            .with_required("b");
        let mut data = HashMap::new();
        data.insert("a".to_string(), json!("hello"));
        // b is missing
        let err = s.validate(&data).unwrap_err();
        assert!(matches!(err, SchemaValidationError::MissingField(ref f) if f == "b"));
    }
}
