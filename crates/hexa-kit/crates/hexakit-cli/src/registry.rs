use std::collections::HashMap;

use anyhow::{bail, Context, Result};
use serde::Deserialize;

const DOMAIN_ROLES_JSON: &str = include_str!("../assets/domain-roles.json");

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct DomainRolesRegistry {
    pub version: String,
    pub updated: String,
    pub source: String,
    pub domains: Vec<DomainRole>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DomainRole {
    pub id: String,
    pub repo: String,
    #[serde(default)]
    pub core_lang: Option<String>,
    #[serde(default)]
    pub edge_langs: Vec<String>,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub successor: Option<String>,
    #[serde(default)]
    pub justify_required: bool,
}

impl DomainRolesRegistry {
    pub fn bundled() -> Result<Self> {
        serde_json::from_str(DOMAIN_ROLES_JSON).context("parse bundled domain-roles.json")
    }

    pub fn find(&self, domain_id: &str) -> Result<&DomainRole> {
        self.domains
            .iter()
            .find(|d| d.id == domain_id)
            .with_context(|| format!("unknown domain {domain_id:?}"))
    }

    pub fn list_ids(&self) -> Vec<&str> {
        self.domains.iter().map(|d| d.id.as_str()).collect()
    }
}

/// Human-readable domain metadata derived from DOMAIN_ROLES.md rows.
pub fn domain_title(id: &str) -> &'static str {
    match id {
        "scaffolding" => "Scaffolding / templates",
        "types" => "Schemas / shared types",
        "testing" => "Testing",
        "observability" => "Observability",
        "mcp" => "MCP",
        "secrets" => "Secrets / auth",
        "resilience" => "HTTP / resilience",
        "tooling" => "Tooling crates",
        "infra" => "Tiny cross-cutting infra",
        "extras" => "Optional extras manifest",
        "code-review" => "Code review agent",
        "agent-runtime" => "Agent runtime",
        "process-mgr" => "Process manager / share CLI",
        _ => "Domain repository",
    }
}

pub fn domain_owns(id: &str) -> &'static [&'static str] {
    match id {
        "scaffolding" => &[
            "New-project bootstrap (hexagonal layout, folder folding, file templates)",
            "Fleet architectural pattern enforcement",
            "Generators that stamp per-repo config (not duplicated boilerplate repos)",
        ],
        "types" => &[
            "Schema SSOT (Protobuf/OpenAPI/Rust types as declared in repo boundary)",
            "Codegen and shared type definitions",
        ],
        "testing" => &[
            "Shared test utilities, fixtures, and fleet testing conventions",
            "Pre-commit / pre-push hook bundles for Phenotype repos",
        ],
        "observability" => &[
            "OpenTelemetry integration, health checks, and profiling helpers",
            "Fleet observability adapters and telemetry wiring",
        ],
        "mcp" => &[
            "Model Context Protocol hosts, servers, and SDK surfaces",
            "MCP transport and tool registration patterns",
        ],
        "secrets" => &[
            "Secrets management, auth flows, and credential rotation",
            "Auth vault APIs and policy hooks",
        ],
        "resilience" => &[
            "HTTP client resilience (retries, circuit breakers, timeouts)",
            "Cross-service reliability primitives",
        ],
        "tooling" => &[
            "Diff, registry, and shared tooling crates",
            "Resilience-adjacent shared utilities",
        ],
        "infra" => &[
            "Dynamic-keep cross-cutting infra (error helpers, config loaders, string/time utils)",
            "Crates too small for standalone repo governance",
        ],
        "extras" => &[
            "Dynamic extras manifest linking optional domain packages",
            "Opt-in package install hints (not boundary owners)",
        ],
        "code-review" => &[
            "Code review agent workflows and review automation",
            "Review policy integration with fleet governance",
        ],
        "agent-runtime" => &[
            "Agent runtime platform and orchestration",
            "Agent loop hosting and tool routing",
        ],
        "process-mgr" => &[
            "Process manager CLI and control-plane helpers",
            "Share/workflow CLI surfaces (successor: thegent control-plane)",
        ],
        _ => &["Domain-specific capability for this repository"],
    }
}

pub fn format_lang(lang: &str) -> String {
    match lang {
        "rust" => "Rust".into(),
        "py" | "python" => "Python 3.14+ (uv)".into(),
        "go" => "Go".into(),
        "ts" | "typescript" => "Bun + TypeScript".into(),
        "zig" => "Zig".into(),
        "mojo" => "Mojo".into(),
        other => other.to_string(),
    }
}

pub fn edge_lang_label(code: &str) -> String {
    match code {
        "py" => "Python".into(),
        "go" => "Go".into(),
        "ts" => "TypeScript".into(),
        other => other.to_string(),
    }
}

pub fn validate_domain_flag(domain: &str, registry: &DomainRolesRegistry) -> Result<()> {
    if domain.is_empty() {
        bail!(
            "--domain is required (available: {})",
            registry.list_ids().join(", ")
        );
    }
    registry.find(domain)?;
    Ok(())
}

pub fn adjacent_domains<'a>(
    registry: &'a DomainRolesRegistry,
    selected_id: &str,
) -> Vec<&'a DomainRole> {
    registry
        .domains
        .iter()
        .filter(|d| d.id != selected_id)
        .collect()
}

pub fn repo_url(repo: &str) -> String {
    format!("https://github.com/KooshaPari/{repo}")
}

#[allow(dead_code)]
pub fn domain_index(registry: &DomainRolesRegistry) -> HashMap<&str, &DomainRole> {
    registry
        .domains
        .iter()
        .map(|d| (d.id.as_str(), d))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_registry_parses() {
        let reg = DomainRolesRegistry::bundled().unwrap();
        assert_eq!(reg.domains.len(), 13);
        assert!(reg.find("testing").is_ok());
    }

    #[test]
    fn unknown_domain_errors() {
        let reg = DomainRolesRegistry::bundled().unwrap();
        assert!(reg.find("nope").is_err());
    }
}
