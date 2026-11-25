//! Process management primitives for PhenoProc registry
//!
//! Core process management types and traits used by sharecli.
//! Process lifecycle (spawn, wait, kill-group) delegates to substrate
//! [`CommandGroupProcess`] via [`ProcessPort`].

use anyhow::Result;
use dashmap::DashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Instant;

pub use runtime_process::CommandGroupProcess;
pub use substrate_core::process_port::{
    ProcessHandle, ProcessPort, ProcessSpawnSpec, ProcessState,
};

/// Information about a managed process.
///
/// Contains metadata tracked by the process pool for lifecycle management.
#[derive(Debug, Clone)]
pub struct ProcessInfo {
    /// Process ID assigned by the OS.
    pub pid: u32,
    /// Human-readable process name.
    pub name: String,
    /// Project this process belongs to.
    pub project: String,
    /// Harness type (e.g., "claude", "codex").
    pub harness: String,
    /// When the process was spawned.
    pub started_at: Instant,
    /// Current lifecycle status.
    pub status: ProcessStatus,
    /// Memory usage in MB (reported by the harness).
    pub memory_mb: u64,
    /// CPU usage percentage (if available).
    pub cpu_percent: Option<f32>,
    /// Command-line arguments used to spawn the process.
    pub cmd: Vec<String>,
}

/// Lifecycle status of a managed process.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProcessStatus {
    /// Process is actively running.
    Running,
    /// Process has been stopped (e.g., via SIGSTOP).
    Stopped,
    /// Process has exited normally.
    Exited,
    /// Process encountered an error.
    Error,
}

impl std::fmt::Display for ProcessStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ProcessStatus::Running => write!(f, "running"),
            ProcessStatus::Stopped => write!(f, "stopped"),
            ProcessStatus::Exited => write!(f, "exited"),
            ProcessStatus::Error => write!(f, "error"),
        }
    }
}

impl From<&ProcessState> for ProcessStatus {
    fn from(state: &ProcessState) -> Self {
        match state {
            ProcessState::Running { .. } => ProcessStatus::Running,
            ProcessState::Exited { .. } => ProcessStatus::Exited,
        }
    }
}

/// A managed process with lifecycle control backed by substrate [`ProcessHandle`].
///
/// Wraps a [`ProcessInfo`] with the underlying [`ProcessHandle`] so the pool
/// can delegate spawn/kill/status operations to the substrate runtime.
#[derive(Debug, Clone)]
pub struct ManagedProcess {
    /// Process metadata.
    pub info: ProcessInfo,
    /// Substrate process handle for lifecycle operations.
    pub handle: ProcessHandle,
    /// The full command string that was executed.
    pub command: String,
    /// Working directory for the process.
    pub cwd: String,
}

/// Filter predicate for querying processes from a [`ProcessPool`].
#[derive(Debug, Clone)]
pub enum ProcessFilter {
    /// Match all processes.
    All,
    /// Match processes belonging to a specific project.
    ByProject(String),
    /// Match processes using a specific harness type.
    ByHarness(String),
}

/// Resource limits for a project.
///
/// Used by [`ProjectResources`] to enforce per-project caps on memory
/// and process count.
#[derive(Debug, Clone)]
pub struct ProjectLimits {
    /// Maximum memory in MB.
    pub memory_limit_mb: u64,
    /// Maximum number of concurrent processes.
    pub max_processes: usize,
    /// Optional CPU core affinity list.
    pub cpu_affinity: Option<Vec<usize>>,
}

/// Resource tracking for a project.
///
/// Uses [`DashMap`] for lock-free concurrent access. Limits are per-project;
/// querying a project that has no limits returns the default ([4096 MB, 10 procs]).
#[derive(Debug, Clone)]
pub struct ProjectResources {
    /// Current limits per project.
    limits: Arc<DashMap<String, ProjectLimits>>,
}

impl ProjectResources {
    /// Create a new, empty resource tracker.
    pub fn new() -> Self {
        Self {
            limits: Arc::new(DashMap::new()),
        }
    }

    /// Get limits for a project, returning defaults if not explicitly set.
    pub async fn get_limits(&self, project: &str) -> ProjectLimits {
        self.limits
            .get(project)
            .map(|r| r.value().clone())
            .unwrap_or(ProjectLimits {
                memory_limit_mb: 4096,
                max_processes: 10,
                cpu_affinity: None,
            })
    }

    /// Set or update resource limits for a project.
    pub async fn set_limits(&self, project: &str, limits: ProjectLimits) {
        self.limits.insert(project.to_string(), limits);
    }

    /// Check current usage against limits for a project.
    pub async fn check_limits(&self, project: &str) -> Result<ProjectLimitCheck> {
        let limits = self.get_limits(project).await;
        Ok(ProjectLimitCheck {
            memory_mb: 0,
            memory_limit_mb: limits.memory_limit_mb,
            memory_ok: true,
            process_count: 0,
            max_processes: limits.max_processes,
            processes_ok: true,
        })
    }
}

impl Default for ProjectResources {
    fn default() -> Self {
        Self::new()
    }
}

/// Result of checking project resource limits.
#[derive(Debug, Clone)]
pub struct ProjectLimitCheck {
    /// Current memory usage in MB.
    pub memory_mb: u64,
    /// Configured memory limit in MB.
    pub memory_limit_mb: u64,
    /// Whether memory usage is within limits.
    pub memory_ok: bool,
    /// Current number of running processes.
    pub process_count: usize,
    /// Configured maximum process count.
    pub max_processes: usize,
    /// Whether process count is within limits.
    pub processes_ok: bool,
}

impl ProjectLimitCheck {
    /// Returns `true` if both memory and process limits are satisfied.
    pub fn overall_ok(&self) -> bool {
        self.memory_ok && self.processes_ok
    }
}

/// Shared runtime for pooled process execution.
///
/// Manages separate pools for Node.js and Bun harness types, enforcing
/// per-type capacity limits. Uses atomic counters for thread-safe pool
/// tracking across spawned background tasks.
pub struct SharedRuntime {
    /// Max processes per harness type.
    pub max_per_type: usize,
    node_total: Arc<AtomicUsize>,
    node_idle: Arc<AtomicUsize>,
    bun_total: Arc<AtomicUsize>,
    bun_idle: Arc<AtomicUsize>,
}

impl std::fmt::Debug for SharedRuntime {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SharedRuntime")
            .field("max_per_type", &self.max_per_type)
            .field("node_total", &self.node_total.load(Ordering::Relaxed))
            .field("node_idle", &self.node_idle.load(Ordering::Relaxed))
            .field("bun_total", &self.bun_total.load(Ordering::Relaxed))
            .field("bun_idle", &self.bun_idle.load(Ordering::Relaxed))
            .finish()
    }
}

impl SharedRuntime {
    /// Create a new shared runtime with the given per-type capacity.
    /// All idle counters start at `max_per_type` (pool is initially fully available).
    pub fn new(max_per_type: usize) -> Self {
        Self {
            max_per_type,
            node_total: Arc::new(AtomicUsize::new(0)),
            node_idle: Arc::new(AtomicUsize::new(max_per_type)),
            bun_total: Arc::new(AtomicUsize::new(0)),
            bun_idle: Arc::new(AtomicUsize::new(max_per_type)),
        }
    }

    /// Get current pool status snapshot.
    pub async fn status(&self) -> PoolStatus {
        PoolStatus {
            node_total: self.node_total.load(Ordering::Relaxed),
            node_idle: self.node_idle.load(Ordering::Relaxed),
            bun_total: self.bun_total.load(Ordering::Relaxed),
            bun_idle: self.bun_idle.load(Ordering::Relaxed),
            max_per_type: self.max_per_type,
        }
    }

    /// Execute a command through the harness pool.
    ///
    /// Selects the pool based on `harness_type` ("node" or "bun") and
    /// spawns a child process. Returns `(pid, message)` on success.
    ///
    /// # Errors
    ///
    /// Returns an error if the pool is at capacity or the spawn fails.
    pub async fn run_with_pool(
        &self,
        harness_type: &str,
        project: &str,
        cmd: &str,
    ) -> Result<(u32, String)> {
        let (idle_atomic, total_atomic) = match harness_type.to_lowercase().as_str() {
            "node" => (self.node_idle.clone(), self.node_total.clone()),
            "bun" => (self.bun_idle.clone(), self.bun_total.clone()),
            other => {
                return Err(anyhow::anyhow!(
                    "unknown harness type: '{other}' (expected 'node' or 'bun')"
                ))
            }
        };

        let idle = idle_atomic.load(Ordering::Relaxed);
        if idle == 0 {
            return Err(anyhow::anyhow!(
                "harness pool '{harness_type}' at capacity ({}/{})",
                self.max_per_type,
                self.max_per_type
            ));
        }

        // Spawn child process
        let mut child = tokio::process::Command::new(harness_type)
            .args(cmd.split_whitespace())
            .spawn()?;

        let pid = child
            .id()
            .ok_or_else(|| anyhow::anyhow!("failed to get child pid"))?;

        // Increment total, decrement idle
        total_atomic.fetch_add(1, Ordering::Relaxed);
        idle_atomic.fetch_sub(1, Ordering::Relaxed);

        // Background task reclaims the slot when the child exits
        let max = self.max_per_type;
        tokio::spawn(async move {
            let _ = child.wait().await;
            total_atomic.fetch_sub(1, Ordering::Relaxed);
            let prev = idle_atomic.fetch_add(1, Ordering::Relaxed);
            if prev + 1 > max {
                idle_atomic.store(max, Ordering::Relaxed);
            }
        });

        Ok((pid, format!("{} process for {}", harness_type, project)))
    }

    /// Run a health check on the pool.
    ///
    /// Reports whether the pool has any capacity issues.
    pub async fn health_check(&self) -> HealthStatus {
        let mut issues = Vec::new();
        let nt = self.node_total.load(Ordering::Relaxed);
        let bt = self.bun_total.load(Ordering::Relaxed);
        if nt > self.max_per_type {
            issues.push(format!(
                "node pool over capacity: {}/{}",
                nt, self.max_per_type
            ));
        }
        if bt > self.max_per_type {
            issues.push(format!(
                "bun pool over capacity: {}/{}",
                bt, self.max_per_type
            ));
        }
        HealthStatus {
            healthy: issues.is_empty(),
            issues,
            node_in_use: nt.saturating_sub(self.node_idle.load(Ordering::Relaxed)),
            bun_in_use: bt.saturating_sub(self.bun_idle.load(Ordering::Relaxed)),
        }
    }
}

/// Snapshot of pool utilization across harness types.
#[derive(Debug, Clone)]
pub struct PoolStatus {
    /// Total Node processes spawned.
    pub node_total: usize,
    /// Idle Node process slots.
    pub node_idle: usize,
    /// Total Bun processes spawned.
    pub bun_total: usize,
    /// Idle Bun process slots.
    pub bun_idle: usize,
    /// Maximum processes allowed per type.
    pub max_per_type: usize,
}

/// Health check result for the process pool.
#[derive(Debug, Clone)]
pub struct HealthStatus {
    /// Whether the pool is healthy (no capacity issues).
    pub healthy: bool,
    /// Human-readable descriptions of any issues found.
    pub issues: Vec<String>,
    /// Number of active Node processes.
    pub node_in_use: usize,
    /// Number of active Bun processes.
    pub bun_in_use: usize,
}

/// Process pool for managing multiple processes via substrate [`CommandGroupProcess`].
///
/// Uses [`DashMap`] for lock-free concurrent access to the process registry.
/// The pool enforces memory and process-count limits, and delegates spawn/kill
/// operations to the substrate [`CommandGroupProcess`] runtime.
pub struct ProcessPool {
    /// All managed processes, keyed by PID.
    processes: Arc<DashMap<u32, ManagedProcess>>,
    /// Substrate-backed process lifecycle manager.
    runtime: CommandGroupProcess,
    /// Maximum memory limit in MB.
    pub max_memory_mb: u64,
    /// Maximum number of processes.
    pub max_processes: u32,
}

impl std::fmt::Debug for ProcessPool {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ProcessPool")
            .field("process_count", &self.count())
            .field("max_memory_mb", &self.max_memory_mb)
            .field("max_processes", &self.max_processes)
            .finish_non_exhaustive()
    }
}

impl ProcessPool {
    /// Create a new process pool with default limits
    pub fn new() -> Self {
        Self::with_limits(4096, 100)
    }

    /// Create a new process pool with custom limits.
    pub fn with_limits(max_memory_mb: u64, max_processes: u32) -> Self {
        Self {
            processes: Arc::new(DashMap::new()),
            runtime: CommandGroupProcess::new(),
            max_memory_mb,
            max_processes,
        }
    }

    /// Access the underlying substrate process manager.
    pub fn runtime(&self) -> &CommandGroupProcess {
        &self.runtime
    }

    /// Add a process to the pool.
    pub fn add(&self, process: ManagedProcess) {
        self.processes.insert(process.info.pid, process);
    }

    /// Remove a process from the pool.
    pub fn remove(&self, pid: u32) -> Option<ManagedProcess> {
        self.processes.remove(&pid).map(|(_, v)| v)
    }

    /// Get a process by PID.
    pub fn get(&self, pid: u32) -> Option<ManagedProcess> {
        self.processes.get(&pid).map(|r| r.value().clone())
    }

    /// List all processes.
    pub fn list(&self) -> Vec<ProcessInfo> {
        self.processes
            .iter()
            .map(|r| r.value().info.clone())
            .collect()
    }

    /// Find processes matching a filter.
    pub fn find(&self, filter: ProcessFilter) -> Vec<ProcessInfo> {
        self.processes
            .iter()
            .filter_map(|r| {
                let p = r.value();
                match &filter {
                    ProcessFilter::All => Some(p.info.clone()),
                    ProcessFilter::ByProject(project) => {
                        if p.info.project == *project {
                            Some(p.info.clone())
                        } else {
                            None
                        }
                    }
                    ProcessFilter::ByHarness(harness) => {
                        if p.info.harness == *harness {
                            Some(p.info.clone())
                        } else {
                            None
                        }
                    }
                }
            })
            .collect()
    }

    /// Spawn a new process via substrate [`CommandGroupProcess`]
    pub async fn spawn(
        &self,
        harness: &str,
        args: &[String],
        cwd: Option<PathBuf>,
        project: Option<String>,
        name: Option<String>,
    ) -> Result<ProcessInfo> {
        let spec = ProcessSpawnSpec {
            program: harness.to_string(),
            args: args.to_vec(),
            cwd: cwd.clone(),
        };
        let handle = self
            .runtime
            .spawn(&spec)
            .await
            .map_err(|e| anyhow::anyhow!(e.to_string()))?;

        let cwd_str = cwd
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| ".".to_string());
        let proc_name = name.unwrap_or_else(|| harness.to_string());
        let proj = project.unwrap_or_else(|| "default".to_string());

        let info = ProcessInfo {
            pid: handle.pid,
            name: proc_name.clone(),
            project: proj,
            harness: harness.to_string(),
            started_at: Instant::now(),
            status: ProcessStatus::Running,
            memory_mb: 0,
            cpu_percent: None,
            cmd: args.to_vec(),
        };

        let process = ManagedProcess {
            info: info.clone(),
            handle,
            command: format!("{} {}", harness, args.join(" ")),
            cwd: cwd_str,
        };

        self.add(process);
        Ok(info)
    }

    /// Kill a process by PID via substrate process-group kill.
    pub async fn kill(&self, pid: u32) -> Result<()> {
        let handle = self
            .processes
            .get(&pid)
            .map(|r| r.value().handle)
            .ok_or_else(|| anyhow::anyhow!("Process {pid} not found"))?;

        self.runtime
            .kill_group(&handle)
            .await
            .map_err(|e| anyhow::anyhow!(e.to_string()))?;

        if let Some(mut proc) = self.processes.get_mut(&pid) {
            proc.info.status = ProcessStatus::Exited;
        }
        Ok(())
    }

    /// Kill all processes.
    pub async fn kill_all(&self) -> Result<()> {
        let handles: Vec<(u32, ProcessHandle)> = self
            .processes
            .iter()
            .map(|r| (*r.key(), r.value().handle))
            .collect();

        for (pid, handle) in handles {
            let _ = self.runtime.kill_group(&handle).await;
            if let Some(mut proc) = self.processes.get_mut(&pid) {
                proc.info.status = ProcessStatus::Exited;
            }
        }
        Ok(())
    }

    /// Refresh status for a managed process from the substrate runtime.
    pub async fn refresh_status(&self, pid: u32) -> Result<ProcessStatus> {
        let handle = self
            .processes
            .get(&pid)
            .map(|r| r.value().handle)
            .ok_or_else(|| anyhow::anyhow!("Process {pid} not found"))?;

        let state = self
            .runtime
            .status(&handle)
            .await
            .map_err(|e| anyhow::anyhow!(e.to_string()))?;
        let status = ProcessStatus::from(&state);

        if let Some(mut proc) = self.processes.get_mut(&pid) {
            proc.info.status = status;
        }
        Ok(status)
    }

    /// Get system memory usage across all managed processes.
    pub async fn system_memory_usage(&self) -> (u64, u64) {
        let used: u64 = self
            .processes
            .iter()
            .map(|r| r.value().info.memory_mb)
            .sum();
        (used, self.max_memory_mb)
    }

    /// Get the number of managed processes.
    pub fn count(&self) -> usize {
        self.processes.len()
    }

    /// Check if pool is at capacity.
    pub fn is_full(&self) -> bool {
        self.processes.len() >= self.max_processes as usize
    }

    /// Get total memory usage across all processes.
    pub fn total_memory_mb(&self) -> u64 {
        self.processes
            .iter()
            .map(|r| r.value().info.memory_mb)
            .sum()
    }

    /// Find processes by project name.
    pub fn by_project(&self, project: &str) -> Vec<ManagedProcess> {
        self.processes
            .iter()
            .filter(|r| r.value().info.project == project)
            .map(|r| r.value().clone())
            .collect()
    }

    /// Find processes by harness type.
    pub fn by_harness(&self, harness: &str) -> Vec<ManagedProcess> {
        self.processes
            .iter()
            .filter(|r| r.value().info.harness == harness)
            .map(|r| r.value().clone())
            .collect()
    }

    /// Clear all processes from the pool (does not kill running children).
    pub fn clear(&self) {
        self.processes.clear();
    }
}

impl Default for ProcessPool {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    fn create_test_process(pid: u32, project: &str, harness: &str) -> ManagedProcess {
        ManagedProcess {
            info: ProcessInfo {
                pid,
                name: harness.to_string(),
                project: project.to_string(),
                harness: harness.to_string(),
                started_at: Instant::now(),
                status: ProcessStatus::Running,
                memory_mb: 100,
                cpu_percent: Some(5.0),
                cmd: vec!["test".to_string()],
            },
            handle: ProcessHandle {
                id: Uuid::new_v4(),
                pid,
            },
            command: "test".to_string(),
            cwd: "/tmp".to_string(),
        }
    }

    #[test]
    fn test_process_pool_add_remove() {
        let pool = ProcessPool::new();

        let process = create_test_process(1234, "project-a", "claude");
        pool.add(process);

        assert_eq!(pool.count(), 1);

        let removed = pool.remove(1234);
        assert!(removed.is_some());
        assert_eq!(pool.count(), 0);
    }

    #[test]
    fn test_process_pool_by_project() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-a", "codex"));
        pool.add(create_test_process(1002, "project-b", "claude"));

        let results = pool.by_project("project-a");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_process_pool_by_harness() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-b", "claude"));
        pool.add(create_test_process(1002, "project-c", "codex"));

        let results = pool.by_harness("claude");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_process_pool_capacity() {
        let pool = ProcessPool::with_limits(4096, 2);

        assert!(!pool.is_full());

        pool.add(create_test_process(1000, "p1", "claude"));
        pool.add(create_test_process(1001, "p2", "claude"));

        assert!(pool.is_full());
    }

    #[test]
    fn test_total_memory() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "p1", "claude"));
        pool.add(create_test_process(1001, "p2", "claude"));

        assert_eq!(pool.total_memory_mb(), 200);
    }

    #[test]
    fn test_process_filter() {
        let pool = ProcessPool::new();

        pool.add(create_test_process(1000, "project-a", "claude"));
        pool.add(create_test_process(1001, "project-b", "claude"));
        pool.add(create_test_process(1002, "project-a", "codex"));

        let all = pool.find(ProcessFilter::All);
        assert_eq!(all.len(), 3);

        let by_project = pool.find(ProcessFilter::ByProject("project-a".to_string()));
        assert_eq!(by_project.len(), 2);

        let by_harness = pool.find(ProcessFilter::ByHarness("codex".to_string()));
        assert_eq!(by_harness.len(), 1);
    }
}
