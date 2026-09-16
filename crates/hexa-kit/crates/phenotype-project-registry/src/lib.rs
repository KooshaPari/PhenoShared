//! Project registry for unified health dashboard.
//!
//! Discovers and manages projects across the repos shelf for health tracking.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use phenotype_health::LanguageStack;
use serde::{Deserialize, Serialize};

/// Metadata about a discovered project
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectMetadata {
    pub name: String,
    pub path: PathBuf,
    pub language: LanguageStack,
    pub github_repo: Option<String>,
    pub owner: String,
    pub has_claude_md: bool,
    pub has_readme: bool,
    pub has_contributing: bool,
    pub has_license: bool,
    pub has_changelog: bool,
    pub has_codecov: bool,
    pub has_deny_toml: bool,
    pub has_security_workflow: bool,
    pub workflow_count: usize,
}

impl ProjectMetadata {
    /// Calculate documentation completeness score (0-100)
    pub fn documentation_score(&self) -> f32 {
        let required = [
            self.has_claude_md,
            self.has_readme,
            self.has_contributing,
            self.has_license,
            self.has_changelog,
        ];
        let present = required.iter().filter(|&&x| x).count();
        (present as f32 / required.len() as f32) * 100.0
    }

    /// Calculate compliance score based on required files (0-100)
    pub fn compliance_score(&self) -> f32 {
        let required = [
            self.has_codecov,
            self.has_deny_toml,
            self.has_security_workflow,
        ];
        let present = required.iter().filter(|&&x| x).count();
        (present as f32 / required.len() as f32) * 100.0
    }
}

/// Registry of all projects in the repos shelf
#[derive(Debug, Default)]
pub struct ProjectRegistry {
    projects: HashMap<String, ProjectMetadata>,
}

impl ProjectRegistry {
    /// Create a new empty registry
    pub fn new() -> Self {
        Self {
            projects: HashMap::new(),
        }
    }

    /// Discover all projects in the given root directory
    pub async fn discover_projects(&self, root: &Path) -> anyhow::Result<Vec<ProjectMetadata>> {
        let mut projects = Vec::new();

        if !root.is_dir() {
            return Ok(projects);
        }

        let mut entries = tokio::fs::read_dir(root).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();

            if !path.is_dir() {
                continue;
            }

            // Skip hidden directories and special folders
            let name = entry.file_name();
            let name_str = name.to_string_lossy();
            if name_str.starts_with('.') || name_str.starts_with('_') {
                continue;
            }

            // Skip common non-project directories
            let skip_dirs = ["node_modules", "target", "dist", "build", ".git"];
            if skip_dirs.contains(&name_str.as_ref()) {
                continue;
            }

            // Detect project type and metadata
            if let Some(metadata) = self.analyze_project(&path, &name_str).await {
                projects.push(metadata);
            }
        }

        Ok(projects)
    }

    /// Analyze a single project directory
    async fn analyze_project(&self, path: &Path, name: &str) -> Option<ProjectMetadata> {
        // Detect language stack
        let language = self.detect_language(path).await?;

        // Check for documentation files
        let has_claude_md = path.join("CLAUDE.md").exists();
        let has_readme = path.join("README.md").exists() || path.join("readme.md").exists();
        let has_contributing = path.join("CONTRIBUTING.md").exists();
        let has_license = path.join("LICENSE").exists() || path.join("LICENSE.md").exists();
        let has_changelog = path.join("CHANGELOG.md").exists();

        // Check for compliance files
        let has_codecov = path.join("codecov.yml").exists();
        let has_deny_toml = path.join("deny.toml").exists();
        let has_security_workflow = path.join(".github/workflows/security.yml").exists()
            || path.join(".github/workflows/sast-full.yml").exists();

        // Count workflows
        let workflow_count = self.count_workflows(path).await;

        // Try to extract GitHub owner from git remote or use default
        let owner = self
            .detect_owner(path)
            .await
            .unwrap_or_else(|| "<REDACTED>".to_string());

        Some(ProjectMetadata {
            name: name.to_string(),
            path: path.to_path_buf(),
            language,
            github_repo: Some(name.to_string()),
            owner,
            has_claude_md,
            has_readme,
            has_contributing,
            has_license,
            has_changelog,
            has_codecov,
            has_deny_toml,
            has_security_workflow,
            workflow_count,
        })
    }

    /// Detect the language stack of a project
    async fn detect_language(&self, path: &Path) -> Option<LanguageStack> {
        let mut languages = Vec::new();

        if path.join("Cargo.toml").exists() {
            languages.push("rust".to_string());
        }

        if path.join("package.json").exists() {
            languages.push("typescript".to_string());
        }

        if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
            languages.push("python".to_string());
        }

        if path.join("go.mod").exists() {
            languages.push("go".to_string());
        }

        match languages.len() {
            0 => None,
            1 => match languages[0].as_str() {
                "rust" => Some(LanguageStack::Rust),
                "typescript" => Some(LanguageStack::TypeScript),
                "python" => Some(LanguageStack::Python),
                "go" => Some(LanguageStack::Go),
                _ => Some(LanguageStack::Mixed(languages)),
            },
            _ => Some(LanguageStack::Mixed(languages)),
        }
    }

    /// Count GitHub workflow files
    async fn count_workflows(&self, path: &Path) -> usize {
        let workflows_dir = path.join(".github/workflows");
        if !workflows_dir.exists() {
            return 0;
        }

        match tokio::fs::read_dir(&workflows_dir).await {
            Ok(mut entries) => {
                let mut count = 0;
                while let Ok(Some(entry)) = entries.next_entry().await {
                    let file_name = entry.file_name();
                    let name_str = file_name.to_string_lossy();
                    if name_str.ends_with(".yml") || name_str.ends_with(".yaml") {
                        count += 1;
                    }
                }
                count
            }
            Err(_) => 0,
        }
    }

    /// Detect repository owner from git config
    async fn detect_owner(&self, _path: &Path) -> Option<String> {
        // In a real implementation, this would parse git remote origin URL
        // For now, return None to use default
        None
    }

    /// Get all registered projects
    pub fn get_projects(&self) -> Vec<&ProjectMetadata> {
        self.projects.values().collect()
    }

    /// Get a specific project by name
    pub fn get_project(&self, name: &str) -> Option<&ProjectMetadata> {
        self.projects.get(name)
    }
}

#[cfg(test)]
mod tests {
    use tempfile::TempDir;

    use super::*;

    #[tokio::test]
    async fn test_detect_language_rust() {
        let dir = TempDir::new().unwrap();
        std::fs::write(dir.path().join("Cargo.toml"), "[package]").unwrap();

        let registry = ProjectRegistry::new();
        let lang = registry.detect_language(dir.path()).await;

        assert!(matches!(lang, Some(LanguageStack::Rust)));
    }

    #[tokio::test]
    async fn test_detect_language_typescript() {
        let dir = TempDir::new().unwrap();
        std::fs::write(dir.path().join("package.json"), "{}").unwrap();

        let registry = ProjectRegistry::new();
        let lang = registry.detect_language(dir.path()).await;

        assert!(matches!(lang, Some(LanguageStack::TypeScript)));
    }

    #[tokio::test]
    async fn test_detect_language_mixed() {
        let dir = TempDir::new().unwrap();
        std::fs::write(dir.path().join("Cargo.toml"), "[package]").unwrap();
        std::fs::write(dir.path().join("package.json"), "{}").unwrap();

        let registry = ProjectRegistry::new();
        let lang = registry.detect_language(dir.path()).await;

        assert!(matches!(lang, Some(LanguageStack::Mixed(_))));
    }
}
