//! Specification-driven development module.
//!
//! ## xDD Methodology: SpecDD (Specification-Driven Development)
//!
//! SpecDD combines executable specifications with traditional
//! requirements to create living documentation.
//!
//! ## Spec Format
//!
//! ```yaml
//! spec:
//!   name: User Authentication
//!   version: 1.0.0
//!   features:
//!     - id: AUTH-001
//!       name: Login
//!       scenario:
//!         given: valid credentials
//!         when: user submits login form
//!         then: redirect to dashboard
//! ```
//!
//! ## Usage
//!
//! ```rust,no_run
//! use phenotype_xdd_lib::spec::parser::SpecParser;
//!
//! let yaml_str = "spec:\n  name: My Spec\n  version: 1.0.0\n";
//! let spec = SpecParser::parse_yaml(yaml_str).unwrap();
//! assert_eq!(spec.spec.name, "My Spec");
//! ```

pub use parser::SpecParser;
use serde::{Deserialize, Serialize};
pub use validator::SpecValidator;

use crate::domain::{XddError, XddResult};

/// Specification root.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Spec {
    pub spec: SpecMetadata,
    #[serde(default)]
    pub features: Vec<Feature>,
    #[serde(default)]
    pub requirements: Vec<Requirement>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpecMetadata {
    pub name: String,
    pub version: String,
    #[serde(default)]
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Feature {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub description: Option<String>,
    #[serde(default)]
    pub scenario: Option<Scenario>,
    #[serde(default)]
    pub given: Vec<Condition>,
    #[serde(default)]
    pub when: Vec<Action>,
    #[serde(default)]
    pub then: Vec<Outcome>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Scenario {
    pub given: String,
    pub when: String,
    pub then: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Condition {
    pub description: String,
    #[serde(default)]
    pub params: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Action {
    pub description: String,
    #[serde(default)]
    pub params: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Outcome {
    pub description: String,
    #[serde(default)]
    pub params: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Requirement {
    pub id: String,
    pub description: String,
    #[serde(default)]
    pub priority: Priority,
    #[serde(default)]
    pub status: Status,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
#[derive(Default)]
pub enum Priority {
    Critical,
    High,
    #[default]
    Medium,
    Low,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
#[derive(Default)]
pub enum Status {
    #[default]
    Pending,
    Implemented,
    Verified,
    Deferred,
}

/// Parsed and validated specification.
pub mod parser {
    use super::*;

    /// Parse specification from YAML string.
    pub fn parse_yaml(yaml: &str) -> XddResult<Spec> {
        serde_yaml_ng::from_str(yaml)
            .map_err(|e| XddError::spec(format!("Failed to parse YAML: {e}")))
    }

    /// SpecParser with validation.
    pub struct SpecParser;

    impl SpecParser {
        /// Parse and validate a specification.
        pub fn parse(spec_yaml: &str) -> XddResult<Spec> {
            let spec = parse_yaml(spec_yaml)?;
            super::SpecValidator::new().validate(&spec)?;
            Ok(spec)
        }

        /// Parse a YAML specification string (alias for `parse`).
        pub fn parse_yaml(spec_yaml: &str) -> XddResult<Spec> {
            Self::parse(spec_yaml)
        }

        /// Parse from a file.
        pub fn parse_file(path: &std::path::Path) -> XddResult<Spec> {
            let content = std::fs::read_to_string(path)
                .map_err(|e| XddError::spec(format!("Failed to read file: {e}")))?;
            Self::parse(&content)
        }
    }
}

/// Specification validator.
pub mod validator {
    use super::*;

    pub struct SpecValidator {
        errors: Vec<XddError>,
    }

    impl SpecValidator {
        pub fn new() -> Self {
            Self { errors: vec![] }
        }

        /// Validate a specification.
        pub fn validate(&mut self, spec: &Spec) -> XddResult<()> {
            self.validate_metadata(&spec.spec);
            self.validate_features(&spec.features);
            self.validate_requirements(&spec.requirements);

            if !self.errors.is_empty() {
                return Err(XddError::spec(format!(
                    "Validation failed: {} errors",
                    self.errors.len()
                )));
            }
            Ok(())
        }

        fn validate_metadata(&mut self, meta: &SpecMetadata) {
            if meta.name.is_empty() {
                self.errors
                    .push(XddError::spec("Spec name cannot be empty"));
            }
            if meta.version.is_empty() {
                self.errors
                    .push(XddError::spec("Spec version cannot be empty"));
            }
        }

        fn validate_features(&mut self, features: &[Feature]) {
            let mut seen_ids = std::collections::HashSet::new();
            for feature in features {
                if !seen_ids.insert(&feature.id) {
                    self.errors.push(XddError::spec(format!(
                        "Duplicate feature ID: {}",
                        feature.id
                    )));
                }
                if feature.name.is_empty() {
                    self.errors
                        .push(XddError::spec("Feature name cannot be empty"));
                }
                // Either scenario or given/when/then should be present
                if feature.scenario.is_none()
                    && feature.given.is_empty()
                    && feature.when.is_empty()
                    && feature.then.is_empty()
                {
                    self.errors.push(XddError::spec(format!(
                        "Feature {} has no scenario or given/when/then",
                        feature.id
                    )));
                }
            }
        }

        fn validate_requirements(&mut self, requirements: &[Requirement]) {
            let mut seen_ids = std::collections::HashSet::new();
            for req in requirements {
                if !seen_ids.insert(&req.id) {
                    self.errors.push(XddError::spec(format!(
                        "Duplicate requirement ID: {}",
                        req.id
                    )));
                }
                if req.description.is_empty() {
                    self.errors
                        .push(XddError::spec("Requirement description cannot be empty"));
                }
            }
        }
    }

    impl Default for SpecValidator {
        fn default() -> Self {
            Self::new()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_valid_spec() {
        let yaml = r#"
spec:
  name: Test Spec
  version: 1.0.0
features:
  - id: TEST-001
    name: Test Feature
    given:
      - description: initial condition
    when:
      - description: action performed
    then:
      - description: expected outcome
"#;
        let spec = SpecParser::parse(yaml).unwrap();
        assert_eq!(spec.spec.name, "Test Spec");
        assert_eq!(spec.features.len(), 1);
    }

    #[test]
    fn test_parse_invalid_yaml() {
        let yaml = "not: valid: yaml:";
        assert!(SpecParser::parse(yaml).is_err());
    }

    #[test]
    fn test_validate_empty_name() {
        let spec = Spec {
            spec: SpecMetadata {
                name: "".to_string(),
                version: "1.0.0".to_string(),
                description: None,
            },
            features: vec![],
            requirements: vec![],
        };
        let result = SpecValidator::new().validate(&spec);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_duplicate_feature_ids() {
        let spec = Spec {
            spec: SpecMetadata {
                name: "Test".to_string(),
                version: "1.0.0".to_string(),
                description: None,
            },
            features: vec![
                Feature {
                    id: "TEST-001".to_string(),
                    name: "Feature 1".to_string(),
                    description: None,
                    scenario: None,
                    given: vec![],
                    when: vec![],
                    then: vec![],
                },
                Feature {
                    id: "TEST-001".to_string(),
                    name: "Feature 2".to_string(),
                    description: None,
                    scenario: None,
                    given: vec![],
                    when: vec![],
                    then: vec![],
                },
            ],
            requirements: vec![],
        };
        let result = SpecValidator::new().validate(&spec);
        assert!(result.is_err());
    }
}
