// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! ZodAdapter (delegates to zod-types via a JSON Schema bridge).

use crate::schema::{Schema, SchemaFormat, ValidationError, ValidationResult};
use serde_json::Value;

/// Adapter that uses a JSON-Schema-compatible validator to back the Schema port.
pub struct ZodAdapter {
    #[allow(dead_code)]
    json_schema: serde_json::Value,
}

impl ZodAdapter {
    pub fn new(json_schema: serde_json::Value) -> Self {
        Self { json_schema }
    }
}

impl Schema for ZodAdapter {
    fn format(&self) -> SchemaFormat {
        SchemaFormat::Zod
    }

    fn validate(&self, _value: &Value) -> ValidationResult {
        // In production, this would call into a zod-compatible validator.
        // For the port spec, we accept any value as a stub.
        ValidationResult {
            ok: true,
            errors: vec![],
        }
    }

    fn coerce(&self, value: Value) -> Result<Value, ValidationError> {
        Ok(value)
    }
}
