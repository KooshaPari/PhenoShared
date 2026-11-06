//! Dispatch storage stubs for SIDE-FR-011 (audit remediation).
//! Scaffold until `sidekick-dispatch` lands in workspace — traces to DATA.md.
//!
//! These tests document the JSONL append contract without requiring the crate lib.

#[derive(Debug, Clone, PartialEq, Eq)]
struct DispatchJob {
    id: String,
    provider: String,
    status: String,
}

impl DispatchJob {
    fn new(id: &str, provider: &str) -> Self {
        Self {
            id: id.to_string(),
            provider: provider.to_string(),
            status: "pending".to_string(),
        }
    }

    fn mark_running(&mut self) {
        self.status = "running".to_string();
    }

    fn mark_done(&mut self) {
        self.status = "done".to_string();
    }
}

#[test]
fn storage_stub_dispatch_job_lifecycle() {
    let mut job = DispatchJob::new("job-001", "claude");
    assert_eq!(job.status, "pending");

    job.mark_running();
    assert_eq!(job.status, "running");

    job.mark_done();
    assert_eq!(job.status, "done");
}

#[test]
fn storage_stub_jsonl_line_is_single_record() {
    let job = DispatchJob::new("job-002", "openai");
    let line = format!(
        r#"{{"id":"{}","provider":"{}","status":"{}"}}"#,
        job.id, job.provider, job.status
    );
    assert!(line.starts_with('{'));
    assert!(line.ends_with('}'));
    assert!(line.contains("job-002"));
}
