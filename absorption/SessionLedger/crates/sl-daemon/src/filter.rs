//! Pure filter logic for `sl search`.
//!
//! [`FilterSpec`] holds all filter criteria; [`apply_filters`] applies them to
//! a slice of [`BundleMeta`] references and returns only the matching items.

use crate::export::BundleMeta;

/// All filter parameters for `sl search`.
///
/// All fields are optional — an unset field means "no constraint on that axis".
#[derive(Debug, Clone)]
pub struct FilterSpec {
    /// Include only bundles whose `created_at` is >= this ISO date prefix (e.g. `"2024-01-01"`).
    pub since: Option<String>,
    /// Include only bundles whose `created_at` is <= this ISO date prefix (e.g. `"2024-12-31"`).
    pub until: Option<String>,
    /// Include only bundles whose `model` contains this substring (case-insensitive).
    pub model: Option<String>,
    /// Include only bundles with `token_count >= min_tokens`.
    pub min_tokens: Option<u64>,
    /// Include only bundles that carry ALL of these tags.
    pub tags: Vec<String>,
    /// Maximum number of results to return (applied after all other filters).
    pub limit: usize,
}

impl FilterSpec {
    /// Create a new `FilterSpec` with sensible defaults (no constraints, limit = 50).
    ///
    /// Used in unit tests and by callers that want a default limit-50 spec.
    // `new` is exercised by the test suite; the binary constructs FilterSpec via
    // struct literal so the compiler marks this dead from the bin target.
    #[allow(dead_code)]
    pub fn new() -> Self {
        Self { limit: 50, ..Self::default() }
    }
}

impl Default for FilterSpec {
    fn default() -> Self {
        Self {
            since: None,
            until: None,
            model: None,
            min_tokens: None,
            tags: Vec::new(),
            limit: 50,
        }
    }
}

/// Apply `spec` to `bundles` and return filtered, limited results.
///
/// Filtering order:
/// 1. `--since` / `--until` — lexicographic ISO-8601 comparison on `created_at`
/// 2. `--model` — case-insensitive substring match
/// 3. `--min-tokens` — numeric lower bound
/// 4. `--tag` (repeatable, AND logic) — every listed tag must be present
/// 5. `--limit` — truncate to at most N results
pub fn apply_filters<'a>(bundles: &'a [BundleMeta], spec: &FilterSpec) -> Vec<&'a BundleMeta> {
    let iter = bundles.iter().filter(|m| {
        // --since
        if let Some(ref since) = spec.since {
            if !m.created_at.is_empty() && m.created_at.as_str() < since.as_str() {
                return false;
            }
        }
        // --until
        if let Some(ref until) = spec.until {
            // Compare only the date prefix so "2024-01-31T23:59:59Z" passes "2024-01-31"
            let date_part = &m.created_at[..m.created_at.len().min(until.len())];
            if !m.created_at.is_empty() && date_part > until.as_str() {
                return false;
            }
        }
        // --model
        if let Some(ref pattern) = spec.model {
            if !m.model.to_ascii_lowercase().contains(&pattern.to_ascii_lowercase()) {
                return false;
            }
        }
        // --min-tokens
        if let Some(min) = spec.min_tokens {
            if m.token_count < min {
                return false;
            }
        }
        // --tag (AND: every tag in spec.tags must appear in m.tags)
        for required_tag in &spec.tags {
            if !m.tags.iter().any(|t| t.eq_ignore_ascii_case(required_tag)) {
                return false;
            }
        }
        true
    });

    iter.take(spec.limit).collect()
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_bundle(
        session_id: &str,
        created_at: &str,
        model: &str,
        token_count: u64,
        tags: &[&str],
    ) -> BundleMeta {
        BundleMeta {
            session_id: session_id.into(),
            created_at: created_at.into(),
            model: model.into(),
            token_count,
            message_count: 1,
            user_turn_count: 0,
            duration_ms: 0,
            tags: tags.iter().map(|s| s.to_string()).collect(),
        }
    }

    fn corpus() -> Vec<BundleMeta> {
        vec![
            make_bundle("s1", "2024-01-01T00:00:00Z", "claude-3-sonnet", 500, &["rust"]),
            make_bundle("s2", "2024-03-15T12:00:00Z", "gpt-4", 1500, &["python", "ml"]),
            make_bundle("s3", "2024-06-01T00:00:00Z", "claude-3-opus", 3000, &["rust", "ml"]),
            make_bundle("s4", "2024-09-20T08:00:00Z", "gemini-pro", 200, &[]),
            make_bundle("s5", "2025-01-01T00:00:00Z", "claude-3-5-sonnet", 8000, &["perf"]),
        ]
    }

    #[test]
    fn no_filters_returns_all_up_to_default_limit() {
        let bundles = corpus();
        let spec = FilterSpec::new(); // limit=50
        let result = apply_filters(&bundles, &spec);
        assert_eq!(result.len(), 5);
    }

    #[test]
    fn since_excludes_earlier_bundles() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.since = Some("2024-06-01".into());
        let result = apply_filters(&bundles, &spec);
        // s3 (2024-06-01), s4 (2024-09-20), s5 (2025-01-01)
        assert_eq!(result.len(), 3);
        assert!(result.iter().any(|m| m.session_id == "s3"));
        assert!(result.iter().any(|m| m.session_id == "s5"));
    }

    #[test]
    fn until_excludes_later_bundles() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.until = Some("2024-03-15".into());
        let result = apply_filters(&bundles, &spec);
        // s1 (2024-01-01) and s2 (2024-03-15)
        assert_eq!(result.len(), 2);
        assert!(result.iter().any(|m| m.session_id == "s1"));
        assert!(result.iter().any(|m| m.session_id == "s2"));
    }

    #[test]
    fn since_and_until_narrows_window() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.since = Some("2024-03-01".into());
        spec.until = Some("2024-07-01".into());
        let result = apply_filters(&bundles, &spec);
        // s2 (2024-03-15) and s3 (2024-06-01)
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn model_substring_match_is_case_insensitive() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.model = Some("CLAUDE".into());
        let result = apply_filters(&bundles, &spec);
        // s1, s3, s5
        assert_eq!(result.len(), 3);
    }

    #[test]
    fn model_no_match_returns_empty() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.model = Some("llama".into());
        let result = apply_filters(&bundles, &spec);
        assert!(result.is_empty());
    }

    #[test]
    fn min_tokens_filters_low_count() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.min_tokens = Some(1000);
        let result = apply_filters(&bundles, &spec);
        // s2 (1500), s3 (3000), s5 (8000)
        assert_eq!(result.len(), 3);
        assert!(result.iter().all(|m| m.token_count >= 1000));
    }

    #[test]
    fn single_tag_filter() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.tags = vec!["rust".into()];
        let result = apply_filters(&bundles, &spec);
        // s1, s3
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn multiple_tags_and_logic() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.tags = vec!["rust".into(), "ml".into()];
        let result = apply_filters(&bundles, &spec);
        // only s3 has both rust AND ml
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].session_id, "s3");
    }

    #[test]
    fn limit_truncates_results() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.limit = 2;
        let result = apply_filters(&bundles, &spec);
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn combined_model_and_min_tokens() {
        let bundles = corpus();
        let mut spec = FilterSpec::new();
        spec.model = Some("claude".into());
        spec.min_tokens = Some(1000);
        let result = apply_filters(&bundles, &spec);
        // s3 (claude-3-opus, 3000), s5 (claude-3-5-sonnet, 8000)
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn empty_corpus_returns_empty() {
        let bundles: Vec<BundleMeta> = vec![];
        let spec = FilterSpec::new();
        let result = apply_filters(&bundles, &spec);
        assert!(result.is_empty());
    }
}
