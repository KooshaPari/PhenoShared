// Fixture source file for trace-gate integration tests.
// FR-001 and FR-002 are annotated here; FR-003 is deliberately absent.

#[trace_fr(spec = "SPEC-001", fr = "FR-001")]
pub fn login(username: &str, _password: &str) -> bool {
    !username.is_empty()
}

// FR: FR-002
pub fn register(username: &str) -> bool {
    !username.is_empty()
}
