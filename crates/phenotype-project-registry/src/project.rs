//! Project Discovery Module
//!
//! Discovers projects in the file system and extracts metadata.

use std::path::{Path, PathBuf};

/// Project type based on language
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectType {
    Rust,
    TypeScript,
    Python,
    Go,
    Unknown,
}

impl ProjectType {
    pub fn from_path(path: &Path) -> Self {
        if path.join("Cargo.toml").exists() {
            return ProjectType::Rust;
        }
        if path.join("package.json").exists() {
            return ProjectType::TypeScript;
        }
        if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
            return ProjectType::Python;
        }
        if path.join("go.mod").exists() {
            return ProjectType::Go;
        }
        ProjectType::Unknown
    }
}

/// Discovered project metadata
#[derive(Debug, Clone)]
pub struct Project {
    pub name: String,
    pub path: PathBuf,
    pub project_type: ProjectType,
}

/// Project registry - collection of discovered projects
#[derive(Debug, Clone, Default)]
pub struct ProjectRegistry {
    pub projects: Vec<Project>,
}

impl ProjectRegistry {
    pub fn discover(root: &Path) -> Self {
        let mut registry = Self::default();
        
        if let Ok(entries) = std::fs::read_dir(root) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let project_type = ProjectType::from_path(&path);
                    if project_type != ProjectType::Unknown {
                        let name = path.file_name()
                            .map(|n| n.to_string_lossy().to_string())
                            .unwrap_or_default();
                        registry.projects.push(Project {
                            name,
                            path,
                            project_type,
                        });
                    }
                }
            }
        }
        
        registry
    }
}
