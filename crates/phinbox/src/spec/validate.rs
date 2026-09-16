//! Validation logic for prompt specs.

use super::types::{FieldSpec, PromptSpec};

impl PromptSpec {
    /// Validate the spec. Returns an error message on the first violation.
    pub fn validate(&self) -> Result<(), String> {
        if self.title.is_empty() {
            return Err("title must not be empty".into());
        }
        if self.title.chars().count() > 80 {
            return Err(format!(
                "title exceeds 80 chars (got {})",
                self.title.chars().count()
            ));
        }
        if self.question.chars().count() > 2000 {
            return Err(format!(
                "question exceeds 2000 chars (got {})",
                self.question.chars().count()
            ));
        }
        if let FieldSpec::Choice { options, default_index, .. } = &self.field {
            if options.is_empty() {
                return Err("choice field must have at least one option".into());
            }
            if let Some(idx) = default_index {
                if *idx >= options.len() {
                    return Err(format!(
                        "default_index {idx} out of range ({} options)",
                        options.len()
                    ));
                }
            }
        }
        if let FieldSpec::Text { pattern: Some(p), .. } = &self.field {
            regex::Regex::new(p).map_err(|e| format!("invalid pattern regex: {e}"))?;
        }
        Ok(())
    }
}
