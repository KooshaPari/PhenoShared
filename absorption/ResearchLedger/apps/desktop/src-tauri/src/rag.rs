use crate::storage::SearchResult;
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Citation {
    pub citation_id: String,
    pub document_id: String,
    pub title: String,
    pub source_uri: Option<String>,
    pub snippet: String,
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RetrievalCoverage {
    /// Results that contributed to the answer context.
    pub retrieved: u32,
    /// Citation records emitted alongside the answer context.
    pub cited: u32,
    /// Citations that retain an original source URI.
    pub with_source_uri: u32,
    /// Fraction of emitted citations with a source URI, in `[0, 1]`.
    pub source_uri_ratio: f32,
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RetrievalConfidence {
    /// Deterministic evidence-coverage signal, not a factual-truth probability.
    pub score: f32,
    pub label: String,
    pub rationale: String,
}

#[derive(Debug, Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RetrievalContext {
    pub query: String,
    pub context: String,
    pub citations: Vec<Citation>,
    pub coverage: RetrievalCoverage,
    pub confidence: RetrievalConfidence,
}

#[derive(Debug, Clone)]
pub struct VectorHit {
    pub document_id: String,
    pub score: f32,
    pub result: Option<SearchResult>,
}

/// Reciprocal-rank fusion seam for a future local/cloud vector provider.
/// Lexical FTS5 remains authoritative when no vector hits are supplied.
pub fn fuse_ranked(
    lexical: Vec<SearchResult>,
    vector: Vec<VectorHit>,
    limit: usize,
) -> Vec<SearchResult> {
    let mut scores: HashMap<String, (f32, SearchResult)> = HashMap::new();
    for (rank, result) in lexical.into_iter().enumerate() {
        let score = 1.0 / (60.0 + rank as f32 + 1.0);
        scores
            .entry(result.document_id.clone())
            .or_insert((0.0, result))
            .0 += score;
    }
    for (rank, hit) in vector.into_iter().enumerate() {
        let contribution = hit.score.max(0.0) / (60.0 + rank as f32 + 1.0);
        if let Some((score, _)) = scores.get_mut(&hit.document_id) {
            *score += contribution;
        } else if let Some(result) = hit.result {
            scores.insert(hit.document_id, (contribution, result));
        }
    }
    let mut ranked = scores.into_values().collect::<Vec<_>>();
    ranked.sort_by(|left, right| {
        right
            .0
            .total_cmp(&left.0)
            .then_with(|| left.1.document_id.cmp(&right.1.document_id))
    });
    ranked
        .into_iter()
        .take(limit)
        .map(|(_, result)| result)
        .collect()
}

pub fn build_context(query: &str, results: Vec<SearchResult>) -> RetrievalContext {
    let citations = results
        .into_iter()
        .enumerate()
        .map(|(index, result)| Citation {
            citation_id: (index + 1).to_string(),
            document_id: result.document_id,
            title: result.title,
            source_uri: result.source_uri,
            snippet: result.snippet,
        })
        .collect::<Vec<_>>();
    let context = citations
        .iter()
        .map(|citation| {
            format!(
                "[{}] {}\n{}",
                citation.citation_id, citation.title, citation.snippet
            )
        })
        .collect::<Vec<_>>()
        .join("\n\n");
    let coverage = coverage(&citations);
    RetrievalContext {
        query: query.into(),
        context,
        citations,
        confidence: confidence(&coverage),
        coverage,
    }
}

fn coverage(citations: &[Citation]) -> RetrievalCoverage {
    let cited = citations.len() as u32;
    let with_source_uri = citations
        .iter()
        .filter(|citation| {
            citation
                .source_uri
                .as_deref()
                .is_some_and(|uri| !uri.trim().is_empty())
        })
        .count() as u32;
    RetrievalCoverage {
        retrieved: cited,
        cited,
        with_source_uri,
        source_uri_ratio: if cited == 0 {
            0.0
        } else {
            with_source_uri as f32 / cited as f32
        },
    }
}

fn confidence(coverage: &RetrievalCoverage) -> RetrievalConfidence {
    // Two cited results are enough to reach the provenance coverage ceiling. This avoids
    // reporting high confidence from a single, even if fully attributed, result.
    let result_depth = (coverage.cited as f32 / 2.0).min(1.0);
    let score = coverage.source_uri_ratio * result_depth;
    let label = if score >= 0.75 {
        "supported"
    } else if score > 0.0 {
        "limited"
    } else {
        "insufficient"
    };
    RetrievalConfidence {
        score,
        label: label.into(),
        rationale: format!(
            "{}/{} cited results retain source URIs; score is source coverage capped by two-result depth.",
            coverage.with_source_uri, coverage.cited
        ),
    }
}

/// Deterministic reranker fallback used when no local cross-encoder is configured.
/// It rewards query-token overlap in the title and snippet while preserving the
/// fused order for ties, so retrieval remains explainable and offline-safe.
pub fn rerank(query: &str, results: Vec<SearchResult>) -> Vec<SearchResult> {
    let tokens = normalized_tokens(query);
    let mut ranked = results
        .into_iter()
        .enumerate()
        .map(|(index, result)| {
            let haystack = normalized_tokens(&format!("{} {}", result.title, result.snippet));
            let score = tokens.intersection(&haystack).count();
            (score, index, result)
        })
        .collect::<Vec<_>>();
    ranked.sort_by(|left, right| right.0.cmp(&left.0).then(left.1.cmp(&right.1)));
    ranked.into_iter().map(|(_, _, result)| result).collect()
}

fn normalized_tokens(value: &str) -> HashSet<String> {
    value
        .split(|character: char| !character.is_alphanumeric())
        .map(|token| {
            token
                .chars()
                .flat_map(char::to_lowercase)
                .collect::<String>()
        })
        .filter(|token| token.chars().count() > 2)
        .collect()
}

/// Applies verified cross-encoder scores and appends any unscored candidates in their fused
/// order. The latter keeps partial provider responses deterministic and citation-safe.
pub fn rerank_with_cross_encoder(
    results: Vec<SearchResult>,
    scores: Vec<crate::embeddings::CrossEncoderScore>,
) -> Vec<SearchResult> {
    let mut score_by_index = HashMap::new();
    for score in scores {
        score_by_index.insert(score.index, score.relevance_score);
    }
    let mut ranked = results
        .into_iter()
        .enumerate()
        .map(|(index, result)| (score_by_index.get(&index).copied(), index, result))
        .collect::<Vec<_>>();
    ranked.sort_by(|left, right| match (left.0, right.0) {
        (Some(left_score), Some(right_score)) => right_score
            .total_cmp(&left_score)
            .then(left.1.cmp(&right.1)),
        (Some(_), None) => std::cmp::Ordering::Less,
        (None, Some(_)) => std::cmp::Ordering::Greater,
        (None, None) => left.1.cmp(&right.1),
    });
    ranked.into_iter().map(|(_, _, result)| result).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn context_keeps_citations_aligned_with_snippets() {
        let bundle = build_context(
            "agents",
            vec![SearchResult {
                document_id: "github:octo/agents".into(),
                title: "Agents".into(),
                source_uri: Some("https://github.com/octo/agents".into()),
                snippet: "agent workflow".into(),
            }],
        );
        assert!(bundle.context.contains("[1] Agents"));
        assert_eq!(bundle.citations[0].citation_id, "1");
        assert_eq!(
            bundle.citations[0].source_uri.as_deref(),
            Some("https://github.com/octo/agents")
        );
        assert_eq!(bundle.coverage.retrieved, 1);
        assert_eq!(bundle.coverage.cited, 1);
        assert_eq!(bundle.coverage.with_source_uri, 1);
        assert_eq!(bundle.confidence.label, "limited");
        assert_eq!(bundle.confidence.score, 0.5);
    }

    #[test]
    fn context_reports_missing_source_coverage_without_overstating_confidence() {
        let bundle = build_context(
            "agents",
            vec![
                SearchResult {
                    document_id: "with-source".into(),
                    title: "With source".into(),
                    source_uri: Some("https://example.com/source".into()),
                    snippet: "cited evidence".into(),
                },
                SearchResult {
                    document_id: "without-source".into(),
                    title: "Without source".into(),
                    source_uri: None,
                    snippet: "local note".into(),
                },
            ],
        );

        assert_eq!(bundle.coverage.retrieved, 2);
        assert_eq!(bundle.coverage.cited, 2);
        assert_eq!(bundle.coverage.with_source_uri, 1);
        assert_eq!(bundle.coverage.source_uri_ratio, 0.5);
        assert_eq!(bundle.confidence.label, "limited");
        assert_eq!(bundle.confidence.score, 0.5);
    }

    #[test]
    fn lexical_results_remain_available_without_vectors() {
        let result = SearchResult {
            document_id: "doc".into(),
            title: "Doc".into(),
            source_uri: None,
            snippet: "text".into(),
        };
        assert_eq!(fuse_ranked(vec![result], vec![], 10).len(), 1);
    }

    #[test]
    fn vector_only_results_are_not_dropped() {
        let result = SearchResult {
            document_id: "vector-doc".into(),
            title: "Vector doc".into(),
            source_uri: None,
            snippet: "semantic match".into(),
        };
        let hits = vec![VectorHit {
            document_id: result.document_id.clone(),
            score: 0.9,
            result: Some(result),
        }];
        assert_eq!(fuse_ranked(vec![], hits, 10)[0].document_id, "vector-doc");
    }

    #[test]
    fn deterministic_reranker_preserves_ties() {
        let first = SearchResult {
            document_id: "first".into(),
            title: "Agents and ledgers".into(),
            source_uri: None,
            snippet: "local research".into(),
        };
        let second = SearchResult {
            document_id: "second".into(),
            title: "Agents other note".into(),
            source_uri: None,
            snippet: "unrelated".into(),
        };
        let ranked = rerank("agents", vec![second, first]);
        assert_eq!(
            ranked
                .iter()
                .map(|result| result.document_id.as_str())
                .collect::<Vec<_>>(),
            vec!["second", "first"]
        );
    }

    #[test]
    fn reranker_matches_complete_tokens_only() {
        let cart = SearchResult {
            document_id: "cart".into(),
            title: "Cart article".into(),
            source_uri: None,
            snippet: "contains artistry as a substring".into(),
        };
        let art = SearchResult {
            document_id: "art".into(),
            title: "Art notes".into(),
            source_uri: None,
            snippet: "exact token".into(),
        };
        let ranked = rerank("art", vec![cart, art]);
        assert_eq!(ranked[0].document_id, "art");
    }

    #[test]
    fn reranker_normalizes_unicode_case_and_character_length() {
        assert!(normalized_tokens("éx").is_empty());
        assert!(normalized_tokens("ÉTUDES").contains("études"));

        let unicode = SearchResult {
            document_id: "unicode".into(),
            title: "ÉTUDES sur les agents".into(),
            source_uri: None,
            snippet: "recherche locale".into(),
        };
        let unrelated = SearchResult {
            document_id: "unrelated".into(),
            title: "Agents".into(),
            source_uri: None,
            snippet: "other material".into(),
        };
        let ranked = rerank("études", vec![unrelated, unicode]);
        assert_eq!(ranked[0].document_id, "unicode");
    }

    #[test]
    fn fused_ties_are_sorted_by_document_id() {
        let result = |document_id: &str| SearchResult {
            document_id: document_id.into(),
            title: document_id.into(),
            source_uri: None,
            snippet: String::new(),
        };
        let ranked = fuse_ranked(
            vec![],
            vec![
                VectorHit {
                    document_id: "b".into(),
                    score: 0.0,
                    result: Some(result("b")),
                },
                VectorHit {
                    document_id: "a".into(),
                    score: 0.0,
                    result: Some(result("a")),
                },
            ],
            10,
        );
        assert_eq!(
            ranked
                .iter()
                .map(|result| result.document_id.as_str())
                .collect::<Vec<_>>(),
            vec!["a", "b"]
        );
    }

    #[test]
    fn cross_encoder_scores_reorder_the_fixture_candidates() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../tests/fixtures/retrieval/cross_encoder_contract.json"
        ))
        .unwrap();
        let scores = crate::embeddings::LocalCrossEncoder::parse_response(
            &fixture["response"].to_string(),
            fixture["documents"].as_array().unwrap().len(),
        )
        .unwrap();
        let results = fixture["documents"]
            .as_array()
            .unwrap()
            .iter()
            .enumerate()
            .map(|(index, document)| SearchResult {
                document_id: index.to_string(),
                title: document.as_str().unwrap().to_string(),
                source_uri: None,
                snippet: document.as_str().unwrap().to_string(),
            })
            .collect();

        let ranked = rerank_with_cross_encoder(results, scores);
        assert_eq!(
            ranked
                .into_iter()
                .map(|result| result.document_id)
                .collect::<Vec<_>>(),
            ["2", "1", "0"]
        );
    }
}
