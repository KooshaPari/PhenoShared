use std::collections::BTreeSet;

pub fn extract_urls(content: &str) -> Vec<String> {
    let mut urls = BTreeSet::new();
    let normalized = content.replace("](", " ");
    for token in normalized.split_whitespace() {
        let candidate = token
            .trim_matches(|character: char| "(<\"'`".contains(character))
            .trim_end_matches(|character: char| ".,;:!?)]}>\"'`".contains(character));
        if candidate.starts_with("https://") || candidate.starts_with("http://") {
            urls.insert(candidate.to_string());
        }
    }
    urls.into_iter().collect()
}

pub fn canonical_url(url: &str) -> String {
    url.split('#')
        .next()
        .unwrap_or(url)
        .trim_end_matches('/')
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn extracts_sorted_deduplicated_urls() {
        assert_eq!(
            extract_urls("See https://b.example/x and https://a.example/y. https://b.example/x"),
            vec!["https://a.example/y", "https://b.example/x"]
        );
    }
    #[test]
    fn canonicalizes_fragment_and_trailing_slash() {
        assert_eq!(
            canonical_url("https://example.com/x/#section"),
            "https://example.com/x"
        );
    }
}
