use serde_json::Value;
use thiserror::Error;

/// Error type for schema validation failures.
#[derive(Debug, Error, PartialEq)]
pub enum SchemaError {
    #[error("missing required field: {0}")]
    MissingField(String),
    #[error("wrong type for field {field}: expected {expected}, got {got}")]
    WrongType {
        field: String,
        expected: String,
        got: String,
    },
}

/// A single field definition inside a configuration schema.
#[derive(Debug, Clone, PartialEq)]
pub struct SchemaField {
    pub name: String,
    pub required: bool,
    pub type_hint: String,
}

impl SchemaField {
    /// Create a new schema field.
    pub fn new(name: impl Into<String>, required: bool, type_hint: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            required,
            type_hint: type_hint.into(),
        }
    }
}

/// A collection of schema fields that can validate a JSON Value config.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct ConfigSchema {
    pub fields: Vec<SchemaField>,
}

impl ConfigSchema {
    /// Create a new, empty schema.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a field to the schema.
    pub fn field(
        mut self,
        name: impl Into<String>,
        required: bool,
        type_hint: impl Into<String>,
    ) -> Self {
        self.fields
            .push(SchemaField::new(name, required, type_hint));
        self
    }

    /// Validate the given JSON Value config against this schema.
    ///
    /// `config` should be a JSON object (`serde_json::Value::Object`).
    /// Non-object values are treated as having no fields, so all required
    /// fields will be reported as missing.
    pub fn validate(&self, config: &Value) -> Result<(), SchemaError> {
        let obj = match config {
            Value::Object(map) => map,
            _ => {
                // Not an object — no fields are present; all required fields are missing.
                let missing: Vec<&SchemaField> =
                    self.fields.iter().filter(|f| f.required).collect();
                if missing.is_empty() {
                    return Ok(());
                }
                return Err(SchemaError::MissingField(missing[0].name.clone()));
            }
        };

        for field in &self.fields {
            match obj.get(&field.name) {
                Some(value) => {
                    if !type_matches(value, &field.type_hint) {
                        return Err(SchemaError::WrongType {
                            field: field.name.clone(),
                            expected: field.type_hint.clone(),
                            got: format!("{:?}", value),
                        });
                    }
                }
                None => {
                    if field.required {
                        return Err(SchemaError::MissingField(field.name.clone()));
                    }
                }
            }
        }
        Ok(())
    }
}

/// Check whether a JSON value matches the given type hint.
fn type_matches(value: &Value, hint: &str) -> bool {
    match hint {
        "string" => value.is_string(),
        "integer" => value.is_i64() || value.is_u64(),
        "boolean" => value.is_boolean(),
        "number" => value.is_number(),
        "array" => value.is_array(),
        "object" => value.is_object(),
        _ => true, // unknown type hints are treated as permissive
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn schema_validates_required_fields() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", true, "integer");

        let config = json!({
            "name": "localhost",
            "port": 8080
        });

        assert_eq!(schema.validate(&config), Ok(()));
    }

    #[test]
    fn schema_rejects_missing_field() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", true, "integer");

        let config = json!({
            "name": "localhost"
            // "port" is missing
        });

        assert_eq!(
            schema.validate(&config),
            Err(SchemaError::MissingField("port".to_string()))
        );
    }

    #[test]
    fn schema_accepts_optional_fields() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", false, "integer");

        let config = json!({
            "name": "localhost"
            // "port" is optional and omitted
        });

        assert_eq!(schema.validate(&config), Ok(()));
    }

    #[test]
    fn schema_rejects_wrong_type() {
        let schema = ConfigSchema::new().field("port", true, "integer");

        let config = json!({
            "port": "not_a_number"
        });

        assert!(matches!(
            schema.validate(&config),
            Err(SchemaError::WrongType { field, expected, .. })
                if field == "port" && expected == "integer"
        ));
    }

    #[test]
    fn schema_validates_optional_field_when_present() {
        let schema = ConfigSchema::new().field("timeout", false, "integer");

        let config = json!({
            "timeout": "not_a_number"
        });

        assert!(matches!(
            schema.validate(&config),
            Err(SchemaError::WrongType { field, expected, .. })
                if field == "timeout" && expected == "integer"
        ));
    }

    #[test]
    fn schema_rejects_non_object_config() {
        let schema = ConfigSchema::new().field("name", true, "string");

        let config = json!("not_an_object");

        assert_eq!(
            schema.validate(&config),
            Err(SchemaError::MissingField("name".to_string()))
        );
    }

    #[test]
    fn schema_non_object_with_no_required_fields_ok() {
        let schema = ConfigSchema::new().field("name", false, "string");

        let config = json!(42);

        assert_eq!(schema.validate(&config), Ok(()));
    }

    #[test]
    fn test_schema_field_creation() {
        let field = SchemaField::new("timeout", false, "integer");
        assert_eq!(field.name, "timeout");
        assert!(!field.required);
        assert_eq!(field.type_hint, "integer");

        let required_field = SchemaField::new("host", true, "string");
        assert_eq!(required_field.name, "host");
        assert!(required_field.required);
        assert_eq!(required_field.type_hint, "string");
    }

    #[test]
    fn test_schema_validation_pass() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", true, "integer")
            .field("debug", false, "boolean");

        let config = json!({
            "name": "my-app",
            "port": 3000
        });

        assert!(schema.validate(&config).is_ok());
    }

    #[test]
    fn test_schema_validation_fail() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", true, "integer");

        // "port" is required but missing
        let config = json!({
            "name": "my-app"
        });

        let err = schema.validate(&config).unwrap_err();
        assert_eq!(err, SchemaError::MissingField("port".to_string()));
    }

    #[test]
    fn test_schema_type_check() {
        let schema = ConfigSchema::new()
            .field("name", true, "string")
            .field("port", true, "integer")
            .field("debug", true, "boolean")
            .field("ratio", true, "number");

        // All types match
        let valid = json!({
            "name": "app",
            "port": 8080,
            "debug": true,
            "ratio": 0.5
        });
        assert!(schema.validate(&valid).is_ok());

        // Wrong type: port is a string, not integer
        let invalid = json!({
            "name": "app",
            "port": "8080",
            "debug": true,
            "ratio": 0.5
        });
        let err = schema.validate(&invalid).unwrap_err();
        match err {
            SchemaError::WrongType { field, expected, .. } => {
                assert_eq!(field, "port");
                assert_eq!(expected, "integer");
            }
            other => panic!("expected WrongType, got {:?}", other),
        }
    }
}
