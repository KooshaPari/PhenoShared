//! Small, dependency-free validation for the portable OKF Markdown boundary.
//!
//! OKF v0.2 intentionally has one universally required frontmatter key: `type`.
//! The validator therefore rejects malformed concept boundaries without rejecting
//! producer-defined extensions such as provenance or trust metadata.

use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConceptMetadata {
    pub type_name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError(&'static str);

impl fmt::Display for ValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.0)
    }
}

impl std::error::Error for ValidationError {}

/// Validate the required frontmatter shape of an OKF concept document.
///
/// This deliberately does not parse or reject extension fields. OKF requires
/// consumers to tolerate unknown metadata so round-tripping stays portable.
pub fn validate_concept(markdown: &str) -> Result<ConceptMetadata, ValidationError> {
    let mut lines = markdown.lines();
    if lines.next() != Some("---") {
        return Err(ValidationError("OKF frontmatter must start with `---`"));
    }

    let mut type_name = None;
    let mut closed = false;
    for line in lines.by_ref() {
        if line == "---" {
            closed = true;
            break;
        }
        if let Some(value) = line.strip_prefix("type:") {
            if matches!(value.as_bytes().first(), None | Some(b' ' | b'\t')) {
                type_name = Some(unquote_yaml_scalar(value.trim()));
            }
        }
    }
    if !closed {
        return Err(ValidationError("OKF frontmatter must end with `---`"));
    }
    let type_name = type_name.ok_or(ValidationError("OKF concept requires a `type` field"))?;
    if type_name.is_empty() {
        return Err(ValidationError("OKF concept `type` must not be empty"));
    }
    Ok(ConceptMetadata { type_name })
}

fn unquote_yaml_scalar(value: &str) -> String {
    let bytes = value.as_bytes();
    if bytes.len() >= 2
        && matches!(bytes[0], b'\'' | b'"')
        && bytes[0] == *bytes.last().expect("checked length")
    {
        value[1..value.len() - 1].trim().to_string()
    } else {
        value.to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_type_key_without_yaml_delimiter_whitespace() {
        let result = validate_concept("---\ntype:evil\n---\n# Not an OKF concept");

        assert_eq!(
            result.unwrap_err().to_string(),
            "OKF concept requires a `type` field"
        );
    }
}
