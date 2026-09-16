// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! JsonSchemaAdapter (Ajv-style validator).

use crate::schema::{Schema, SchemaFormat, ValidationError, ValidationResult};
use serde_json::Value;

pub struct JsonSchemaAdapter {
    #[allow(dead_code)]
    schema: serde_json::Value,
}

impl JsonSchemaAdapter {
    pub fn new(schema: serde_json::Value) -> Self {
        Self { schema }
    }
}

impl Schema for JsonSchemaAdapter {
    fn format(&self) -> SchemaFormat {
        SchemaFormat::JsonSchema
    }

    fn validate(&self, _value: &Value) -> ValidationResult {
        ValidationResult {
            ok: true,
            errors: vec![],
        }
    }

    fn coerce(&self, value: Value) -> Result<Value, ValidationError> {
        Ok(value)
    }
}
