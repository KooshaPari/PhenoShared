// Rust tooling binary for checking broken links in VitePress docs.
// Reason: Rust default per Phenotype scripting hierarchy; standalone tool.

use anyhow::Result;
use pulldown_cmark::{Event, Parser};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Debug, Clone)]
struct LinkRef {
    path: String,
    line: usize,
}

/// Returns true for URLs that should be skipped (absolute URLs and anchor-only links).
fn is_skip_url(url: &str) -> bool {
    url.starts_with("http://") || url.starts_with("https://") || url.starts_with('#')
}

/// Strips the `#fragment` portion from a URL, returning the path component only.
fn strip_anchor(url: &str) -> &str {
    url.split('#').next().unwrap_or(url)
}

/// Given a base directory and a link target, generates the candidate paths to check.
/// Tries: raw path, path with `.md` extension, and `index.md` inside path as directory.
fn resolve_candidates(base_dir: &Path, link: &str) -> Vec<PathBuf> {
    let mut target = base_dir.to_path_buf();
    target.push(link);
    vec![
        target.clone(),
        {
            let mut p = target.clone();
            p.set_extension("md");
            p
        },
        {
            let mut p = target.clone();
            if p.is_file() {
                p.pop();
            }
            p.push("index.md");
            p
        },
    ]
}

#[cfg(test)]
/// Extracts all link URLs from a markdown string.
fn extract_links_from_markdown(content: &str) -> Vec<String> {
    let parser = Parser::new(content);
    let mut links = Vec::new();
    for event in parser {
        if let Event::Start(pulldown_cmark::Tag::Link { dest_url: url, .. }) = event {
            links.push(url.to_string());
        }
    }
    links
}

fn main() -> Result<()> {
    let docs_root = PathBuf::from("docs-site");

    if !docs_root.exists() {
        eprintln!("Error: docs-site directory not found");
        std::process::exit(1);
    }

    let mut broken_links: HashMap<String, Vec<LinkRef>> = HashMap::new();
    let mut total_links = 0;
    let mut checked_paths = std::collections::HashSet::new();

    // Walk all markdown files (skip node_modules)
    for entry in WalkDir::new(&docs_root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            !e.path()
                .components()
                .any(|c| c.as_os_str() == "node_modules")
        })
        .filter(|e| e.path().extension().and_then(|s| s.to_str()) == Some("md"))
    {
        let file_path = entry.path().to_path_buf();
        let content = match std::fs::read_to_string(&file_path) {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Failed to read {}: {}", file_path.display(), e);
                continue;
            }
        };

        let parser = Parser::new(&content);
        let mut line_num = 1;

        for event in parser {
            // Count newlines for approximate line tracking
            if let Event::Text(text) = &event {
                line_num += text.matches('\n').count();
            }

            if let Event::Start(pulldown_cmark::Tag::Link { dest_url: url, .. }) = &event {
                let url_str = url.to_string();
                total_links += 1;

                if is_skip_url(&url_str) {
                    continue;
                }

                // Check relative links
                let base_dir = file_path
                    .parent()
                    .unwrap_or_else(|| Path::new("."))
                    .to_path_buf();
                let link_without_anchor = strip_anchor(&url_str);

                if !link_without_anchor.is_empty() && link_without_anchor != "/" {
                    let candidates = resolve_candidates(&base_dir, link_without_anchor);

                    let mut exists = false;
                    for candidate in &candidates {
                        if candidate.exists() {
                            exists = true;
                            checked_paths.insert(candidate.clone());
                            break;
                        }
                    }

                    if !exists {
                        let rel_path = file_path.strip_prefix(&docs_root).unwrap_or(&file_path);
                        broken_links
                            .entry(url_str.clone())
                            .or_default()
                            .push(LinkRef {
                                path: rel_path.display().to_string(),
                                line: line_num,
                            });
                    }
                }
            }
        }
    }

    // Report results
    println!("\n=== Doc Link Check Report ===");
    println!("Total links scanned: {}", total_links);
    println!("Paths checked: {}", checked_paths.len());
    println!("Broken links found: {}\n", broken_links.len());

    if !broken_links.is_empty() {
        for (link, refs) in broken_links.iter() {
            println!("Broken: {}", link);
            for r in refs {
                println!("  └─ {}:{}", r.path, r.line);
            }
        }
        std::process::exit(1);
    } else {
        println!("✓ All links are valid");
        std::process::exit(0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    // ── is_skip_url ──────────────────────────────────────────────────────────

    #[test]
    fn skip_url_http() {
        assert!(is_skip_url("http://example.com/page"));
    }

    #[test]
    fn skip_url_https() {
        assert!(is_skip_url("https://docs.rs/anyhow"));
    }

    #[test]
    fn skip_url_anchor_only() {
        assert!(is_skip_url("#section-header"));
    }

    #[test]
    fn skip_url_relative_not_skipped() {
        assert!(!is_skip_url("../guide/intro.md"));
        assert!(!is_skip_url("./sibling.md"));
        assert!(!is_skip_url("subdir/page"));
    }

    // ── strip_anchor ─────────────────────────────────────────────────────────

    #[test]
    fn strip_anchor_with_fragment() {
        assert_eq!(strip_anchor("page.md#heading"), "page.md");
    }

    #[test]
    fn strip_anchor_no_fragment() {
        assert_eq!(strip_anchor("page.md"), "page.md");
    }

    #[test]
    fn strip_anchor_empty_fragment() {
        assert_eq!(strip_anchor("page.md#"), "page.md");
    }

    // ── extract_links_from_markdown ───────────────────────────────────────────

    #[test]
    fn extract_links_happy_path() {
        let md = "See [the guide](guide.md) and [the API](api/index.md).";
        let links = extract_links_from_markdown(md);
        assert_eq!(links.len(), 2);
        assert!(links.contains(&"guide.md".to_string()));
        assert!(links.contains(&"api/index.md".to_string()));
    }

    #[test]
    fn extract_links_mixed_absolute_and_relative() {
        let md = "[home](/) [ext](https://example.com) [rel](./page.md)";
        let links = extract_links_from_markdown(md);
        assert_eq!(links.len(), 3);
        assert!(links.contains(&"https://example.com".to_string()));
        assert!(links.contains(&"./page.md".to_string()));
    }

    #[test]
    fn extract_links_no_links() {
        let links = extract_links_from_markdown("Just plain text with **bold** and _italic_.");
        assert!(links.is_empty());
    }

    // ── resolve_candidates ────────────────────────────────────────────────────

    #[test]
    fn resolve_candidates_produces_three_paths() {
        let base = Path::new("/docs");
        let candidates = resolve_candidates(base, "guide/intro");
        assert_eq!(candidates.len(), 3);
        // raw
        assert_eq!(candidates[0], PathBuf::from("/docs/guide/intro"));
        // with .md
        assert_eq!(candidates[1], PathBuf::from("/docs/guide/intro.md"));
        // index.md (intro is not a file, so stays as-is + index.md)
        assert_eq!(candidates[2], PathBuf::from("/docs/guide/intro/index.md"));
    }

    #[test]
    fn resolve_candidates_existing_md_file_found() -> Result<(), Box<dyn std::error::Error>> {
        let dir = TempDir::new()?;
        let target = dir.path().join("page.md");
        fs::write(&target, "# Page")?;

        let candidates = resolve_candidates(dir.path(), "page");
        // candidates[1] should be page.md which exists
        assert!(candidates[1].exists(), "expected page.md to be found");
        Ok(())
    }

    #[test]
    fn resolve_candidates_index_md_found() -> Result<(), Box<dyn std::error::Error>> {
        let dir = TempDir::new()?;
        let subdir = dir.path().join("guide");
        fs::create_dir(&subdir)?;
        fs::write(subdir.join("index.md"), "# Guide")?;

        let candidates = resolve_candidates(dir.path(), "guide");
        // candidates[2] == dir/guide/index.md
        assert!(
            candidates[2].exists(),
            "expected guide/index.md to be found"
        );
        Ok(())
    }
}
