//! Git adapter using subprocess commands
//!
//! Following Hexagonal Architecture: Infrastructure (Driven Adapter).

use crate::domain::{
    BranchName, DomainResult, Worktree, WorktreeError, WorktreeId, WorktreeListing,
};
use crate::ports::{BranchOperations, WorktreeRepository};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Git worktree adapter using git commands
#[derive(Clone)]
pub struct GitWorktreeAdapter;

impl GitWorktreeAdapter {
    pub fn new() -> Self {
        Self
    }

    fn run_git(&self, repo_path: &Path, args: &[&str]) -> Result<String, WorktreeError> {
        let output = Command::new("git")
            .args(["-C", repo_path.to_str().unwrap_or(".")])
            .args(args)
            .output()
            .map_err(|e| WorktreeError::GitError(format!("git command failed: {}", e)))?;

        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr);
            Err(WorktreeError::GitError(format!("git failed: {}", stderr)))
        }
    }

    /// Resolve paths for stable comparisons (macOS `/var` → `/private/var`).
    fn canonicalize_path(path: &Path) -> PathBuf {
        path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
    }

    fn same_path(a: &Path, b: &Path) -> bool {
        Self::canonicalize_path(a) == Self::canonicalize_path(b)
    }

    /// Route a parsed worktree into the main slot or the worktrees list.
    ///
    /// Extracted from `WorktreeRepository::list` to remove the duplicated
    /// "main vs linked" dispatch that previously appeared twice in the parser.
    fn push_record(wt: Worktree, main: &mut Option<Worktree>, worktrees: &mut Vec<Worktree>) {
        if wt.is_main {
            *main = Some(wt);
        } else {
            worktrees.push(wt);
        }
    }
}

impl Default for GitWorktreeAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl WorktreeRepository for GitWorktreeAdapter {
    fn list(&self, repo_path: &Path) -> DomainResult<WorktreeListing> {
        let output = self.run_git(repo_path, &["worktree", "list", "--porcelain"])?;
        let repo_canonical = Self::canonicalize_path(repo_path);

        let mut worktrees: Vec<Worktree> = Vec::new();
        let mut main: Option<Worktree> = None;
        let mut current: Option<Worktree> = None;
        // Git porcelain lists the primary worktree first; track that plus path
        // equality so macOS `/var` vs `/private/var` still classifies correctly.
        let mut seen_worktree = false;

        for line in output.lines() {
            if line.starts_with("worktree ") {
                if let Some(wt) = current.take() {
                    Self::push_record(wt, &mut main, &mut worktrees);
                }

                let raw = PathBuf::from(line.trim_start_matches("worktree "));
                let path = Self::canonicalize_path(&raw);
                // Primary = first porcelain record OR path matches the repo root.
                // (Never use `/.git/worktrees` — that is a gitdir path, not porcelain.)
                let is_main = !seen_worktree || Self::same_path(&path, &repo_canonical);
                seen_worktree = true;
                current = Some(Worktree {
                    id: WorktreeId(path.clone()),
                    branch: BranchName::default(),
                    path,
                    head: String::new(),
                    created_at: chrono::Utc::now(),
                    is_main,
                    locked: false,
                    lock_reason: None,
                });
            } else if let Some(ref mut wt) = current {
                if line.starts_with("branch ") {
                    wt.branch = BranchName::new(line.trim_start_matches("branch ").trim());
                } else if line.starts_with("HEAD ") {
                    // git porcelain uses uppercase HEAD (not "head ").
                    wt.head = line.trim_start_matches("HEAD ").to_string();
                } else if line.starts_with("locked") {
                    wt.locked = true;
                    let reason = line.strip_prefix("locked").unwrap_or("").trim();
                    wt.lock_reason = if reason.is_empty() {
                        None
                    } else {
                        Some(reason.to_string())
                    };
                }
            }
        }

        if let Some(wt) = current {
            Self::push_record(wt, &mut main, &mut worktrees);
        }

        let main =
            main.unwrap_or_else(|| Worktree::main(repo_canonical, String::new()));
        let total_count = worktrees.len();

        Ok(WorktreeListing {
            worktrees: worktrees.clone(),
            main,
            total_count,
        })
    }

    fn create(
        &self,
        repo_path: &Path,
        branch: &BranchName,
        worktree_path: &Path,
        start_point: Option<&str>,
    ) -> DomainResult<Worktree> {
        let path_str = worktree_path
            .to_str()
            .ok_or_else(|| WorktreeError::InvalidPath("Invalid worktree path".to_string()))?;

        let start = start_point.unwrap_or("HEAD");
        let _output = self.run_git(
            repo_path,
            &["worktree", "add", "-b", branch.as_str(), path_str, start],
        )?;

        Ok(Worktree::new(
            branch.clone(),
            worktree_path.to_path_buf(),
            start.to_string(),
        ))
    }

    fn remove(&self, worktree_path: &Path, force: bool) -> DomainResult<()> {
        let path_str = worktree_path
            .to_str()
            .ok_or_else(|| WorktreeError::InvalidPath("Invalid worktree path".to_string()))?;

        let mut args = vec!["worktree", "remove", path_str];
        if force {
            args.push("--force");
        }

        self.run_git(worktree_path, &args)?;
        Ok(())
    }

    fn lock(&self, worktree_path: &Path, reason: &str) -> DomainResult<()> {
        let path_str = worktree_path
            .to_str()
            .ok_or_else(|| WorktreeError::InvalidPath("Invalid worktree path".to_string()))?;

        self.run_git(
            worktree_path,
            &["worktree", "lock", path_str, "--reason", reason],
        )?;
        Ok(())
    }

    fn unlock(&self, worktree_path: &Path) -> DomainResult<()> {
        let path_str = worktree_path
            .to_str()
            .ok_or_else(|| WorktreeError::InvalidPath("Invalid worktree path".to_string()))?;

        self.run_git(worktree_path, &["worktree", "unlock", path_str])?;
        Ok(())
    }

    fn prune(&self, repo_path: &Path) -> DomainResult<()> {
        self.run_git(repo_path, &["worktree", "prune"])?;
        Ok(())
    }
}

/// Simple filesystem adapter for lock files
#[derive(Clone)]
pub struct SimpleFilesystemAdapter;

impl SimpleFilesystemAdapter {
    pub fn new() -> Self {
        Self
    }
}

impl Default for SimpleFilesystemAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl BranchOperations for GitWorktreeAdapter {
    fn exists(&self, repo_path: &Path, branch: &BranchName) -> DomainResult<bool> {
        // Local heads only — `origin/<name>` would Err on missing remotes and
        // break create_worktree before `git worktree add -b` can run.
        match self.run_git(
            repo_path,
            &[
                "rev-parse",
                "--verify",
                "--quiet",
                &format!("refs/heads/{}", branch.as_str()),
            ],
        ) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    fn create(
        &self,
        repo_path: &Path,
        branch: &BranchName,
        from_ref: Option<&str>,
    ) -> DomainResult<()> {
        let mut args = vec!["checkout", "-b", branch.as_str()];
        if let Some(ref_name) = from_ref {
            args.push(ref_name);
        }

        self.run_git(repo_path, &args)?;
        Ok(())
    }

    fn delete(&self, repo_path: &Path, branch: &BranchName) -> DomainResult<()> {
        self.run_git(repo_path, &["branch", "-d", branch.as_str()])?;
        Ok(())
    }

    fn current(&self, repo_path: &Path) -> DomainResult<BranchName> {
        let output = self.run_git(repo_path, &["rev-parse", "--abbrev-ref", "HEAD"])?;
        Ok(BranchName::new(output.trim()))
    }
}
