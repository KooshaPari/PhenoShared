// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! T68: PhenoSchema hexagonal port — Schema.
//!
//! 3 adapters: JsonSchema (Ajv), Zod, CborSchema.
//! Domain code depends on this trait, not on a specific schema engine.

use serde::{Deserialize, Serialize};

/// JSON Pointer-like path within a document.
pub type Path = Vec<String>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ValidationError {
    pub path: Path,
    pub message: String,
    pub code: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub ok: bool,
    pub errors: Vec<ValidationError>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum SchemaFormat {
    JsonSchema,
    Zod,
    Cbor,
}

/// Hexagonal port: a schema that can validate + coerce values.
pub trait Schema: Send + Sync {
    fn format(&self) -> SchemaFormat;
    fn validate(&self, value: &serde_json::Value) -> ValidationResult;
    fn coerce(&self, value: serde_json::Value) -> Result<serde_json::Value, ValidationError>;
}
