use crate::{enrichment, storage::SourceDocument};

fn body_lines(content: &str) -> Vec<String> {
    let mut lines = content.lines();
    if lines.next() != Some("---") {
        lines = content.lines();
    } else {
        for line in lines.by_ref() {
            if line == "---" {
                break;
            }
        }
    }

    lines
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with("---") && !line.starts_with('#'))
        .map(|line| line.trim_start_matches(['-', '*', '>']).trim().to_string())
        .filter(|line| !line.is_empty())
        .collect()
}

fn sentences(lines: &[String]) -> Vec<String> {
    lines
        .iter()
        .flat_map(|line| line.split_inclusive(['.', '!', '?']))
        .map(str::trim)
        .filter(|sentence| sentence.len() >= 20)
        .map(ToOwned::to_owned)
        .collect()
}

fn first_sentence(lines: &[String]) -> String {
    sentences(lines)
        .into_iter()
        .next()
        .unwrap_or_else(|| "No summary available.".into())
}

pub fn extract_claims(content: &str) -> Vec<String> {
    sentences(&body_lines(content))
        .into_iter()
        .take(8)
        .collect()
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimEvidence {
    pub claim: String,
    pub quote: String,
    pub start: i64,
    pub end: i64,
}

pub fn extract_claim_evidence(content: &str) -> Vec<ClaimEvidence> {
    let mut search_from = 0;
    extract_claims(content)
        .into_iter()
        .filter_map(|claim| {
            let start = content[search_from..].find(&claim)? + search_from;
            let end = start + claim.len();
            search_from = end;
            Some(ClaimEvidence {
                quote: claim.clone(),
                claim,
                start: start as i64,
                end: end as i64,
            })
        })
        .collect()
}

fn bullet_list(items: &[String], empty: &str) -> String {
    if items.is_empty() {
        format!("- {empty}")
    } else {
        items
            .iter()
            .map(|item| format!("- {item} [1]"))
            .collect::<Vec<_>>()
            .join("\n")
    }
}

fn yaml_scalar(value: &str) -> String {
    serde_json::to_string(value).unwrap_or_else(|_| "\"\"".into())
}

pub fn render_deterministic(document: &SourceDocument) -> String {
    let lines = body_lines(&document.content);
    let all_sentences = sentences(&lines);
    let summary = first_sentence(&lines);
    let claims = extract_claims(&document.content);
    let definitions = all_sentences
        .iter()
        .filter(|sentence| {
            let lower = sentence.to_ascii_lowercase();
            lower.contains(" is ") || lower.contains(" are ") || lower.contains(" means ")
        })
        .take(8)
        .cloned()
        .collect::<Vec<_>>();
    let alternatives = all_sentences
        .iter()
        .filter(|sentence| {
            let lower = sentence.to_ascii_lowercase();
            lower.contains("alternative")
                || lower.contains("instead")
                || lower.contains(" versus ")
                || lower.contains(" vs ")
        })
        .take(8)
        .cloned()
        .collect::<Vec<_>>();
    let questions = lines
        .iter()
        .filter(|line| {
            let lower = line.to_ascii_lowercase();
            line.ends_with('?') || lower.contains("unknown") || lower.contains("future work")
        })
        .take(8)
        .cloned()
        .collect::<Vec<_>>();
    let links = enrichment::extract_urls(&document.content);
    let references = if links.is_empty() {
        "- No outbound references discovered.".to_string()
    } else {
        links
            .iter()
            .map(|url| format!("- [{}]({})", url, enrichment::canonical_url(url)))
            .collect::<Vec<_>>()
            .join("\n")
    };
    let source = document
        .source_uri
        .as_deref()
        .unwrap_or("urn:researchledger:local");
    format!(
        "---\ntype: \"Distilled Research Note\"\ntitle: {}\ndescription: \"Deterministic structured research extraction\"\nresource: {}\ntags: [distillation, deterministic]\ntimestamp: {}\n---\n\n# Summary\n\n{} [1]\n\n# Claims\n\n{}\n\n# Definitions\n\n{}\n\n# Alternatives\n\n{}\n\n# Open Questions\n\n{}\n\n# Discovered References\n\n{}\n\n# Source\n\n[Original source]({})\n\n# Citations\n\n[1] [Original source]({})\n",
        yaml_scalar(&format!("{} — deterministic distillation", document.title)),
        yaml_scalar(source),
        yaml_scalar(&document.captured_at),
        summary,
        bullet_list(&claims, "No claim-shaped sentences discovered."),
        bullet_list(&definitions, "No definition-shaped sentences discovered."),
        bullet_list(&alternatives, "No alternatives discovered."),
        bullet_list(&questions, "No open questions discovered."),
        references,
        source,
        source,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn document(content: &str) -> SourceDocument {
        SourceDocument {
            id: "x".into(),
            relative_path: "x.md".into(),
            title: "Example: durable research".into(),
            source_kind: "test".into(),
            source_uri: Some("https://example.com/source".into()),
            content: content.into(),
            captured_at: "2026-01-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn renders_structured_claims_and_references() {
        let note = render_deterministic(&document(
            "A durable ledger is local and reviewable. The alternative is a hosted service. What remains unknown? See https://example.com/reference.",
        ));
        assert!(note.contains("# Claims"));
        assert!(note.contains("# Definitions"));
        assert!(note.contains("# Alternatives"));
        assert!(note.contains("# Open Questions"));
        assert!(note.contains("A durable ledger is local and reviewable. [1]"));
        assert!(note.contains("https://example.com/reference"));
        assert!(note.contains("type: \"Distilled Research Note\""));
    }

    #[test]
    fn renders_stable_summary_and_source_citation() {
        let note = render_deterministic(&document("A concise research finding."));
        assert!(note.contains("A concise research finding. [1]"));
        assert!(note.contains("[1] [Original source](https://example.com/source)"));
    }

    #[test]
    fn claim_evidence_has_reproducible_byte_spans() {
        let content = "Intro. A durable ledger is local and reviewable. Another finding follows.";
        let evidence = extract_claim_evidence(content);
        assert_eq!(evidence.len(), 2);
        assert_eq!(
            &content[evidence[0].start as usize..evidence[0].end as usize],
            evidence[0].quote
        );
        assert_eq!(
            evidence[0].start,
            content.find(&evidence[0].claim).unwrap() as i64
        );
        assert!(evidence[0].end <= evidence[1].start);
    }

    #[test]
    fn claims_exclude_yaml_frontmatter() {
        let claims = extract_claims(
            "---\ntitle: A frontmatter sentence that must not become distilled research evidence.\ntype: Research Note\n---\nA durable ledger is local and reviewable.",
        );

        assert_eq!(claims, vec!["A durable ledger is local and reviewable."]);
    }
}
