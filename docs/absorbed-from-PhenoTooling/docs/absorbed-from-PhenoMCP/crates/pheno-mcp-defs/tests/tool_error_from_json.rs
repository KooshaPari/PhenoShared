// SPDX-License-Identifier: MIT OR Apache-2.0

use pheno_mcp_defs::ToolError;

/// Unit test for the pure `From<serde_json::Error>` conversion.
#[test]
fn tool_error_from_json_error_maps_correctly() {
    let json_err = serde_json::from_str::<serde_json::Value>("not valid json").unwrap_err();
    let err: ToolError = json_err.into();
    assert_eq!(err, ToolError::Parse("expected value at line 1 column 1".to_string()));
}
