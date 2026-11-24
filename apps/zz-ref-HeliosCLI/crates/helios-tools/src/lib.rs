// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! File-edit tools for the Helios agent.
//!
//! Provides [`FileEditTool`] with three operations:
//! - [`read_file`](FileEditTool::read_file): read a file's contents
//! - [`write_file`](FileEditTool::write_file): overwrite a file with new content
//! - [`edit_file`](FileEditTool::edit_file): search-and-replace within a file

use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use thiserror::Error;
use tracing::debug;

/// Errors specific to file-edit operations.
#[derive(Debug, Error)]
pub enum FileEditError {
    /// The file does not exist.
    #[error("file not found: {path}")]
    NotFound { path: PathBuf },

    /// The search string was not found in the file (for `edit_file`).
    #[error("search string not found in {path}")]
    SearchNotFound { path: PathBuf },

    /// The search string appears multiple times and `replace_all` was not set.
    #[error("search string is ambiguous ({count} matches) in {path}; use replace_all or provide more context")]
    AmbiguousMatch { path: PathBuf, count: usize },

    /// An I/O error occurred.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// The search string must not be empty.
    #[error("search string must not be empty")]
    EmptySearch,
}

/// Result type alias for file-edit operations.
pub type FileEditResult<T> = std::result::Result<T, FileEditError>;

/// A tool that provides file read, write, and search-and-replace operations.
///
/// All paths are resolved relative to the tool's working directory.
#[derive(Debug, Clone)]
pub struct FileEditTool {
    working_dir: PathBuf,
}

impl FileEditTool {
    /// Create a new `FileEditTool` rooted at the given working directory.
    pub fn new(working_dir: impl Into<PathBuf>) -> Self {
        Self { working_dir: working_dir.into() }
    }

    /// Create a `FileEditTool` rooted at the current working directory.
    pub fn from_cwd() -> Result<Self> {
        let cwd = std::env::current_dir().context("Failed to get current directory")?;
        Ok(Self::new(cwd))
    }

    /// Resolve a path against the working directory.
    ///
    /// If `path` is already absolute it is returned as-is; otherwise it is
    /// joined with the working directory.
    fn resolve(&self, path: &Path) -> PathBuf {
        if path.is_absolute() {
            path.to_path_buf()
        } else {
            self.working_dir.join(path)
        }
    }

    /// Read the contents of a file.
    ///
    /// Returns the file content as a `String`. The file must exist and be valid
    /// UTF-8.
    pub fn read_file(&self, path: impl AsRef<Path>) -> FileEditResult<String> {
        let resolved = self.resolve(path.as_ref());
        debug!(path = %resolved.display(), "read_file");

        let content = std::fs::read_to_string(&resolved).map_err(|e| {
            if e.kind() == std::io::ErrorKind::NotFound {
                FileEditError::NotFound { path: resolved }
            } else {
                FileEditError::Io(e)
            }
        })?;
        Ok(content)
    }

    /// Write content to a file, overwriting any existing content.
    ///
    /// Parent directories are created automatically if they don't exist.
    pub fn write_file(&self, path: impl AsRef<Path>, content: &str) -> FileEditResult<()> {
        let resolved = self.resolve(path.as_ref());
        debug!(path = %resolved.display(), len = content.len(), "write_file");

        // Ensure parent directory exists
        if let Some(parent) = resolved.parent() {
            std::fs::create_dir_all(parent).map_err(FileEditError::Io)?;
        }

        std::fs::write(&resolved, content).map_err(FileEditError::Io)?;
        Ok(())
    }

    /// Search for `search` in the file and replace it with `replace`.
    ///
    /// If `replace_all` is `false` (default), the search string must appear
    /// exactly once. If it appears more than once, [`FileEditError::AmbiguousMatch`]
    /// is returned. Set `replace_all` to `true` to replace every occurrence.
    ///
    /// The file must exist and `search` must not be empty.
    pub fn edit_file(
        &self,
        path: impl AsRef<Path>,
        search: &str,
        replace: &str,
        replace_all: bool,
    ) -> FileEditResult<String> {
        if search.is_empty() {
            return Err(FileEditError::EmptySearch);
        }

        let resolved = self.resolve(path.as_ref());
        debug!(
            path = %resolved.display(),
            search_len = search.len(),
            replace_len = replace.len(),
            replace_all,
            "edit_file"
        );

        let content = std::fs::read_to_string(&resolved).map_err(|e| {
            if e.kind() == std::io::ErrorKind::NotFound {
                FileEditError::NotFound { path: resolved.clone() }
            } else {
                FileEditError::Io(e)
            }
        })?;

        let count = content.matches(search).count();
        if count == 0 {
            return Err(FileEditError::SearchNotFound { path: resolved });
        }

        if !replace_all && count > 1 {
            return Err(FileEditError::AmbiguousMatch { path: resolved, count });
        }

        let new_content = if replace_all {
            content.replace(search, replace)
        } else {
            // Exactly one occurrence — safe to replace
            content.replacen(search, replace, 1)
        };

        std::fs::write(&resolved, &new_content).map_err(FileEditError::Io)?;
        Ok(new_content)
    }

    /// Get a reference to the working directory.
    pub fn working_dir(&self) -> &Path {
        &self.working_dir
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn tool_in_tmpdir() -> (FileEditTool, TempDir) {
        let tmp = TempDir::new().unwrap();
        let tool = FileEditTool::new(tmp.path());
        (tool, tmp)
    }

    #[test]
    fn read_file_returns_content() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("hello.txt");
        std::fs::write(&path, "hello world").unwrap();

        let content = tool.read_file(&path).unwrap();
        assert_eq!(content, "hello world");
    }

    #[test]
    fn read_file_not_found_returns_error() {
        let (tool, _tmp) = tool_in_tmpdir();
        let result = tool.read_file("nonexistent.txt");
        assert!(result.is_err());
        match result.unwrap_err() {
            FileEditError::NotFound { .. } => {}
            other => panic!("expected NotFound, got: {other}"),
        }
    }

    #[test]
    fn write_file_creates_file() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("new.txt");

        tool.write_file(&path, "created").unwrap();
        let content = tool.read_file(&path).unwrap();
        assert_eq!(content, "created");
    }

    #[test]
    fn write_file_overwrites_existing() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("overwrite.txt");

        tool.write_file(&path, "first").unwrap();
        tool.write_file(&path, "second").unwrap();
        assert_eq!(tool.read_file(&path).unwrap(), "second");
    }

    #[test]
    fn write_file_creates_parent_directories() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("a").join("b").join("c.txt");

        tool.write_file(&path, "nested").unwrap();
        assert_eq!(tool.read_file(&path).unwrap(), "nested");
    }

    #[test]
    fn edit_file_single_replacement() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("edit.txt");
        tool.write_file(&path, "hello world").unwrap();

        let new = tool.edit_file(&path, "world", "rust", false).unwrap();
        assert_eq!(new, "hello rust");
        assert_eq!(tool.read_file(&path).unwrap(), "hello rust");
    }

    #[test]
    fn edit_file_replace_all() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("multi.txt");
        tool.write_file(&path, "aaa bbb aaa ccc aaa").unwrap();

        let new = tool.edit_file(&path, "aaa", "zzz", true).unwrap();
        assert_eq!(new, "zzz bbb zzz ccc zzz");
    }

    #[test]
    fn edit_file_ambiguous_returns_error() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("ambig.txt");
        tool.write_file(&path, "foo foo foo").unwrap();

        let result = tool.edit_file(&path, "foo", "bar", false);
        assert!(result.is_err());
        match result.unwrap_err() {
            FileEditError::AmbiguousMatch { count, .. } => assert_eq!(count, 3),
            other => panic!("expected AmbiguousMatch, got: {other}"),
        }
    }

    #[test]
    fn edit_file_search_not_found() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("miss.txt");
        tool.write_file(&path, "hello").unwrap();

        let result = tool.edit_file(&path, "xyz", "abc", false);
        assert!(result.is_err());
        match result.unwrap_err() {
            FileEditError::SearchNotFound { .. } => {}
            other => panic!("expected SearchNotFound, got: {other}"),
        }
    }

    #[test]
    fn edit_file_not_found() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("ghost.txt");

        let result = tool.edit_file(&path, "a", "b", false);
        assert!(result.is_err());
    }

    #[test]
    fn edit_file_empty_search_fails() {
        let (tool, tmp) = tool_in_tmpdir();
        let path = tmp.path().join("empty_search.txt");
        tool.write_file(&path, "content").unwrap();

        let result = tool.edit_file(&path, "", "replacement", false);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("empty") || err.contains("not be empty"));
    }

    #[test]
    fn resolve_absolute_path() {
        let (tool, _tmp) = tool_in_tmpdir();
        // On Windows, an absolute path needs a drive letter (e.g. C:\...)
        let abs = PathBuf::from(if cfg!(windows) {
            "C:\\some\\absolute\\path.txt"
        } else {
            "/some/absolute/path.txt"
        });
        assert_eq!(tool.resolve(&abs), abs);
    }

    #[test]
    fn resolve_relative_path() {
        let (tool, tmp) = tool_in_tmpdir();
        let rel = PathBuf::from("relative/path.txt");
        assert_eq!(tool.resolve(&rel), tmp.path().join("relative/path.txt"));
    }

    #[test]
    fn read_file_via_relative_path() {
        let (tool, tmp) = tool_in_tmpdir();
        std::fs::write(tmp.path().join("rel.txt"), "relative").unwrap();

        let content = tool.read_file("rel.txt").unwrap();
        assert_eq!(content, "relative");
    }

    #[test]
    fn working_dir_accessor() {
        let tmp = TempDir::new().unwrap();
        let tool = FileEditTool::new(tmp.path());
        assert_eq!(tool.working_dir(), tmp.path());
    }
}
