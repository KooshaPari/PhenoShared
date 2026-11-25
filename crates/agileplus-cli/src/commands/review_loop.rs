//! Review-fix loop orchestrator.
//!
//! Polls for CI and code review status, feeds review feedback to the agent,
//! and iterates until approved or max cycles reached.
//! Traceability: FR-012 / WP12-T071

use agileplus_domain::domain::work_package::WorkPackage;
use agileplus_domain::ports::agent::{AgentConfig, AgentPort, AgentStatus};

/// Outcome of running the review-fix loop.
#[derive(Debug, Clone)]
pub enum ReviewOutcome {
    /// PR was approved and CI passed.
    Approved,
    /// Max cycles reached without approval.
    MaxCyclesReached { cycles: u32, last_feedback: String },
    /// Agent job failed during a fix cycle.
    AgentFailed { error: String },
    /// Loop was cancelled externally.
    Cancelled,
}

/// Run the review-fix loop for a work package.
///
/// In this scaffold implementation the loop polls the agent port for job
/// completion status. Full Coderabbit integration is wired in later when
/// the ReviewPort adapter (WP09) is available.
///
/// For now the loop:
///   1. Polls `AgentPort::query_status` until the agent completes.
///   2. If the agent returns success the PR is treated as approved.
///   3. If the agent indicates it is waiting for review we simulate a single
///      poll cycle that considers it approved (no-op review adapter).
///   4. If the agent fails we return `AgentFailed`.
///
/// Returns `ReviewOutcome`.
pub async fn run_review_loop<A: AgentPort>(
    wp: &WorkPackage,
    job_id: &str,
    agent: &A,
    _agent_config: &AgentConfig,
    max_cycles: u32,
    poll_interval_secs: u64,
) -> ReviewOutcome {
    let poll = std::time::Duration::from_secs(poll_interval_secs);
    let mut last_feedback = String::new();

    for cycle in 1..=max_cycles {
        println!("  Review cycle {cycle}/{max_cycles}: polling agent status...");

        // Poll with a timeout using tokio::time::timeout
        let status = match agent.query_status(job_id).await {
            Ok(s) => s,
            Err(e) => {
                tracing::warn!(error = %e, "error polling agent status");
                tokio::time::sleep(poll).await;
                continue;
            }
        };

        if let Some(outcome) =
            handle_agent_status(status, cycle, max_cycles, job_id, agent, &mut last_feedback).await
        {
            return outcome;
        }

        tokio::time::sleep(poll).await;
    }

    // One last status check closes the race where an async dispatch completes
    // just after the final sleep interval but before we declare the review loop blocked.
    match agent.query_status(job_id).await {
        Ok(status) => {
            if let Some(outcome) = handle_agent_status(
                status,
                max_cycles,
                max_cycles,
                job_id,
                agent,
                &mut last_feedback,
            )
            .await
            {
                return outcome;
            }
        }
        Err(e) => {
            tracing::warn!(error = %e, "error polling agent status during final review check");
        }
    }

    println!(
        "  Max review cycles ({max_cycles}) reached for WP {}.",
        wp.id
    );
    ReviewOutcome::MaxCyclesReached {
        cycles: max_cycles,
        last_feedback,
    }
}

async fn handle_agent_status<A: AgentPort>(
    status: AgentStatus,
    cycle: u32,
    max_cycles: u32,
    job_id: &str,
    agent: &A,
    last_feedback: &mut String,
) -> Option<ReviewOutcome> {
    match status {
        AgentStatus::Completed { result } => {
            if result.success {
                println!("  Agent completed successfully.");
                Some(ReviewOutcome::Approved)
            } else {
                *last_feedback = result.stderr.clone();
                println!(
                    "  Agent completed with failure: {}",
                    &result.stderr[..result.stderr.len().min(200)]
                );
                if cycle < max_cycles {
                    let instruction = format!(
                        "Your previous attempt failed. Please fix the following issues:\n\n{}",
                        result.stderr
                    );
                    if let Err(e) = agent.send_instruction(job_id, &instruction).await {
                        tracing::warn!(error = %e, "failed to send instruction to agent");
                    }
                }
                None
            }
        }
        AgentStatus::WaitingForReview { pr_url } => {
            println!("  Agent waiting for review at: {pr_url}");
            Some(ReviewOutcome::Approved)
        }
        AgentStatus::Failed { error } => {
            println!("  Agent failed: {error}");
            Some(ReviewOutcome::AgentFailed { error })
        }
        AgentStatus::Running { pid } => {
            tracing::debug!(pid = pid, "agent still running");
            None
        }
        AgentStatus::Pending => {
            tracing::debug!("agent pending");
            None
        }
    }
}

/// Format structured review comments into an agent instruction.
pub fn format_feedback(comments: &[String]) -> String {
    if comments.is_empty() {
        return "No actionable feedback.".to_string();
    }
    let items: Vec<String> = comments
        .iter()
        .enumerate()
        .map(|(i, c)| format!("{}. {}", i + 1, c))
        .collect();
    format!(
        "Please address the following review comments:\n\n{}\n",
        items.join("\n")
    )
}

#[cfg(test)]
mod tests {
    use std::collections::VecDeque;
    use std::path::PathBuf;
    use std::sync::Mutex;

    use agileplus_domain::domain::work_package::WorkPackage;
    use agileplus_domain::error::DomainError;
    use agileplus_domain::ports::agent::{AgentKind, AgentResult, AgentTask};

    use super::*;

    #[test]
    fn format_feedback_empty() {
        assert_eq!(format_feedback(&[]), "No actionable feedback.");
    }

    #[test]
    fn format_feedback_numbered() {
        let comments = vec!["Fix typo".to_string(), "Add test".to_string()];
        let result = format_feedback(&comments);
        assert!(result.contains("1. Fix typo"));
        assert!(result.contains("2. Add test"));
    }

    struct MockAgent {
        statuses: Mutex<VecDeque<AgentStatus>>,
    }

    impl MockAgent {
        fn new(statuses: Vec<AgentStatus>) -> Self {
            Self {
                statuses: Mutex::new(statuses.into()),
            }
        }
    }

    impl AgentPort for MockAgent {
        async fn dispatch(
            &self,
            _task: AgentTask,
            _config: &AgentConfig,
        ) -> Result<AgentResult, DomainError> {
            Err(DomainError::Other("unused in test".to_string()))
        }

        async fn dispatch_async(
            &self,
            _task: AgentTask,
            _config: &AgentConfig,
        ) -> Result<String, DomainError> {
            Err(DomainError::Other("unused in test".to_string()))
        }

        async fn query_status(&self, _job_id: &str) -> Result<AgentStatus, DomainError> {
            let mut statuses = self.statuses.lock().unwrap();
            Ok(statuses.pop_front().unwrap_or(AgentStatus::Pending))
        }

        async fn cancel(&self, _job_id: &str) -> Result<(), DomainError> {
            Ok(())
        }

        async fn send_instruction(
            &self,
            _job_id: &str,
            _instruction: &str,
        ) -> Result<(), DomainError> {
            Ok(())
        }
    }

    fn wp() -> WorkPackage {
        let mut wp = WorkPackage::new(1, "Test WP", 1, "done");
        wp.id = 1;
        wp.worktree_path = Some(PathBuf::from(".").display().to_string());
        wp
    }

    fn agent_config() -> AgentConfig {
        AgentConfig {
            kind: AgentKind::Codex,
            max_review_cycles: 1,
            timeout_secs: 60,
            extra_args: vec![],
        }
    }

    #[tokio::test]
    async fn review_loop_approves_if_job_completes_after_final_sleep() {
        let agent = MockAgent::new(vec![
            AgentStatus::Running { pid: 123 },
            AgentStatus::Completed {
                result: AgentResult {
                    success: true,
                    pr_url: None,
                    commits: vec![],
                    stdout: "ok".to_string(),
                    stderr: String::new(),
                    exit_code: 0,
                },
            },
        ]);

        let outcome = run_review_loop(&wp(), "job-1", &agent, &agent_config(), 1, 0).await;
        assert!(matches!(outcome, ReviewOutcome::Approved));
    }
}
