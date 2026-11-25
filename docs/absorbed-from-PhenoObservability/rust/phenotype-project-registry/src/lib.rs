use serde::{Deserialize, Serialize};
use std::path::Path;

/// Type of project detected
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProjectType {
    RustLibrary,
    RustApplication,
    TypeScriptLibrary,
    TypeScriptApplication,
    GoModule,
    PythonPackage,
    Unknown,
}

/// Health configuration metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthConfig {
    pub enabled: bool,
    pub endpoint: Option<String>,
    pub interval_seconds: Option<u64>,
}

/// Project metadata discovered from filesystem
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectMetadata {
    pub name: String,
    pub project_type: ProjectType,
    pub path: std::path::PathBuf,
    pub health_config: HealthConfig,
}

/// Discover projects under the given root path
pub fn discover_projects(root: impl AsRef<Path>) -> anyhow::Result<Vec<ProjectMetadata>> {
    let root = root.as_ref();
    let mut projects = Vec::new();

    for entry in walkdir::WalkDir::new(root)
        .max_depth(3)
        .into_iter()
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            !name.starts_with('.') && name != "target" && name != "node_modules"
        })
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        let project_type = detect_project_type(path);

        if !matches!(project_type, ProjectType::Unknown) {
            let name = path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();

            let health_config = detect_health_config(path);

            projects.push(ProjectMetadata {
                name,
                project_type,
                path: path.to_path_buf(),
                health_config,
            });
        }
    }

    Ok(projects)
}

fn detect_project_type(path: &Path) -> ProjectType {
    if path.join("Cargo.toml").exists() {
        // Heuristic: if src/main.rs exists, it's an application
        if path.join("src/main.rs").exists() {
            ProjectType::RustApplication
        } else {
            ProjectType::RustLibrary
        }
    } else if path.join("package.json").exists() {
        if path.join("src/main.ts").exists() || path.join("src/index.ts").exists() {
            ProjectType::TypeScriptApplication
        } else {
            ProjectType::TypeScriptLibrary
        }
    } else if path.join("go.mod").exists() {
        ProjectType::GoModule
    } else if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
        ProjectType::PythonPackage
    } else {
        ProjectType::Unknown
    }
}

fn detect_health_config(path: &Path) -> HealthConfig {
    let enabled = path.join("health.toml").exists() || path.join(".github/health.yaml").exists();
    HealthConfig {
        enabled,
        endpoint: None,
        interval_seconds: None,
    }
}
