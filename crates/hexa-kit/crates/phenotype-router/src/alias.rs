//! H14.3 model-id alias resolver.
//!
//! Maps human-friendly model aliases (e.g. "fast", "gpt4", "claude-opus")
//! onto concrete upstream target identifiers (e.g. provider-specific
//! model ids or pool tags). Pure stdlib — no new deps.
//!
//! Resolution rules:
//!   1. Exact match (case-insensitive) on the full alias key wins.
//!   2. Wildcard fallback: if the alias key starts with `*`, match by
//!      suffix (case-insensitive).
//!   3. If nothing matches, return `None` (caller may apply its own
//!      default / 404 handling).
//!
//! The `default` field on [`AliasResolver`] is *not* used by
//! [`AliasResolver::resolve`] — it is exposed so callers can build their
//! own "resolve-or-default" wrapper without re-checking the map.

use std::collections::HashMap;

/// A single alias entry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelAlias {
    /// Canonical (lowercased) alias key. Case-insensitive at lookup time.
    pub alias: String,
    /// Concrete target identifier (e.g. `gpt-4o-mini`, `cliproxy-fast`).
    pub target: String,
    /// Optional provider hint (e.g. `openai`, `anthropic`, `cliproxy`).
    pub provider: Option<String>,
}

impl ModelAlias {
    pub fn new(alias: impl Into<String>, target: impl Into<String>) -> Self {
        Self {
            alias: alias.into().to_lowercase(),
            target: target.into(),
            provider: None,
        }
    }

    pub fn with_provider(
        alias: impl Into<String>,
        target: impl Into<String>,
        provider: impl Into<String>,
    ) -> Self {
        Self {
            alias: alias.into().to_lowercase(),
            target: target.into(),
            provider: Some(provider.into()),
        }
    }
}

/// Result of resolving an alias.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolvedRoute {
    pub target: String,
    pub provider: Option<String>,
}

const WILDCARD: &str = "*";

/// Alias registry + resolver.
#[derive(Debug, Clone, Default)]
pub struct AliasResolver {
    aliases: HashMap<String, ModelAlias>,
    /// Default fallback target used by callers' own resolve-or-default
    /// logic. Not consulted by [`Self::resolve`].
    pub default: String,
}

impl AliasResolver {
    /// New empty resolver.
    pub fn new() -> Self {
        Self::default()
    }

    /// New resolver with a default fallback target.
    pub fn with_default(default: impl Into<String>) -> Self {
        Self {
            aliases: HashMap::new(),
            default: default.into(),
        }
    }

    /// Register an alias. Keys are normalized to lowercase; later calls
    /// overwrite earlier ones for the same key.
    pub fn add(
        &mut self,
        alias: impl Into<String>,
        target: impl Into<String>,
        provider: Option<String>,
    ) {
        let key = alias.into().to_lowercase();
        self.aliases.insert(
            key.clone(),
            ModelAlias {
                alias: key,
                target: target.into(),
                provider,
            },
        );
    }

    /// Number of registered aliases.
    pub fn len(&self) -> usize {
        self.aliases.len()
    }

    pub fn is_empty(&self) -> bool {
        self.aliases.is_empty()
    }

    /// Iterate over registered aliases (insertion order is unspecified).
    pub fn iter(&self) -> impl Iterator<Item = (&String, &ModelAlias)> {
        self.aliases.iter()
    }

    /// Resolve `model_id` to a concrete route.
    ///
    /// Lookup order:
    ///   1. Exact case-insensitive match on the full key.
    ///   2. Wildcard suffix match: for each key starting with `*`,
    ///      match if `model_id` ends with the suffix after `*`
    ///      (case-insensitive).
    pub fn resolve(&self, model_id: &str) -> Option<ResolvedRoute> {
        let needle = model_id.to_lowercase();

        // 1. Exact match wins.
        if let Some(entry) = self.aliases.get(&needle) {
            return Some(ResolvedRoute {
                target: entry.target.clone(),
                provider: entry.provider.clone(),
            });
        }

        // 2. Wildcard fallback. First-match-wins (HashMap iteration order).
        for (key, entry) in &self.aliases {
            if let Some(suffix) = key.strip_prefix(WILDCARD) {
                if !suffix.is_empty() && needle.ends_with(suffix) {
                    return Some(ResolvedRoute {
                        target: entry.target.clone(),
                        provider: entry.provider.clone(),
                    });
                }
            }
        }

        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> AliasResolver {
        let mut r = AliasResolver::with_default("gpt-4o-mini");
        r.add("fast", "gpt-4o-mini", Some("openai".into()));
        r.add("smart", "claude-opus-4-7", Some("anthropic".into()));
        r.add("local", "llama-3.1-70b", Some("ollama".into()));
        r
    }

    #[test]
    fn exact_match_returns_route() {
        let r = sample();
        let got = r.resolve("fast").unwrap();
        assert_eq!(got.target, "gpt-4o-mini");
        assert_eq!(got.provider.as_deref(), Some("openai"));
    }

    #[test]
    fn lookup_is_case_insensitive() {
        let r = sample();
        assert_eq!(r.resolve("FAST").unwrap().target, "gpt-4o-mini");
        assert_eq!(r.resolve("Fast").unwrap().target, "gpt-4o-mini");
        assert_eq!(
            r.resolve("fAsT").unwrap().provider.as_deref(),
            Some("openai")
        );
    }

    #[test]
    fn missing_alias_returns_none() {
        let r = sample();
        assert!(r.resolve("does-not-exist").is_none());
        assert!(r.resolve("").is_none());
    }

    #[test]
    fn wildcard_suffix_fallback_matches() {
        let mut r = AliasResolver::new();
        r.add("*mini", "gpt-4o-mini", Some("openai".into()));
        r.add("fast", "gpt-4o-mini", Some("openai".into()));

        // Wildcard falls through to suffix match.
        assert_eq!(r.resolve("gpt-3.5-mini").unwrap().target, "gpt-4o-mini");
        assert_eq!(r.resolve("anything-mini").unwrap().target, "gpt-4o-mini");
    }

    #[test]
    fn exact_match_beats_wildcard() {
        let mut r = AliasResolver::new();
        r.add("special-mini", "exact-target", Some("provider-a".into()));
        r.add("*mini", "wildcard-target", Some("provider-b".into()));

        let got = r.resolve("special-mini").unwrap();
        assert_eq!(got.target, "exact-target");
        assert_eq!(got.provider.as_deref(), Some("provider-a"));
    }

    #[test]
    fn add_overwrites_existing_key() {
        let mut r = AliasResolver::new();
        r.add("fast", "old-target", None);
        r.add("fast", "new-target", Some("provider-x".into()));
        assert_eq!(r.len(), 1);
        let got = r.resolve("fast").unwrap();
        assert_eq!(got.target, "new-target");
        assert_eq!(got.provider.as_deref(), Some("provider-x"));
    }

    #[test]
    fn wildcard_empty_suffix_is_ignored() {
        // A bare "*" key would match everything; treat as a no-op so
        // exact-match resolution still works correctly.
        let mut r = AliasResolver::new();
        r.add("*", "catch-all", None);
        r.add("fast", "gpt-4o-mini", Some("openai".into()));

        assert_eq!(r.resolve("fast").unwrap().target, "gpt-4o-mini");
        // The bare "*" entry must NOT swallow other queries.
        assert!(r.resolve("random-model").is_none());
    }

    #[test]
    fn default_field_is_preserved() {
        let r = AliasResolver::with_default("fallback-target");
        assert_eq!(r.default, "fallback-target");
        assert!(r.resolve("anything").is_none());
    }

    #[test]
    fn model_alias_helpers_lowercase_key() {
        let a = ModelAlias::new("Fast", "gpt-4o-mini");
        assert_eq!(a.alias, "fast");
        assert_eq!(a.target, "gpt-4o-mini");
        assert!(a.provider.is_none());

        let b = ModelAlias::with_provider("SMART", "claude-opus", "anthropic");
        assert_eq!(b.alias, "smart");
        assert_eq!(b.provider.as_deref(), Some("anthropic"));
    }
}
