//! JSON Schema export for the MCP server and CLI.

use schemars::schema_for;

use crate::spec::{ElicitResponse, PromptSpec};

/// Return the JSON Schema for [`PromptSpec`].
///
/// Used by the MCP server as the `inputSchema` for `phinbox_mcp`.
#[must_use]
pub fn prompt_spec_schema() -> serde_json::Value {
    serde_json::to_value(schema_for!(PromptSpec)).expect("PromptSpec schema serializes")
}

/// Return the JSON Schema for [`ElicitResponse`].
///
/// Used by the MCP server as the `outputSchema` for `phinbox_mcp`.
#[must_use]
pub fn elicit_response_schema() -> serde_json::Value {
    serde_json::to_value(schema_for!(ElicitResponse)).expect("ElicitResponse schema serializes")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prompt_spec_schema_has_title() {
        let s = prompt_spec_schema();
        // schemars adds "title" for the root schema
        assert!(s.get("title").is_some() || s.get("$ref").is_some());
    }

    #[test]
    fn response_schema_has_tag() {
        let s = elicit_response_schema();
        // The schema should mention the "status" tag field
        let s_str = serde_json::to_string(&s).unwrap();
        assert!(
            s_str.contains("status") || s_str.contains("$ref"),
            "response schema must reference status: {s_str}"
        );
    }
}