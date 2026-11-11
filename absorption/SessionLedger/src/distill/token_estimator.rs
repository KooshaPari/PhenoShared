//! Lightweight token estimation without a tokenizer dependency.

use serde_json::Value;

/// Estimates the token budget needed to inject text or structured JSON.
pub trait TokenEstimator {
    /// Estimate tokens for plain text.
    fn estimate_text(&self, text: &str) -> u32;

    /// Estimate tokens for a JSON value using its compact serialized form.
    fn estimate_json(&self, value: &Value) -> u32 {
        self.estimate_text(&value.to_string())
    }
}

/// A deterministic estimator that assumes approximately four characters/token.
#[derive(Debug, Default, Clone, Copy)]
pub struct CharCountTokenEstimator;

impl TokenEstimator for CharCountTokenEstimator {
    fn estimate_text(&self, text: &str) -> u32 {
        let characters = u32::try_from(text.chars().count()).unwrap_or(u32::MAX);
        characters.saturating_add(3) / 4
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn empty_text_costs_zero_tokens() {
        assert_eq!(CharCountTokenEstimator.estimate_text(""), 0);
    }

    #[test]
    fn text_estimate_rounds_up_to_four_character_chunks() {
        let estimator = CharCountTokenEstimator;
        assert_eq!(estimator.estimate_text("a"), 1);
        assert_eq!(estimator.estimate_text("abcd"), 1);
        assert_eq!(estimator.estimate_text("abcde"), 2);
    }

    #[test]
    fn estimator_counts_characters_not_utf8_bytes() {
        assert_eq!(CharCountTokenEstimator.estimate_text("🦀🦀🦀🦀"), 1);
    }

    #[test]
    fn json_estimate_uses_compact_serialization() {
        let value = json!({"key":"value"});
        assert_eq!(
            CharCountTokenEstimator.estimate_json(&value),
            CharCountTokenEstimator.estimate_text(r#"{"key":"value"}"#)
        );
    }
}
