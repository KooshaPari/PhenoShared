const MAX_CHARS: usize = 1_200;

/// Split a source document into bounded chunks while retaining its latest
/// Markdown heading as retrieval context.
pub fn split_document(content: &str) -> Vec<(Option<String>, String)> {
    let mut chunks = Vec::new();
    let mut heading: Option<String> = None;
    let mut current = String::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if let Some(value) = trimmed.strip_prefix('#') {
            if !current.trim().is_empty() {
                chunks.push((heading.clone(), current.trim().to_string()));
                current.clear();
            }
            heading = Some(value.trim().to_string());
        }
        if trimmed.is_empty() {
            if current.len() > 200 {
                chunks.push((heading.clone(), current.trim().to_string()));
                current.clear();
            }
            continue;
        }

        let mut remaining = line;
        while !remaining.is_empty() {
            let separator = usize::from(!current.is_empty());
            let available = MAX_CHARS.saturating_sub(current.len() + separator);
            let end = utf8_prefix_len(remaining, available);
            if end == 0 {
                chunks.push((heading.clone(), current.trim().to_string()));
                current.clear();
                continue;
            }
            if !current.is_empty() {
                current.push('\n');
            }
            current.push_str(&remaining[..end]);
            remaining = &remaining[end..];
            if !remaining.is_empty() {
                chunks.push((heading.clone(), current.trim().to_string()));
                current.clear();
            }
        }
    }
    if !current.trim().is_empty() {
        chunks.push((heading, current.trim().to_string()));
    }
    if chunks.is_empty() {
        vec![(None, String::new())]
    } else {
        chunks
    }
}

fn utf8_prefix_len(value: &str, max_bytes: usize) -> usize {
    if value.len() <= max_bytes {
        return value.len();
    }
    let mut end = 0;
    for (index, character) in value.char_indices() {
        let candidate = index + character.len_utf8();
        if candidate > max_bytes {
            break;
        }
        end = candidate;
    }
    end
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preserves_heading_context_and_bounds_chunk_size() {
        let content = format!("# Intro\n{}\n\n# Next\nsecond", "a".repeat(1_300));
        let chunks = split_document(&content);
        assert!(chunks.len() >= 2);
        assert_eq!(chunks[0].0.as_deref(), Some("Intro"));
        assert!(chunks.iter().all(|(_, text)| text.len() <= MAX_CHARS));
    }

    #[test]
    fn preserves_each_heading_for_consecutive_short_sections() {
        let chunks = split_document("# First\none\n# Second\ntwo");
        assert_eq!(chunks.len(), 2);
        assert_eq!(chunks[0].0.as_deref(), Some("First"));
        assert_eq!(chunks[1].0.as_deref(), Some("Second"));
    }

    #[test]
    fn splits_oversized_utf8_lines_at_safe_boundaries() {
        let chunks = split_document(&"é".repeat(1_000));
        assert!(chunks.len() > 1);
        assert!(chunks.iter().all(|(_, text)| text.len() <= MAX_CHARS));
        let rebuilt = chunks
            .iter()
            .map(|(_, text)| text.as_str())
            .collect::<String>();
        assert_eq!(rebuilt.chars().count(), 1_000);
    }

    #[test]
    fn returns_an_empty_chunk_for_empty_documents() {
        assert_eq!(split_document(""), vec![(None, String::new())]);
    }
}
