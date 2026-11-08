// SPDX-License-Identifier: MIT OR Apache-2.0

use pheno_mcp_defs::ToolError;

/// Unit test for the pure `From<std::io::Error>` conversion.
#[test]
fn tool_error_from_io_error_maps_correctly() {
    let io = std::io::Error::new(std::io::ErrorKind::NotFound, "missing manifest");
    let err: ToolError = io.into();
    assert_eq!(err, ToolError::Io("missing manifest".to_string()));
}
