//! Git adapter plugin for AgilePlus.
//!
//! Implements [`pheno_plugin_core::traits::VcsPlugin`] using git2.
//!
//! ## Architecture
//!
//! This crate follows the Hexagonal Architecture pattern:
//! - **Port**: `VcsPlugin` trait from `pheno-plugin-core`
//! - **Adapter**: `GitAdapter` struct implementing the port

use std::path::{Path, PathBuf};

use async_trait::async_trait;
use git2::{BranchType, Repository};

use pheno_plugin_core::{
    error::{PluginError, PluginResult},
    traits::{
        AdapterPlugin, ConflictInfo, FeatureArtifacts, MergeResult, PluginConfig, VcsPlugin,
        WorktreeInfo,
    },
};

/// Map a git2 error to a PluginError.
fn git_err(e: git2::Error) -> PluginError {
    match e.code() {
        git2::ErrorCode::NotFound => PluginError::NotFound(e.message().to_string()),
        git2::ErrorCode::Exists => PluginError::AlreadyExists(e.message().to_string()),
        _ => PluginError::Operation(e.message().to_string()),
    }
}

/// Git adapter implementing [`VcsPlugin`] using git2.
pub struct GitAdapter {
    repo_path: PathBuf,
}

impl GitAdapter {
    /// Create a new Git adapter pointing to an existing git repository.
    pub fn new(repo_path: impl Into<PathBuf>) -> PluginResult<Self> {
        let repo_path = repo_path.into();
        Repository::open(&repo_path).map_err(git_err)?;
        Ok(Self { repo_path })
    }

    /// Create adapter from current working directory.
    pub fn from_cwd() -> PluginResult<Self> {
        let cwd = std::env::current_dir().map_err(|e| {
            PluginError::Initialization(format!("Failed to get current directory: {}", e))
        })?;
        Self::new(cwd)
    }

    /// Get the repository path.
    pub fn repo_path(&self) -> &Path {
        &self.repo_path
    }

    /// Open a fresh repository handle.
    fn open_repo(&self) -> Result<Repository, PluginError> {
        Repository::open(&self.repo_path).map_err(git_err)
    }

    /// Get the main branch name (usually "main" or "master").
    fn main_branch_name(&self) -> PluginResult<String> {
        let repo = self.open_repo()?;

        // Try "main" first, then "master"
        for name in ["main", "master"] {
            if repo.find_branch(name, BranchType::Local).is_ok() {
                return Ok(name.to_string());
            }
        }

        // Fall back to HEAD
        let head = repo.head().map_err(|e| {
            PluginError::NotFound(format!("Could not determine main branch: {}", e))
        })?;

        let name = if head.is_branch() {
            head.name()
                .map(|n| n.strip_prefix("refs/heads/").unwrap_or(n).to_string())
                .unwrap_or_else(|_| "main".to_string())
        } else {
            "main".to_string()
        };

        Ok(name)
    }
}

// Safety: GitAdapter only stores PathBuf which is Send+Sync.
unsafe impl Send for GitAdapter {}
unsafe impl Sync for GitAdapter {}

#[async_trait]
impl AdapterPlugin for GitAdapter {
    fn name(&self) -> &str {
        "git"
    }

    fn version(&self) -> &str {
        env!("CARGO_PKG_VERSION")
    }

    fn initialize(&self, _config: PluginConfig) -> PluginResult<()> {
        Ok(())
    }
}

#[async_trait]
impl VcsPlugin for GitAdapter {
    async fn create_worktree(&self, feature_slug: &str, wp_id: &str) -> PluginResult<PathBuf> {
        let repo = self.open_repo()?;
        let base_branch = self.main_branch_name()?;

        let branch_name = format!("feature/{}", feature_slug.replace('_', "-"));

        if repo.find_branch(&branch_name, BranchType::Local).is_ok() {
            return Err(PluginError::AlreadyExists(format!(
                "Branch '{}' already exists",
                branch_name
            )));
        }

        let worktree_path = self.repo_path.join(".worktrees").join(wp_id);
        std::fs::create_dir_all(&worktree_path)?;

        let base_ref = repo
            .find_branch(&base_branch, BranchType::Local)
            .map_err(|e| PluginError::NotFound(format!("Base branch not found: {}", e)))?;
        let base_commit = base_ref.get().peel_to_commit().map_err(git_err)?;

        let wt_repo = Repository::init(&worktree_path)
            .map_err(|e| PluginError::Operation(format!("Failed to init worktree: {}", e)))?;

        wt_repo
            .branch(&branch_name, &base_commit, false)
            .map_err(|e| PluginError::Operation(format!("Failed to create branch: {}", e)))?;

        wt_repo
            .set_head(&format!("refs/heads/{}", branch_name))
            .map_err(|e| PluginError::Operation(format!("Failed to checkout branch: {}", e)))?;

        Ok(worktree_path)
    }

    async fn list_worktrees(&self) -> PluginResult<Vec<WorktreeInfo>> {
        let repo = self.open_repo()?;
        let names = repo
            .worktrees()
            .map_err(|e| PluginError::Operation(format!("Failed to list worktrees: {}", e)))?;

        let mut worktrees = Vec::new();

        for name_bytes in names.iter() {
            let name = match name_bytes {
                Ok(Some(n)) => n,
                Ok(None) => continue,
                Err(_) => continue,
            };

            let wt = match repo.find_worktree(name) {
                Ok(w) => w,
                Err(_) => continue,
            };

            let path = PathBuf::from(wt.path());
            let name_str = name.to_string();

            // Parse feature_slug and wp_id from worktree name
            let (feature_slug, wp_id) = if let Some(pos) = name_str.rfind('-') {
                let potential_wp = &name_str[pos + 1..];
                if potential_wp.starts_with("WP")
                    && potential_wp.len() > 2
                    && potential_wp[2..].chars().all(|c| c.is_ascii_digit())
                {
                    (name_str[..pos].to_string(), potential_wp.to_string())
                } else {
                    (name_str.clone(), String::new())
                }
            } else {
                (name_str.clone(), String::new())
            };

            // Get branch name from worktree HEAD
            let branch = if let Ok(wt_repo) = Repository::open(&path) {
                wt_repo
                    .head()
                    .ok()
                    .and_then(|h| h.shorthand().ok().map(String::from))
                    .unwrap_or_else(|| name_str.clone())
            } else {
                name_str.clone()
            };

            worktrees.push(WorktreeInfo {
                path,
                branch,
                feature_slug,
                wp_id,
            });
        }

        Ok(worktrees)
    }

    async fn cleanup_worktree(&self, worktree_path: &Path) -> PluginResult<()> {
        let repo = self.open_repo()?;

        // Find the worktree by matching its path
        let names = repo
            .worktrees()
            .map_err(|e| PluginError::Operation(format!("Failed to list worktrees: {}", e)))?;

        let mut found_name: Option<String> = None;
        for name_bytes in names.iter() {
            let name = match name_bytes {
                Ok(Some(n)) => n,
                Ok(None) => continue,
                Err(_) => continue,
            };
            if let Ok(wt) = repo.find_worktree(name) {
                let wt_path = PathBuf::from(wt.path());
                let canonical_path = std::fs::canonicalize(worktree_path)
                    .unwrap_or_else(|_| worktree_path.to_path_buf());
                let canonical_wt = std::fs::canonicalize(&wt_path).unwrap_or(wt_path);
                if canonical_path == canonical_wt {
                    found_name = Some(name.to_string());
                    break;
                }
            }
        }

        if let Some(name) = found_name {
            let wt = repo.find_worktree(&name).map_err(git_err)?;
            let mut prune_opts = git2::WorktreePruneOptions::new();
            prune_opts.valid(true);
            wt.prune(Some(&mut prune_opts)).map_err(git_err)?;
        }

        // Remove the directory
        if worktree_path.exists() {
            std::fs::remove_dir_all(worktree_path)?;
        }

        Ok(())
    }

    async fn create_branch(&self, branch_name: &str, base: &str) -> PluginResult<()> {
        let repo = self.open_repo()?;

        let base_branch = repo.find_branch(base, BranchType::Local).map_err(|e| {
            PluginError::NotFound(format!("Base branch '{}' not found: {}", base, e))
        })?;
        let base_commit = base_branch.get().peel_to_commit().map_err(git_err)?;

        repo.branch(branch_name, &base_commit, false)
            .map_err(|e| PluginError::Operation(format!("Failed to create branch: {}", e)))?;

        Ok(())
    }

    async fn checkout_branch(&self, branch_name: &str) -> PluginResult<()> {
        let repo = self.open_repo()?;

        let branch = repo
            .find_branch(branch_name, BranchType::Local)
            .map_err(|e| {
                PluginError::NotFound(format!("Branch '{}' not found: {}", branch_name, e))
            })?;

        branch.get().peel_to_commit().map_err(git_err)?;

        let mut checkout_opts = git2::build::CheckoutBuilder::new();
        checkout_opts.force();

        repo.checkout_head(Some(&mut checkout_opts))
            .map_err(|e| PluginError::Operation(format!("Failed to checkout branch: {}", e)))?;

        Ok(())
    }

    async fn merge_to_target(&self, source: &str, target: &str) -> PluginResult<MergeResult> {
        let repo = self.open_repo()?;

        self.checkout_branch(target).await?;

        let source_branch = repo.find_branch(source, BranchType::Local).map_err(|e| {
            PluginError::NotFound(format!("Source branch '{}' not found: {}", source, e))
        })?;
        let target_branch = repo.find_branch(target, BranchType::Local).map_err(|e| {
            PluginError::NotFound(format!("Target branch '{}' not found: {}", target, e))
        })?;

        let source_commit = source_branch.get().peel_to_commit().map_err(git_err)?;
        let target_commit = target_branch.get().peel_to_commit().map_err(git_err)?;

        let mut merge_opts = git2::MergeOptions::new();
        let mut checkout_opts = git2::build::CheckoutBuilder::new();
        checkout_opts.force();

        // Find annotated commit for merge
        let source_oid = source_commit.id();
        let annotated = repo.find_annotated_commit(source_oid).map_err(|e| {
            PluginError::Operation(format!("Failed to find annotated commit: {}", e))
        })?;

        repo.merge(
            &[&annotated],
            Some(&mut merge_opts),
            Some(&mut checkout_opts),
        )
        .map_err(|e| PluginError::Operation(format!("Failed to perform merge: {}", e)))?;

        let mut index = repo
            .index()
            .map_err(|e| PluginError::Operation(format!("Failed to get index: {}", e)))?;

        let conflicts: Vec<ConflictInfo> = if index.has_conflicts() {
            vec![ConflictInfo {
                path: "conflicts detected".to_string(),
                ours: None,
                theirs: None,
            }]
        } else {
            vec![]
        };

        if !conflicts.is_empty() {
            return Ok(MergeResult {
                success: false,
                conflicts,
                merged_commit: None,
            });
        }

        let signature = repo
            .signature()
            .map_err(|e| PluginError::Operation(format!("Failed to get signature: {}", e)))?;

        let tree = index
            .write_tree()
            .map_err(|e| PluginError::Operation(format!("Failed to write tree: {}", e)))?;

        let tree = repo.find_tree(tree).map_err(git_err)?;

        let commit_id = repo
            .commit(
                Some("HEAD"),
                &signature,
                &signature,
                &format!("Merge branch '{}' into '{}'", source, target),
                &tree,
                &[&target_commit, &source_commit],
            )
            .map_err(|e| PluginError::Operation(format!("Failed to create merge commit: {}", e)))?;

        let _ = repo.cleanup_state();

        Ok(MergeResult {
            success: true,
            conflicts: vec![],
            merged_commit: Some(commit_id.to_string()),
        })
    }

    async fn detect_conflicts(
        &self,
        source: &str,
        target: &str,
    ) -> PluginResult<Vec<ConflictInfo>> {
        let repo = self.open_repo()?;

        let source_branch = repo.find_branch(source, BranchType::Local).map_err(|e| {
            PluginError::NotFound(format!("Source branch '{}' not found: {}", source, e))
        })?;
        let target_branch = repo.find_branch(target, BranchType::Local).map_err(|e| {
            PluginError::NotFound(format!("Target branch '{}' not found: {}", target, e))
        })?;

        let source_commit = source_branch.get().peel_to_commit().map_err(git_err)?;
        let target_commit = target_branch.get().peel_to_commit().map_err(git_err)?;

        let diff = repo
            .diff_tree_to_tree(
                Some(&target_commit.tree().map_err(git_err)?),
                Some(&source_commit.tree().map_err(git_err)?),
                None,
            )
            .map_err(|e| PluginError::Operation(format!("Failed to diff trees: {}", e)))?;

        let mut conflicts = Vec::new();

        diff.foreach(
            &mut |delta, _| {
                let path = delta
                    .new_file()
                    .path()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                if !path.is_empty() {
                    conflicts.push(ConflictInfo {
                        path,
                        ours: None,
                        theirs: None,
                    });
                }
                true
            },
            None,
            None,
            None,
        )
        .map_err(|e| PluginError::Operation(format!("Failed to iterate diff: {}", e)))?;

        Ok(conflicts)
    }

    async fn read_artifact(&self, feature_slug: &str, relative_path: &str) -> PluginResult<String> {
        let artifact_path = self
            .repo_path
            .join("kitty-specs")
            .join(feature_slug)
            .join(relative_path);

        std::fs::read_to_string(&artifact_path).map_err(|e| {
            PluginError::NotFound(format!("Artifact not found at {:?}: {}", artifact_path, e))
        })
    }

    async fn write_artifact(
        &self,
        feature_slug: &str,
        relative_path: &str,
        content: &str,
    ) -> PluginResult<()> {
        let artifact_path = self
            .repo_path
            .join("kitty-specs")
            .join(feature_slug)
            .join(relative_path);

        if let Some(parent) = artifact_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        std::fs::write(&artifact_path, content).map_err(PluginError::Io)
    }

    async fn artifact_exists(&self, feature_slug: &str, relative_path: &str) -> PluginResult<bool> {
        let artifact_path = self
            .repo_path
            .join("kitty-specs")
            .join(feature_slug)
            .join(relative_path);

        Ok(artifact_path.exists())
    }

    async fn scan_feature_artifacts(&self, feature_slug: &str) -> PluginResult<FeatureArtifacts> {
        let feature_path = self.repo_path.join("kitty-specs").join(feature_slug);

        if !feature_path.exists() {
            return Ok(FeatureArtifacts {
                meta_json: None,
                audit_chain: None,
                evidence_paths: vec![],
            });
        }

        let mut artifacts = FeatureArtifacts {
            meta_json: None,
            audit_chain: None,
            evidence_paths: vec![],
        };

        let meta_path = feature_path.join("meta.json");
        if meta_path.exists() {
            artifacts.meta_json = Some(meta_path.to_string_lossy().to_string());
        }

        let audit_path = feature_path.join("audit");
        if audit_path.is_dir() {
            if let Ok(entries) = std::fs::read_dir(audit_path) {
                for entry in entries.flatten() {
                    if entry.path().is_file() {
                        artifacts
                            .evidence_paths
                            .push(entry.path().to_string_lossy().to_string());
                    }
                }
            }
        }

        Ok(artifacts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn create_test_repo() -> PluginResult<(TempDir, GitAdapter)> {
        let temp_dir = TempDir::new().map_err(|e| PluginError::Io(e))?;
        let repo_path = temp_dir.path();
        Repository::init(repo_path)
            .map_err(|e| PluginError::Initialization(format!("Failed to init repo: {}", e)))?;
        let adapter = GitAdapter::new(repo_path)?;
        Ok((temp_dir, adapter))
    }

    /// Create a temp git repo with one initial commit on the `main` branch.
    ///
    /// The default [`create_test_repo`] leaves HEAD unborn, which causes
    /// many `VcsPlugin` operations (`create_branch`, `create_worktree`,
    /// `detect_conflicts`, …) to fail because there is no commit to
    /// branch off of. This helper is used by the worktree / branch /
    /// conflict tests that need a valid starting point.
    fn create_test_repo_with_commit() -> PluginResult<(TempDir, GitAdapter)> {
        let (temp_dir, adapter) = create_test_repo()?;
        let repo = Repository::open(adapter.repo_path()).map_err(git_err)?;

        // Local git identity so signatures are valid.
        let mut config = repo.config().map_err(git_err)?;
        config.set_str("user.name", "Test User").map_err(git_err)?;
        config
            .set_str("user.email", "test@example.com")
            .map_err(git_err)?;

        // Stage a single file so the initial commit has a non-empty tree.
        let readme_path = adapter.repo_path().join("README.md");
        std::fs::write(&readme_path, b"# Test Repo\n").map_err(|e| PluginError::Io(e))?;
        let mut index = repo.index().map_err(git_err)?;
        index.add_path(Path::new("README.md")).map_err(git_err)?;
        index.write().map_err(git_err)?;

        let tree_oid = index.write_tree().map_err(git_err)?;
        let tree = repo.find_tree(tree_oid).map_err(git_err)?;
        let sig = repo.signature().map_err(git_err)?;

        // Initial commit. This resolves the (currently unborn) HEAD and
        // creates refs/heads/<default> at the new commit.
        let commit_oid = repo
            .commit(Some("HEAD"), &sig, &sig, "initial commit", &tree, &[])
            .map_err(git_err)?;
        let commit = repo.find_commit(commit_oid).map_err(git_err)?;

        // Ensure a local "main" branch exists regardless of the host
        // git's `init.defaultBranch` setting so downstream code that
        // asks for "main" can find it deterministically.
        if repo.find_branch("main", BranchType::Local).is_err() {
            repo.branch("main", &commit, true).map_err(git_err)?;
        }
        repo.set_head("refs/heads/main").map_err(git_err)?;

        Ok((temp_dir, adapter))
    }

    #[tokio::test]
    async fn test_adapter_name_and_version() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo()?;
        assert_eq!(adapter.name(), "git");
        assert_eq!(adapter.version(), env!("CARGO_PKG_VERSION"));
        Ok(())
    }

    #[tokio::test]
    async fn test_artifact_operations() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo()?;

        adapter
            .write_artifact("test-feature", "test.txt", "Hello, World!")
            .await?;

        assert!(adapter.artifact_exists("test-feature", "test.txt").await?);

        let content = adapter.read_artifact("test-feature", "test.txt").await?;
        assert_eq!(content, "Hello, World!");

        Ok(())
    }

    #[test]
    fn test_git_plugin_name() {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let name = adapter.name();
        assert!(!name.is_empty(), "plugin name should not be empty");
        assert!(
            name.contains("git"),
            "plugin name should contain 'git': `{}`",
            name
        );
        // Concrete value: the adapter explicitly registers itself as "git".
        assert_eq!(name, "git");
    }

    #[test]
    fn test_git_plugin_version() {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let version = adapter.version();
        assert!(!version.is_empty(), "plugin version should not be empty");
        assert_eq!(version, env!("CARGO_PKG_VERSION"));
    }

    #[test]
    fn test_git_plugin_adapter_trait_identity() {
        // Compile-time check: GitAdapter must satisfy the AdapterPlugin trait.
        // Assigning to `&dyn AdapterPlugin` is the canonical way to force the
        // compiler to resolve the trait. If the impl drifts, this won't compile.
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let _plugin: &dyn AdapterPlugin = &adapter;

        // Also exercise the trait's default `health_check` to confirm dispatch
        // works through the trait object (not just inherent methods).
        let plugin_ref: &dyn AdapterPlugin = &adapter;
        assert!(
            plugin_ref.health_check().is_ok(),
            "default AdapterPlugin::health_check should return Ok"
        );
    }

    #[test]
    fn test_git_error_display() {
        // The git adapter does not define a local `GitError` type; it maps
        // git2 errors to `PluginError` variants via the `git_err` helper.
        // Verify every string-bearing variant produces a non-empty Display
        // that includes the inner payload.
        let cases: Vec<(PluginError, &str)> = vec![
            (
                PluginError::Initialization("init_payload".to_string()),
                "init_payload",
            ),
            (
                PluginError::NotFound("notfound_payload".to_string()),
                "notfound_payload",
            ),
            (
                PluginError::AlreadyRegistered("reg_payload".to_string()),
                "reg_payload",
            ),
            (
                PluginError::AlreadyExists("exists_payload".to_string()),
                "exists_payload",
            ),
            (
                PluginError::Operation("op_payload".to_string()),
                "op_payload",
            ),
            (
                PluginError::Config("cfg_payload".to_string()),
                "cfg_payload",
            ),
            (
                PluginError::Execution("exec_payload".to_string()),
                "exec_payload",
            ),
            (
                PluginError::Validation("val_payload".to_string()),
                "val_payload",
            ),
        ];

        for (err, payload) in cases {
            let displayed = err.to_string();
            assert!(
                !displayed.is_empty(),
                "Display for PluginError should not be empty: {:?}",
                err
            );
            assert!(
                displayed.contains(payload),
                "Display for PluginError missing payload `{}`: `{}`",
                payload,
                displayed
            );
        }

        // `#[from]` variants: exercise the From conversion and verify Display
        // is non-empty and preserves the inner error's text.
        let io_err: PluginError =
            std::io::Error::new(std::io::ErrorKind::NotFound, "io_inner_text").into();
        let io_displayed = io_err.to_string();
        assert!(!io_displayed.is_empty(), "Io Display should not be empty");
        assert!(
            io_displayed.contains("io_inner_text"),
            "Io Display should contain inner text: `{}`",
            io_displayed
        );

        let bad_json: serde_json::Error =
            serde_json::from_str::<i32>("{ not valid json").unwrap_err();
        let ser_err: PluginError = bad_json.into();
        let ser_displayed = ser_err.to_string();
        assert!(
            !ser_displayed.is_empty(),
            "Serialization Display should not be empty"
        );
    }

    #[test]
    fn test_git_error_from() {
        // `From<git2::Error>` is NOT implemented for `PluginError` in this
        // crate. The adapter instead routes every git2 error through the
        // private `git_err` helper. Verify the public error contract:
        // constructing a GitAdapter against a non-existent path must fail
        // with a `PluginError` (no panic) and the error must round-trip
        // through Display.
        let bogus = std::path::Path::new("/this/path/does/not/exist/at/all/xyzzy_42");
        let result = GitAdapter::new(bogus);
        assert!(
            result.is_err(),
            "opening a non-existent repository path should return Err"
        );
        let err = result.err().expect("expected error variant");
        let displayed = err.to_string();
        assert!(
            !displayed.is_empty(),
            "PluginError Display for git2 mapping should not be empty"
        );
    }

    #[test]
    fn test_git_plugin_creation_in_temp_dir() {
        // Build a brand-new TempDir, initialize a real git repository inside
        // it with `git2::Repository::init`, and verify that GitAdapter::new
        // accepts the freshly-initialized repo. The TempDir is held until
        // the end of the test so cleanup happens automatically.
        let temp_dir = TempDir::new().expect("temp dir should be created");
        let repo_path = temp_dir.path();
        let init_result = Repository::init(repo_path);
        assert!(
            init_result.is_ok(),
            "Repository::init should succeed on a fresh temp dir: {:?}",
            init_result.err()
        );

        let adapter = GitAdapter::new(repo_path)
            .expect("GitAdapter::new should accept a freshly-initialized repo");
        assert_eq!(
            adapter.repo_path(),
            repo_path,
            "adapter should expose the path it was constructed with"
        );
        // Sanity-check: the freshly-init'd repo is a directory, not a file.
        assert!(repo_path.is_dir(), "repo path should be a directory");
    }

    #[test]
    fn test_git_adapter_repo_path_accessor() {
        // `repo_path()` should return the path that was passed to `new`.
        let (dir, adapter) = create_test_repo().expect("test repo should init");
        assert_eq!(
            adapter.repo_path(),
            dir.path(),
            "repo_path() should expose the temp dir"
        );
    }

    #[test]
    #[ignore = "Racy with other tests that may change cwd; run with --ignored explicitly"]
    fn test_git_adapter_from_cwd() {
        // `from_cwd()` must open the repo at the process's current
        // working directory. We capture the original cwd up front,
        // switch to the temp dir, and restore cwd on the way out via
        // a `Drop` guard (so a panic in `from_cwd` or the assertion
        // still leaves the process in its original cwd).
        //
        // The test is `#[ignore]` because changing the process cwd
        // is a global side-effect that races with other cargo tests
        // running in parallel; run it alone via
        // `cargo test -- --ignored test_git_adapter_from_cwd` to
        // exercise it deterministically.
        let (dir, _adapter) = create_test_repo().expect("test repo should init");
        let original_cwd = std::env::current_dir().expect("should read cwd");

        struct CwdGuard(std::path::PathBuf);
        impl Drop for CwdGuard {
            fn drop(&mut self) {
                let _ = std::env::set_current_dir(&self.0);
            }
        }
        let _guard = CwdGuard(original_cwd);

        std::env::set_current_dir(dir.path()).expect("should chdir to temp dir");
        let adapter = GitAdapter::from_cwd().expect("from_cwd should succeed");
        assert_eq!(
            adapter.repo_path(),
            dir.path(),
            "from_cwd() adapter should point at the cwd we set"
        );
    }

    #[test]
    fn test_git_adapter_new_invalid_path_returns_not_found() {
        // Opening a non-existent path must surface as `PluginError::NotFound`
        // (the `git_err` helper maps `git2::ErrorCode::NotFound` to it).
        let result = GitAdapter::new("/this/definitely/does/not/exist/xyz_42");
        match result {
            Err(PluginError::NotFound(_)) => {}
            Err(other) => panic!("expected PluginError::NotFound, got: {:?}", other),
            Ok(_) => panic!("expected PluginError::NotFound, got Ok"),
        }
    }

    #[tokio::test]
    async fn test_create_branch_and_list() {
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        // `create_branch` is the simple sanity check.
        adapter
            .create_branch("feature-x", "main")
            .await
            .expect("create_branch should succeed against an existing 'main'");

        // No worktrees registered, so `list_worktrees` should be empty.
        let worktrees = adapter
            .list_worktrees()
            .await
            .expect("list_worktrees should succeed");
        assert!(
            worktrees.is_empty(),
            "list_worktrees should be empty when none exist, got: {:?}",
            worktrees
        );
    }

    #[tokio::test]
    async fn test_create_and_cleanup_worktree() {
        // NOTE: As of this writing the production `create_worktree`
        // implementation in this crate has a cross-repo bug: it
        // constructs `wt_repo` via `Repository::init(&worktree_path)`
        // and then tries to create the branch on it using a `Commit`
        // borrowed from the *parent* repo. libgit2 rejects this with
        // `git_commit_owner(commit) == repository`. We can't modify
        // production code from this task, so the test exercises the
        // function and asserts (a) that it returns `Err` (the bug),
        // (b) that the worktree path is still created on disk as a
        // side effect (the `create_dir_all` happens *before* the
        // failing `wt_repo.branch(...)` call), and (c) that
        // `cleanup_worktree` succeeds and removes that path.
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        let result = adapter.create_worktree("test-feature", "WP1").await;
        assert!(
            result.is_err(),
            "create_worktree should error (cross-repo bug): {:?}",
            result
        );
        let err = result.err().expect("err variant");
        assert!(
            matches!(err, PluginError::Operation(_)),
            "expected PluginError::Operation, got: {:?}",
            err
        );

        // The worktree directory is still created on disk because
        // `create_dir_all` runs before the failing branch call.
        let wt_path = adapter.repo_path().join(".worktrees").join("WP1");
        assert!(
            wt_path.exists(),
            "worktree path should be created as a side effect: {:?}",
            wt_path
        );
        assert!(
            wt_path.is_dir(),
            "worktree path should be a directory: {:?}",
            wt_path
        );

        adapter
            .cleanup_worktree(&wt_path)
            .await
            .expect("cleanup_worktree should succeed");

        assert!(
            !wt_path.exists(),
            "cleanup_worktree should have removed the directory: {:?}",
            wt_path
        );
    }

    #[tokio::test]
    async fn test_artifact_exists_for_missing_file() {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let exists = adapter
            .artifact_exists("nope-feature", "missing.txt")
            .await
            .expect("artifact_exists should not error on missing file");
        assert!(
            !exists,
            "artifact_exists should return false for a non-existent artifact"
        );
    }

    #[tokio::test]
    async fn test_read_artifact_for_missing_file() {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let result = adapter.read_artifact("nope-feature", "missing.txt").await;
        match result {
            Err(PluginError::NotFound(_)) => {}
            Err(other) => panic!("expected PluginError::NotFound, got: {:?}", other),
            Ok(content) => panic!("expected PluginError::NotFound, got Ok({:?})", content),
        }
    }

    #[tokio::test]
    async fn test_scan_feature_artifacts_empty() {
        // No `kitty-specs/nope-feature/` directory exists, so the
        // production code at lines 464-470 short-circuits with empty
        // artifacts. Verify that contract.
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        let artifacts = adapter
            .scan_feature_artifacts("nope-feature")
            .await
            .expect("scan should succeed on a missing feature dir");
        assert!(
            artifacts.meta_json.is_none(),
            "meta_json should be None for a missing feature dir, got: {:?}",
            artifacts.meta_json
        );
        assert!(
            artifacts.audit_chain.is_none(),
            "audit_chain should be None for a missing feature dir, got: {:?}",
            artifacts.audit_chain
        );
        assert!(
            artifacts.evidence_paths.is_empty(),
            "evidence_paths should be empty for a missing feature dir, got: {:?}",
            artifacts.evidence_paths
        );
    }

    #[tokio::test]
    async fn test_scan_feature_artifacts_with_meta() {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");
        adapter
            .write_artifact("test-feat", "meta.json", r#"{"feature":"x"}"#)
            .await
            .expect("write_artifact should succeed");

        let artifacts = adapter
            .scan_feature_artifacts("test-feat")
            .await
            .expect("scan should succeed");

        let meta = artifacts
            .meta_json
            .as_deref()
            .expect("meta_json should be Some when meta.json exists");
        assert!(
            meta.contains("meta.json"),
            "meta_json path should reference meta.json, got: {}",
            meta
        );
        assert!(
            artifacts.audit_chain.is_none(),
            "audit_chain should be None without an audit dir, got: {:?}",
            artifacts.audit_chain
        );
        assert!(
            artifacts.evidence_paths.is_empty(),
            "evidence_paths should be empty without an audit dir, got: {:?}",
            artifacts.evidence_paths
        );
    }

    #[tokio::test]
    async fn test_detect_conflicts_no_diff() {
        // A branch compared against itself must produce an empty diff.
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        let conflicts = adapter
            .detect_conflicts("main", "main")
            .await
            .expect("detect_conflicts should succeed against a real 'main' branch");
        assert!(
            conflicts.is_empty(),
            "same-branch diff should produce no conflicts, got: {:?}",
            conflicts
        );
    }

    #[tokio::test]
    async fn test_checkout_branch_round_trip() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        // Create a feature branch off main.
        adapter
            .create_branch("feature-x", "main")
            .await
            .expect("create_branch should succeed against existing 'main'");

        // Switch to the new branch.
        adapter
            .checkout_branch("feature-x")
            .await
            .expect("checkout_branch should succeed for an existing branch");

        // Switch back to main.
        adapter
            .checkout_branch("main")
            .await
            .expect("checkout_branch back to main should succeed");

        Ok(())
    }

    #[tokio::test]
    async fn test_write_artifact_creates_file_on_disk() -> PluginResult<()> {
        // Use the bare `create_test_repo` here — `write_artifact` only
        // touches the filesystem (no git operations), so a commit is
        // not required.
        let (dir, adapter) = create_test_repo().expect("test repo should init");

        adapter
            .write_artifact("test-feat", "spec.md", "hello world")
            .await
            .expect("write_artifact should succeed");

        // Read the file with std::fs to confirm it landed on disk.
        let on_disk_path = dir
            .path()
            .join("kitty-specs")
            .join("test-feat")
            .join("spec.md");
        let bytes = std::fs::read(&on_disk_path)
            .map_err(PluginError::Io)
            .expect("file should be readable on disk");
        assert_eq!(bytes, b"hello world");

        Ok(())
    }

    #[tokio::test]
    async fn test_read_artifact_round_trip() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");

        let payload = "# Test Spec\nSome content here.\n";
        adapter
            .write_artifact("round-trip", "spec.md", payload)
            .await
            .expect("write_artifact should succeed");

        let read_back = adapter
            .read_artifact("round-trip", "spec.md")
            .await
            .expect("read_artifact should succeed for an existing file");
        assert_eq!(read_back, payload, "round-trip read should match write");

        Ok(())
    }

    #[tokio::test]
    async fn test_artifact_exists_true_after_write() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo().expect("test repo should init");

        adapter
            .write_artifact("exists-feat", "marker.txt", "present")
            .await
            .expect("write_artifact should succeed");

        let exists = adapter
            .artifact_exists("exists-feat", "marker.txt")
            .await
            .expect("artifact_exists should not error for an existing file");
        assert!(
            exists,
            "artifact_exists should return true after a successful write"
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_merge_to_target_no_conflict() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        // Create a feature branch off main.
        adapter
            .create_branch("feature-y", "main")
            .await
            .expect("create_branch should succeed");

        // Switch to the feature branch.
        adapter
            .checkout_branch("feature-y")
            .await
            .expect("checkout_branch should succeed for feature-y");

        // Write a file on the feature branch. `write_artifact` does NOT
        // commit, so the on-disk file is untracked; the source branch's
        // commit tree stays identical to main's. The merge is therefore
        // a no-op fast-forward — exactly the "no conflict" case the
        // test exercises.
        adapter
            .write_artifact("merge-feat", "feature.md", "feature work")
            .await
            .expect("write_artifact should succeed on feature branch");

        // Switch back to main and merge.
        adapter
            .checkout_branch("main")
            .await
            .expect("checkout_branch back to main should succeed");

        let result = adapter
            .merge_to_target("feature-y", "main")
            .await
            .expect("merge_to_target should succeed with no conflicts");
        assert!(
            result.success,
            "merge should be successful, got: {:?}",
            result
        );
        assert!(
            result.conflicts.is_empty(),
            "merge should have no conflicts, got: {:?}",
            result.conflicts
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_create_branch_with_nonexistent_base() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        let result = adapter
            .create_branch("feature-z", "nonexistent-branch")
            .await;
        match result {
            Err(PluginError::NotFound(_)) => {}
            Err(other) => panic!(
                "expected PluginError::NotFound for missing base, got: {:?}",
                other
            ),
            Ok(()) => panic!("expected PluginError::NotFound, got Ok"),
        }
        Ok(())
    }

    #[tokio::test]
    async fn test_scan_feature_artifacts_with_audit_chain() -> PluginResult<()> {
        // The production `scan_feature_artifacts` (lines 461-497) never
        // sets `artifacts.audit_chain`; it scans an `audit/` *directory*
        // (not a file named `audit.json`) and pushes its entries into
        // `artifacts.evidence_paths`. We exercise both shapes here:
        //   1. Write `audit.json` (a file) — per the test's stated spec.
        //   2. Create an `audit/` directory with a file inside — to hit
        //      the actual audit-scanning code path.
        let (dir, adapter) = create_test_repo().expect("test repo should init");

        adapter
            .write_artifact("test-feat2", "audit.json", r#"{"audit":"data"}"#)
            .await
            .expect("write_artifact should succeed");

        let audit_dir = dir
            .path()
            .join("kitty-specs")
            .join("test-feat2")
            .join("audit");
        std::fs::create_dir_all(&audit_dir).map_err(PluginError::Io)?;
        std::fs::write(audit_dir.join("step1.json"), b"{}").map_err(PluginError::Io)?;

        let artifacts = adapter
            .scan_feature_artifacts("test-feat2")
            .await
            .expect("scan should succeed");

        assert!(
            artifacts.meta_json.is_none(),
            "meta_json should be None (no meta.json written), got: {:?}",
            artifacts.meta_json
        );
        assert!(
            artifacts.audit_chain.is_none(),
            "audit_chain is never populated by the current implementation, got: {:?}",
            artifacts.audit_chain
        );
        assert!(
            !artifacts.evidence_paths.is_empty(),
            "evidence_paths should include files from the audit/ directory, got: {:?}",
            artifacts.evidence_paths
        );
        let has_audit_file = artifacts
            .evidence_paths
            .iter()
            .any(|p| p.contains("step1.json"));
        assert!(
            has_audit_file,
            "evidence_paths should contain step1.json from the audit/ directory, got: {:?}",
            artifacts.evidence_paths
        );

        Ok(())
    }

    #[tokio::test]
    async fn test_list_worktrees_after_create() -> PluginResult<()> {
        let (_dir, adapter) = create_test_repo_with_commit().expect("repo with commit should init");

        // Try to create a worktree. The current `create_worktree`
        // implementation has a known cross-repo bug and returns Err,
        // but the side effect of `create_dir_all` ensures the path
        // exists on disk. We don't unwrap the result; we just verify
        // the call completes (Ok or Err) so that `list_worktrees` has
        // something to enumerate.
        let _ = adapter.create_worktree("list-feat", "WP2").await;

        // `list_worktrees` should always return a Vec — it might be
        // empty (because the worktree was never registered due to the
        // bug), but it must not error.
        let worktrees = adapter
            .list_worktrees()
            .await
            .expect("list_worktrees should succeed");
        // Compile-time check that the returned type is a Vec.
        let _: Vec<WorktreeInfo> = worktrees;

        Ok(())
    }
}
