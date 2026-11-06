//! Integration tests for worktree-manager (`wtm`) against real tempfile git repos.
//!
//! Covers create / list / lock / remove and optional `start_point` wiring.

use std::path::{Path, PathBuf};
use std::process::Command;

use tempfile::TempDir;
use worktree_manager::{BranchName, GitWorktreeAdapter, WorktreeService};

fn run_git(repo: &Path, args: &[&str]) -> String {
    let output = Command::new("git")
        .args(["-C", repo.to_str().unwrap()])
        .args(args)
        .output()
        .expect("git must be invokable");
    assert!(
        output.status.success(),
        "git {:?} failed: {}",
        args,
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8_lossy(&output.stdout).to_string()
}

/// Bare init + one commit on `main` (no remote). Mirrors airlock-v2 git_ops tests.
fn init_git_repo(dir: &Path) -> PathBuf {
    std::fs::create_dir_all(dir).unwrap();
    run_git(dir, &["init", "-q", "-b", "main"]);
    run_git(dir, &["config", "user.email", "test@example.com"]);
    run_git(dir, &["config", "user.name", "Test"]);
    // Avoid "dubious ownership" noise in CI sandboxes.
    run_git(dir, &["config", "commit.gpgsign", "false"]);
    std::fs::write(dir.join("README.md"), "hello\n").unwrap();
    run_git(dir, &["add", "README.md"]);
    run_git(dir, &["commit", "-q", "-m", "init"]);
    // Git on macOS may rewrite /var → /private/var; canonicalize for comparisons.
    dir.canonicalize().unwrap_or_else(|_| dir.to_path_buf())
}

fn same_path(a: &Path, b: &Path) -> bool {
    match (a.canonicalize(), b.canonicalize()) {
        (Ok(ca), Ok(cb)) => ca == cb,
        _ => a == b,
    }
}

fn service() -> WorktreeService<GitWorktreeAdapter, GitWorktreeAdapter> {
    let adapter = GitWorktreeAdapter::new();
    WorktreeService::new(adapter.clone(), adapter)
}

#[test]
fn create_list_lock_remove_lifecycle() {
    let tmp = TempDir::new().unwrap();
    let repo_dir = tmp.path().join("repo");
    let repo = init_git_repo(&repo_dir);
    let wt_path = tmp.path().join("wt-feature");
    let svc = service();

    let created = svc.create_worktree(
        &repo,
        BranchName::new("feature/lifecycle"),
        &wt_path,
        None,
    );
    assert!(
        created.success,
        "create failed: {:?}",
        created.error
    );
    assert!(wt_path.join("README.md").exists());

    let listing = svc.list_worktrees(&repo).expect("list");
    assert!(
        listing.main.is_main,
        "primary worktree must be classified is_main=true"
    );
    assert!(
        same_path(&listing.main.path, &repo),
        "main path should match repo after canonicalize: {:?} vs {:?}",
        listing.main.path,
        repo
    );
    assert!(
        listing
            .worktrees
            .iter()
            .any(|w| same_path(&w.path, &wt_path) && !w.is_main),
        "linked worktree missing from list (or misclassified as main): {:?}",
        listing.worktrees
    );

    svc.lock_worktree(&wt_path, "integration-test")
        .expect("lock");
    let listing = svc.list_worktrees(&repo).expect("list after lock");
    let locked = listing
        .worktrees
        .iter()
        .find(|w| same_path(&w.path, &wt_path))
        .expect("worktree present after lock");
    assert!(locked.locked, "expected locked=true after lock");

    svc.unlock_worktree(&wt_path).expect("unlock");
    svc.remove_worktree(&wt_path, true).expect("remove");
    assert!(!wt_path.exists(), "worktree path should be gone after remove");

    let listing = svc.list_worktrees(&repo).expect("list after remove");
    assert!(
        !listing.worktrees.iter().any(|w| same_path(&w.path, &wt_path)),
        "removed worktree still listed"
    );
}

#[test]
fn create_with_start_point_uses_explicit_commit() {
    let tmp = TempDir::new().unwrap();
    let repo_dir = tmp.path().join("repo");
    let repo = init_git_repo(&repo_dir);

    // Second commit so start_point can target the first.
    std::fs::write(repo.join("second.txt"), "two\n").unwrap();
    run_git(&repo, &["add", "second.txt"]);
    run_git(&repo, &["commit", "-q", "-m", "second"]);

    let first = run_git(&repo, &["rev-list", "--max-parents=0", "HEAD"])
        .trim()
        .to_string();
    assert!(!first.is_empty());

    let wt_path = tmp.path().join("wt-from-root");
    let svc = service();
    let created = svc.create_worktree(
        &repo,
        BranchName::new("feature/from-root"),
        &wt_path,
        Some(&first),
    );
    assert!(
        created.success,
        "create with start_point failed: {:?}",
        created.error
    );

    // Worktree based on root commit must not have second.txt.
    assert!(
        !wt_path.join("second.txt").exists(),
        "start_point should pin worktree to first commit"
    );
    assert!(wt_path.join("README.md").exists());

    let head = run_git(&wt_path, &["rev-parse", "HEAD"]).trim().to_string();
    assert_eq!(head, first);

    svc.remove_worktree(&wt_path, true).expect("cleanup remove");
}

#[test]
fn create_rejects_duplicate_branch() {
    let tmp = TempDir::new().unwrap();
    let repo_dir = tmp.path().join("repo");
    let repo = init_git_repo(&repo_dir);
    let svc = service();

    let first_path = tmp.path().join("wt-a");
    let ok = svc.create_worktree(
        &repo,
        BranchName::new("feature/dup"),
        &first_path,
        None,
    );
    assert!(ok.success, "{:?}", ok.error);

    let second_path = tmp.path().join("wt-b");
    let dup = svc.create_worktree(
        &repo,
        BranchName::new("feature/dup"),
        &second_path,
        None,
    );
    assert!(!dup.success);
    assert!(
        dup.error
            .as_deref()
            .unwrap_or("")
            .contains("already exists"),
        "unexpected error: {:?}",
        dup.error
    );

    svc.remove_worktree(&first_path, true).expect("cleanup");
}
