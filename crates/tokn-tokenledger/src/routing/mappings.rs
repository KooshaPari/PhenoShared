//! Model and provider mapping utilities.
//!
//! Provides deterministic mapping from source model IDs to canonical forms.

use super::ports::*;

// =============================================================================
// MODEL MAPPING RULES
// =============================================================================

/// Mapping rule types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MappingRule {
    /// Direct match
    Exact,
    /// Prefix match (e.g., "openai/" prefix)
    Prefix,
    /// Suffix match (e.g., "/high" suffix)
    Suffix,
    /// Regex match
    Regex,
    /// Fuzzy match
    Fuzzy,
    /// Manual override
    Manual,
    /// No match found
    None,
}

/// Known provider prefixes
pub const PROVIDER_PREFIXES: &[(&str, &str)] = &[
    ("openai/", "openai"),
    ("anthropic/", "anthropic"),
    ("google/", "google"),
    ("amazon/", "aws"),
    ("cohere/", "cohere"),
    ("mistralai/", "mistral"),
    ("meta-llama/", "meta"),
    ("deepseek/", "deepseek"),
    ("xai/", "xai"),
    ("moonshotai/", "moonshot"),
    ("01-ai/", "01-ai"),
    ("qwen/", "qwen"),
    ("nvidia/", "nvidia"),
    ("anyscale/", "anyscale"),
    ("replicate/", "replicate"),
];

/// Known model family patterns
pub const MODEL_FAMILIES: &[(&str, &str)] = &[
    ("gpt-5", "gpt-5"),
    ("gpt-4o", "gpt-4o"),
    ("gpt-4", "gpt-4"),
    ("gpt-3.5", "gpt-3.5"),
    ("claude-opus", "claude-opus"),
    ("claude-sonnet", "claude-sonnet"),
    ("claude-haiku", "claude-haiku"),
    ("gemini-3", "gemini-3"),
    ("gemini-2", "gemini-2"),
    ("gemini-1", "gemini-1"),
    ("llama-4", "llama-4"),
    ("llama-3", "llama-3"),
    ("llama-2", "llama-2"),
    ("deepseek-v3", "deepseek-v3"),
    ("deepseek-r1", "deepseek-r1"),
    ("qwen-3", "qwen-3"),
    ("qwen-2", "qwen-2"),
];

/// Resolve provider from model ID
pub fn resolve_provider(model_id: &str) -> (Option<String>, MappingRule) {
    let lower = model_id.to_lowercase();

    for (prefix, provider) in PROVIDER_PREFIXES {
        if lower.starts_with(prefix) {
            return (Some(provider.to_string()), MappingRule::Prefix);
        }
    }

    // Check model families for hints
    for (family, _provider) in MODEL_FAMILIES {
        if lower.contains(family) {
            // Infer provider from family
            let provider = match *family {
                "gpt-" => Some("openai"),
                "claude-" => Some("anthropic"),
                "gemini-" => Some("google"),
                "llama-" => Some("meta"),
                "deepseek-" => Some("deepseek"),
                "qwen-" => Some("qwen"),
                _ => None,
            };
            return (provider.map(String::from), MappingRule::Fuzzy);
        }
    }

    (None, MappingRule::None)
}

/// Normalize model ID to canonical form
pub fn normalize_model_id(model_id: &str) -> (String, MappingRule) {
    let lower = model_id.to_lowercase();
    let trimmed = lower.trim();

    // Remove provider prefix
    let canonical = PROVIDER_PREFIXES
        .iter()
        .find(|(prefix, _)| trimmed.starts_with(prefix))
        .map(|(prefix, _)| &trimmed[prefix.len()..])
        .unwrap_or(trimmed);

    // Remove common suffixes
    let cleaned = canonical
        .trim_end_matches("-high")
        .trim_end_matches("-low")
        .trim_end_matches("-medium")
        .trim_end_matches("/high")
        .trim_end_matches("/low")
        .trim_end_matches("/medium");

    let rule = if cleaned != canonical {
        MappingRule::Suffix
    } else if trimmed != model_id {
        MappingRule::Prefix
    } else {
        MappingRule::Exact
    };

    (cleaned.to_string(), rule)
}

/// Resolve harness from model or context
pub fn resolve_harness(_model_id: &str, _headers: Option<&str>) -> (Option<String>, MappingRule) {
    // Could use headers or other context hints
    // For now, return unknown
    (None, MappingRule::None)
}

// =============================================================================
// CONVENIENCE FUNCTIONS
// =============================================================================

/// Create a model mapping from raw inputs
pub fn create_mapping(
    source_model: &str,
    provider: Option<&str>,
    harness: Option<&str>,
) -> ModelMapping {
    let (resolved_provider, provider_rule) = resolve_provider(source_model);
    let (canonical, normalize_rule) = normalize_model_id(source_model);
    let (resolved_harness, _) = resolve_harness(source_model, None);

    let p = provider.or(resolved_provider.as_deref());
    let h = harness.or(resolved_harness.as_deref());

    let confidence = match (provider.is_some(), normalize_rule) {
        (true, MappingRule::Exact) => 1.0,
        (true, _) => 0.9,
        (false, MappingRule::Exact) => 0.8,
        (false, MappingRule::Prefix) => 0.7,
        _ => 0.5,
    };

    let rule = match (provider_rule, normalize_rule) {
        (MappingRule::Prefix, _) => "provider_prefix",
        (_, MappingRule::Suffix) => "model_suffix",
        (MappingRule::Fuzzy, _) => "model_family",
        _ => "normalize",
    };

    ModelMapping {
        source_model: source_model.to_string(),
        canonical_model: canonical,
        provider: p.map(String::from),
        harness: h.map(String::from),
        confidence,
        rule: rule.to_string(),
    }
}

/// Resolve complete trio
pub fn resolve_trio(
    provider: Option<&str>,
    harness: Option<&str>,
    model: &str,
) -> ProviderHarnessModel {
    let mapping = create_mapping(model, provider, harness);

    ProviderHarnessModel {
        provider: mapping.provider.unwrap_or_else(|| "unknown".to_string()),
        harness: mapping.harness.unwrap_or_else(|| "unknown".to_string()),
        model: mapping.canonical_model,
        quality_score: None,
        cost_per_1k: None,
        latency_ms: None,
        throughput_tps: None,
        context_window: None,
        success_rate: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_provider() {
        let (provider, rule) = resolve_provider("openai/gpt-4o");
        assert_eq!(provider, Some("openai".to_string()));
        assert_eq!(rule, MappingRule::Prefix);

        let (provider, _rule) = resolve_provider("anthropic/claude-3-5-sonnet");
        assert_eq!(provider, Some("anthropic".to_string()));
    }

    #[test]
    fn test_normalize_model_id() {
        let (canonical, _rule) = normalize_model_id("openai/gpt-4o");
        assert_eq!(canonical, "gpt-4o");

        let (canonical, _rule) = normalize_model_id("GPT-4O");
        assert_eq!(canonical, "gpt-4o");
    }

    #[test]
    fn test_create_mapping() {
        let mapping = create_mapping("gpt-4o", Some("openai"), None);
        assert_eq!(mapping.canonical_model, "gpt-4o");
        assert_eq!(mapping.provider, Some("openai".to_string()));
    }
}
