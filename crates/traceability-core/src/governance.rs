//! Governance types — contracts, rules, and evidence.
//!
//! Source: [`AgilePlus/crates/agileplus-domain/src/domain/governance.rs`](https://example.invalid/AgilePlus/crates/agileplus-domain/src/domain/governance.rs)
//! (1:1 port of vocabulary; `fr_id` stays `String` at the boundary per ADR-0001 §2).

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Policy domain category.
///
/// Source: AgilePlus `governance.rs:7-15`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PolicyDomain {
    /// Security posture policies (scans, hardening).
    Security,
    /// Quality policies (tests, CI, lint).
    Quality,
    /// Regulatory / process compliance policies.
    Compliance,
    /// Performance and budget policies.
    Performance,
    /// Team-defined domain outside the built-ins.
    Custom,
}

impl PolicyDomain {
    /// Stable lowercase string for SQL / JSON round-trips.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Security => "security",
            Self::Quality => "quality",
            Self::Compliance => "compliance",
            Self::Performance => "performance",
            Self::Custom => "custom",
        }
    }
}

/// The definition of a policy rule (stored as JSON blob).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyDefinition {
    /// Human-readable statement of what the rule requires.
    pub description: String,
    /// How the rule is checked (manual vs automated).
    pub check: PolicyCheck,
}

/// An active policy rule in the registry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyRule {
    /// Registry id of the rule.
    pub id: i64,
    /// Domain the rule belongs to.
    pub domain: PolicyDomain,
    /// The rule body (description + check mode).
    pub rule: PolicyDefinition,
    /// Whether the rule is currently enforced.
    pub active: bool,
    /// UTC creation time.
    pub created_at: DateTime<Utc>,
    /// UTC last-modification time.
    pub updated_at: DateTime<Utc>,
}

/// A required-evidence entry inside a governance rule.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceRequirement {
    /// Functional-requirement ID the evidence must satisfy.
    pub fr_id: String,
    /// Type of evidence required.
    pub evidence_type: EvidenceType,
}

/// A governance rule captured inside a contract.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceRule {
    /// Lifecycle transition the rule guards (e.g. `Active->Done`).
    pub transition: String,
    /// Evidence that must exist for the transition.
    pub required_evidence: Vec<EvidenceRequirement>,
    /// Registry ids of the [`PolicyRule`]s referenced by this rule.
    pub policy_refs: Vec<i64>,
}

/// A versioned governance contract bound to a feature.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceContract {
    /// Contract id.
    pub id: i64,
    /// Feature the contract is bound to.
    pub feature_id: i64,
    /// Monotonic contract version.
    pub version: i32,
    /// Rules that make up the contract.
    pub rules: Vec<GovernanceRule>,
    /// UTC time the contract was bound to the feature.
    pub bound_at: DateTime<Utc>,
}

/// Type of evidence artifact.
///
/// Source: AgilePlus `governance.rs:74-84`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceType {
    /// Automated test-run output.
    TestResult,
    /// CI pipeline artifact / log.
    CiOutput,
    /// Peer-review sign-off record.
    ReviewApproval,
    /// Security-scanner report.
    SecurityScan,
    /// Linter / static-analysis output.
    LintResult,
    /// Human attestation recorded manually.
    ManualAttestation,
}

impl EvidenceType {
    /// Stable snake_case string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::TestResult => "test_result",
            Self::CiOutput => "ci_output",
            Self::ReviewApproval => "review_approval",
            Self::SecurityScan => "security_scan",
            Self::LintResult => "lint_result",
            Self::ManualAttestation => "manual_attestation",
        }
    }
}

/// An evidence artifact attached to a work package.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    /// Evidence record id.
    pub id: i64,
    /// Work package the evidence belongs to.
    pub wp_id: i64,
    /// Functional requirement the evidence satisfies.
    pub fr_id: String,
    /// Kind of evidence recorded.
    pub evidence_type: EvidenceType,
    /// Path to the evidence artifact.
    pub artifact_path: String,
    /// Optional structured payload (metrics, hashes, etc.).
    pub metadata: Option<serde_json::Value>,
    /// UTC time the evidence was recorded.
    pub created_at: DateTime<Utc>,
}

/// The result of a policy check.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PolicyCheck {
    /// A human must approve the policy.
    ManualApproval,
    /// The policy is verified by an automated check.
    Automated,
}

/// A well-known built-in policy that maps a short reference key to a
/// `PolicyDomain` + `EvidenceType` pair.
///
/// Source: AgilePlus `governance.rs:118-184`.
#[derive(Debug, Clone, Copy)]
pub struct BuiltinPolicy {
    /// Short human-readable label (e.g. "Unit tests passing").
    pub label: &'static str,
    /// Governance domain for grouping.
    pub domain: PolicyDomain,
    /// Required evidence kind.
    pub evidence_type: EvidenceType,
}

impl BuiltinPolicy {
    const KNOWN: &'static [(&'static str, BuiltinPolicy)] = &[
        (
            "tests-pass",
            BuiltinPolicy {
                label: "Unit tests passing",
                domain: PolicyDomain::Quality,
                evidence_type: EvidenceType::TestResult,
            },
        ),
        (
            "ci-green",
            BuiltinPolicy {
                label: "CI pipeline green",
                domain: PolicyDomain::Quality,
                evidence_type: EvidenceType::CiOutput,
            },
        ),
        (
            "review-approved",
            BuiltinPolicy {
                label: "Peer review approved",
                domain: PolicyDomain::Quality,
                evidence_type: EvidenceType::ReviewApproval,
            },
        ),
        (
            "security-scan",
            BuiltinPolicy {
                label: "Security scan clean",
                domain: PolicyDomain::Security,
                evidence_type: EvidenceType::SecurityScan,
            },
        ),
        (
            "lint-pass",
            BuiltinPolicy {
                label: "Lint checks pass",
                domain: PolicyDomain::Quality,
                evidence_type: EvidenceType::LintResult,
            },
        ),
    ];

    /// Look up a built-in policy by its reference key.
    pub fn from_ref(policy_ref: &str) -> Option<&'static BuiltinPolicy> {
        Self::KNOWN
            .iter()
            .find(|(key, _)| *key == policy_ref)
            .map(|(_, bp)| bp)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn policy_domain_as_str() {
        assert_eq!(PolicyDomain::Security.as_str(), "security");
        assert_eq!(PolicyDomain::Quality.as_str(), "quality");
        assert_eq!(PolicyDomain::Compliance.as_str(), "compliance");
        assert_eq!(PolicyDomain::Performance.as_str(), "performance");
        assert_eq!(PolicyDomain::Custom.as_str(), "custom");
    }

    #[test]
    fn evidence_type_as_str() {
        assert_eq!(EvidenceType::TestResult.as_str(), "test_result");
        assert_eq!(EvidenceType::CiOutput.as_str(), "ci_output");
        assert_eq!(
            EvidenceType::ManualAttestation.as_str(),
            "manual_attestation"
        );
    }

    #[test]
    fn builtin_policy_known_refs_resolve() {
        let tests_pass = BuiltinPolicy::from_ref("tests-pass").unwrap();
        assert_eq!(tests_pass.domain, PolicyDomain::Quality);
        assert_eq!(tests_pass.evidence_type, EvidenceType::TestResult);

        let security = BuiltinPolicy::from_ref("security-scan").unwrap();
        assert_eq!(security.domain, PolicyDomain::Security);
    }

    #[test]
    fn builtin_policy_unknown_ref_returns_none() {
        assert!(BuiltinPolicy::from_ref("nonexistent-policy").is_none());
        assert!(BuiltinPolicy::from_ref("").is_none());
    }

    #[test]
    fn governance_contract_serde_roundtrip() {
        let now = Utc::now();
        let contract = GovernanceContract {
            id: 42,
            feature_id: 100,
            version: 3,
            rules: vec![GovernanceRule {
                transition: "Active->Done".to_string(),
                required_evidence: vec![EvidenceRequirement {
                    fr_id: "FR-001".to_string(),
                    evidence_type: EvidenceType::TestResult,
                }],
                policy_refs: vec![1],
            }],
            bound_at: now,
        };
        let json = serde_json::to_string(&contract).unwrap();
        let back: GovernanceContract = serde_json::from_str(&json).unwrap();
        assert_eq!(back.id, contract.id);
        assert_eq!(back.rules.len(), 1);
    }
}
