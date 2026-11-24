//! Eidolon Sandbox — Container and VM automation.
//!
//! Phase-3 Migration (per findings/2026-06-17-eidolon-absorption.md):
//! - Docker: Orchestration helpers from KVirtualStage/docker/
//! - nanoVMs: Isolation helpers from KVirtualStage/nanovms/
//! - PlayCua: Desktop/sandbox backend dispatcher (see `playcua_dispatcher`).
//! - Orchestration: process-compose patterns and resource governance
//!
//! # Input validation contract
//!
//! Every `SandboxAutomator` impl in this crate gates [`SandboxClient`]
//! through [`eidolon_core::security`] before any payload touches a
//! real backend:
//!
//! - [`SandboxClient::new`] validates the `sandbox_id` up front via
//!   [`validate_sandbox_id`](eidolon_core::security::validate_sandbox_id),
//!   so a malformed id can never reach the (eventual) container /
//!   microVM lifecycle hooks.
//! - [`SandboxClient::exec`] validates the command string via
//!   [`validate_exec_cmd`](eidolon_core::security::validate_exec_cmd),
//!   so shell metacharacter injection is rejected at the trait
//!   boundary rather than silently passed to a future `sh -c`.
//!
//! Both validators emit [`PhenoError::BadRequest`] for malformed input
//! and [`PhenoError::Forbidden`] for policy rejections — see the
//! [`eidolon_core::security`] module docs for the rule set.

use eidolon_core::security::{validate_exec_cmd, validate_sandbox_id, SandboxPolicy};
use eidolon_core::traits::{ResourceUsage, SandboxAutomator, SandboxMetadata};
use eidolon_core::{AutomationEvent, Result};

pub mod docker;
pub mod playcua_dispatcher;

pub use playcua_dispatcher::{NullPlayCuaPort, PlayCuaConfig, PlayCuaDispatcher, PlayCuaPort};

/// Sandbox automation implementer.
#[derive(Debug)]
pub struct SandboxClient {
    sandbox_id: String,
    /// Isolation policy the future Docker / nanoVMs / Firecracker
    /// backend should enforce. Carried as a value today so the public
    /// API stays stable when real isolation backends land; the stub
    /// impls read it only to populate the metadata response.
    policy: SandboxPolicy,
}

impl SandboxClient {
    /// Construct a sandbox client with the default isolation policy.
    ///
    /// Returns [`PhenoError::BadRequest`] if `sandbox_id` fails
    /// [`validate_sandbox_id`](eidolon_core::security::validate_sandbox_id)
    /// — i.e. is empty, too long, contains a forbidden byte, or starts
    /// with `-`.
    pub fn new(sandbox_id: &str) -> Result<Self> {
        validate_sandbox_id(sandbox_id)?;
        Ok(Self {
            sandbox_id: sandbox_id.to_string(),
            policy: SandboxPolicy::default(),
        })
    }

    /// Construct a sandbox client with an explicit isolation policy.
    ///
    /// Same id-validation contract as [`SandboxClient::new`]. Use this
    /// when the caller wants to express non-default isolation
    /// guarantees (e.g. `cpu_cores = 4`, `network = Allow` for an
    /// automation that legitimately needs egress).
    pub fn with_policy(sandbox_id: &str, policy: SandboxPolicy) -> Result<Self> {
        validate_sandbox_id(sandbox_id)?;
        Ok(Self {
            sandbox_id: sandbox_id.to_string(),
            policy,
        })
    }

    /// Borrow the configured isolation policy (for inspection / logging
    /// by callers that don't yet need to dispatch a real backend).
    pub fn policy(&self) -> &SandboxPolicy {
        &self.policy
    }
}

#[async_trait::async_trait]
impl SandboxAutomator for SandboxClient {
    async fn get_metadata(&self) -> Result<SandboxMetadata> {
        // TODO: Integrate nanoVMs / Docker / KVM introspection.
        // For now, surface the configured policy so callers can see
        // what was requested even though the backend is a stub.
        Ok(SandboxMetadata {
            id: self.sandbox_id.clone(),
            image: "stub:latest".to_string(),
            cpu_limit: self.policy.cpu_cores,
            memory_limit_mb: self.policy.memory_mib,
            disk_limit_mb: self.policy.disk_mib,
        })
    }

    async fn start(&self) -> Result<()> {
        log::info!(
            "Starting sandbox {} (cpu={} mem={}MiB disk={:?}MiB net={:?})",
            self.sandbox_id,
            self.policy.cpu_cores,
            self.policy.memory_mib,
            self.policy.disk_mib,
            self.policy.network
        );
        Ok(())
    }

    async fn stop(&self) -> Result<()> {
        log::info!("Stopping sandbox {}", self.sandbox_id);
        Ok(())
    }

    async fn exec(&self, cmd: &str) -> Result<String> {
        validate_exec_cmd(cmd)?;
        log::info!("Executing in sandbox {}: {}", self.sandbox_id, cmd);
        Ok("stub output".to_string())
    }

    async fn resource_usage(&self) -> Result<ResourceUsage> {
        Ok(ResourceUsage {
            cpu_percent: 0.0,
            memory_mb: 128,
            disk_mb: Some(512),
        })
    }

    async fn record_event(&self, event: AutomationEvent) -> Result<()> {
        log::debug!("Recorded sandbox event: {:?}", event);
        Ok(())
    }
}
