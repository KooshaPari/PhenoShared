//! Runtime AgentPort adapter selection for the AgilePlus CLI.
//!
//! AgilePlus owns planning, state, and governance. Substrate owns provider
//! dispatch and low-token cockpit events.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use agileplus_domain::error::DomainError;
use agileplus_domain::ports::agent::{
    AgentConfig, AgentKind, AgentPort, AgentResult, AgentStatus, AgentTask,
};

use crate::agent_stub::StubAgentAdapter;

mod substrate;
use self::substrate::{
    build_prompt, build_substrate_dispatch, cockpit_update_for, emit_cockpit_update,
    emit_cockpit_update_blocking, terminate_process,
};

pub enum ConfiguredAgentAdapter {
    Substrate(SubstrateAgentAdapter),
    Stub(StubAgentAdapter),
}

impl ConfiguredAgentAdapter {
    pub fn from_env() -> Self {
        match std::env::var("AGILEPLUS_AGENT_BACKEND") {
            Ok(value) if value.eq_ignore_ascii_case("stub") => Self::Stub(StubAgentAdapter),
            _ => Self::Substrate(SubstrateAgentAdapter::from_env()),
        }
    }
}

impl AgentPort for ConfiguredAgentAdapter {
    async fn dispatch(
        &self,
        task: AgentTask,
        config: &AgentConfig,
    ) -> Result<AgentResult, DomainError> {
        match self {
            Self::Substrate(adapter) => adapter.dispatch(task, config).await,
            Self::Stub(adapter) => adapter.dispatch(task, config).await,
        }
    }

    async fn dispatch_async(
        &self,
        task: AgentTask,
        config: &AgentConfig,
    ) -> Result<String, DomainError> {
        match self {
            Self::Substrate(adapter) => adapter.dispatch_async(task, config).await,
            Self::Stub(adapter) => adapter.dispatch_async(task, config).await,
        }
    }

    async fn query_status(&self, job_id: &str) -> Result<AgentStatus, DomainError> {
        match self {
            Self::Substrate(adapter) => adapter.query_status(job_id).await,
            Self::Stub(adapter) => adapter.query_status(job_id).await,
        }
    }

    async fn cancel(&self, job_id: &str) -> Result<(), DomainError> {
        match self {
            Self::Substrate(adapter) => adapter.cancel(job_id).await,
            Self::Stub(adapter) => adapter.cancel(job_id).await,
        }
    }

    async fn send_instruction(&self, job_id: &str, instruction: &str) -> Result<(), DomainError> {
        match self {
            Self::Substrate(adapter) => adapter.send_instruction(job_id, instruction).await,
            Self::Stub(adapter) => adapter.send_instruction(job_id, instruction).await,
        }
    }
}

pub struct SubstrateAgentAdapter {
    bin: String,
    cockpit_url: Option<String>,
    running: Arc<Mutex<HashMap<String, RunningJob>>>,
    completed: Arc<Mutex<HashMap<String, AgentResult>>>,
}

#[derive(Debug, Clone)]
struct RunningJob {
    pid: u32,
    task: AgentTask,
}

impl SubstrateAgentAdapter {
    pub fn from_env() -> Self {
        Self {
            bin: std::env::var("SUBSTRATE_BIN").unwrap_or_else(|_| "substrate".to_string()),
            cockpit_url: std::env::var("AGILEPLUS_COCKPIT_URL")
                .ok()
                .or_else(|| std::env::var("SUBSTRATE_COCKPIT_URL").ok()),
            running: Arc::new(Mutex::new(HashMap::new())),
            completed: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn run_id(task: &AgentTask) -> String {
        format!(
            "agileplus-{}-{}-{}",
            task.feature_slug,
            task.wp_id,
            chrono::Utc::now().timestamp_millis()
        )
    }

    fn engine(kind: AgentKind) -> &'static str {
        match kind {
            AgentKind::ClaudeCode => "claude",
            AgentKind::Codex => "codex",
        }
    }
}

impl AgentPort for SubstrateAgentAdapter {
    async fn dispatch(
        &self,
        task: AgentTask,
        config: &AgentConfig,
    ) -> Result<AgentResult, DomainError> {
        let job_id = Self::run_id(&task);
        emit_cockpit_update(
            self.cockpit_url.as_deref(),
            cockpit_update_for(&job_id, &task, "running", 0.0, "agent dispatched"),
        )
        .await;
        let prompt = build_prompt(&task)?;
        let output = build_substrate_dispatch(&self.bin, &job_id, &task, config, &prompt, false)?
            .output()
            .map_err(|err| DomainError::Other(format!("executing substrate dispatch: {err}")))?;
        let result = AgentResult {
            success: output.status.success(),
            pr_url: None,
            commits: vec![],
            stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
            stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
            exit_code: output.status.code().unwrap_or(-1),
        };
        emit_cockpit_update(
            self.cockpit_url.as_deref(),
            cockpit_update_for(
                &job_id,
                &task,
                if result.success {
                    "completed"
                } else {
                    "failed"
                },
                1.0,
                if result.success {
                    "agent completed"
                } else {
                    "agent failed"
                },
            ),
        )
        .await;
        Ok(result)
    }

    async fn dispatch_async(
        &self,
        task: AgentTask,
        config: &AgentConfig,
    ) -> Result<String, DomainError> {
        let job_id = Self::run_id(&task);
        emit_cockpit_update(
            self.cockpit_url.as_deref(),
            cockpit_update_for(&job_id, &task, "running", 0.0, "agent dispatched"),
        )
        .await;
        let prompt = build_prompt(&task)?;
        let child = build_substrate_dispatch(&self.bin, &job_id, &task, config, &prompt, true)?
            .spawn()
            .map_err(|err| DomainError::Other(format!("spawning substrate dispatch: {err}")))?;
        let pid = child.id();
        self.running
            .lock()
            .map_err(|_| DomainError::Other("substrate running cache poisoned".to_string()))?
            .insert(
                job_id.clone(),
                RunningJob {
                    pid,
                    task: task.clone(),
                },
            );

        let running = Arc::clone(&self.running);
        let completed = Arc::clone(&self.completed);
        let cockpit_url = self.cockpit_url.clone();
        let task_for_update = task.clone();
        let waiter_job_id = job_id.clone();
        std::thread::spawn(move || {
            let result = match child.wait_with_output() {
                Ok(output) => AgentResult {
                    success: output.status.success(),
                    pr_url: None,
                    commits: vec![],
                    stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
                    stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
                    exit_code: output.status.code().unwrap_or(-1),
                },
                Err(err) => AgentResult {
                    success: false,
                    pr_url: None,
                    commits: vec![],
                    stdout: String::new(),
                    stderr: format!("waiting for substrate dispatch: {err}"),
                    exit_code: -1,
                },
            };
            emit_cockpit_update_blocking(
                cockpit_url.as_deref(),
                cockpit_update_for(
                    &waiter_job_id,
                    &task_for_update,
                    if result.success {
                        "completed"
                    } else {
                        "failed"
                    },
                    1.0,
                    if result.success {
                        "agent completed"
                    } else {
                        "agent failed"
                    },
                ),
            );

            if let Ok(mut running) = running.lock() {
                running.remove(&waiter_job_id);
            }
            if let Ok(mut completed) = completed.lock() {
                completed.insert(waiter_job_id, result);
            }
        });

        Ok(job_id)
    }

    async fn query_status(&self, job_id: &str) -> Result<AgentStatus, DomainError> {
        let running_pid = self
            .running
            .lock()
            .map_err(|_| DomainError::Other("substrate running cache poisoned".to_string()))?
            .get(job_id)
            .cloned();
        if let Some(job) = running_pid {
            return Ok(AgentStatus::Running { pid: job.pid });
        }

        let result = self
            .completed
            .lock()
            .map_err(|_| DomainError::Other("substrate result cache poisoned".to_string()))?
            .get(job_id)
            .cloned();
        Ok(match result {
            Some(result) if result.success => AgentStatus::Completed { result },
            Some(result) => AgentStatus::Failed {
                error: result.stderr,
            },
            None => AgentStatus::Pending,
        })
    }

    async fn cancel(&self, job_id: &str) -> Result<(), DomainError> {
        let running_job = self
            .running
            .lock()
            .map_err(|_| DomainError::Other("substrate running cache poisoned".to_string()))?
            .remove(job_id);
        let Some(job) = running_job else {
            return Ok(());
        };

        terminate_process(job.pid)?;
        let result = AgentResult {
            success: false,
            pr_url: None,
            commits: vec![],
            stdout: String::new(),
            stderr: "canceled by AgilePlus".to_string(),
            exit_code: -1,
        };
        self.completed
            .lock()
            .map_err(|_| DomainError::Other("substrate result cache poisoned".to_string()))?
            .insert(job_id.to_string(), result);
        emit_cockpit_update(
            self.cockpit_url.as_deref(),
            cockpit_update_for(job_id, &job.task, "canceled", 1.0, "agent canceled"),
        )
        .await;
        Ok(())
    }

    async fn send_instruction(&self, _job_id: &str, instruction: &str) -> Result<(), DomainError> {
        eprintln!("Substrate instruction channel is not persistent yet:\n{instruction}");
        Ok(())
    }
}
