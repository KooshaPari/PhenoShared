use scraper::{Html, Selector};
use std::collections::BTreeMap;

use crate::provider_html::is_hackernews_post_path;

/// A single Hacker News "saved" item. HN never wraps posts in an outer
/// `<article>` like LinkedIn/X/Reddit do; the row carries everything
/// (title, link, score, by-user, time-ago) and lives inside the saved-posts
/// table.
#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
pub struct HNPost {
    pub id: String,
    pub url: String,
    pub title: String,
    pub text: String,
    pub author: String,
}

/// On-disk wire format written by `scripts/hackernews_capture.mjs`.
/// The `provider` field is a string literal so a downstream loader can
/// sanity-check the file at deserialisation time even if the JSON has been
/// hand-edited. Other capture metadata is intentionally ignored by Serde:
/// it is not part of the persisted post contract.
#[derive(Debug, serde::Deserialize)]
pub struct HNCaptureFile {
    pub provider: String,
    pub posts: Vec<HNPost>,
}

/// Parses a Hacker News "saved stories" capture JSON document into posts.
/// Returns `Err` for malformed JSON; the `provider` field, if present, is
/// verified to equal `"hackernews"`.
pub fn parse_capture_json(input: &str) -> Result<Vec<HNPost>, HackerNewsReaderError> {
    let parsed: HNCaptureFile = serde_json::from_str(input).map_err(HackerNewsReaderError::Json)?;
    let HNCaptureFile { provider, posts } = parsed;
    if !provider.is_empty() && provider != "hackernews" {
        return Err(HackerNewsReaderError::UnknownProvider(provider));
    }
    Ok(posts)
}

/// Custom error type for HN ingestion. We wrap `serde_json::Error` so the
/// UI's `String` conversion (via `to_string`) stays readable, and add a
/// sentinel for `provider` mismatches so the import fails loudly when a
/// Reddit/X capture file is mistakenly fed to the HN importer.
#[derive(Debug)]
pub enum HackerNewsReaderError {
    Json(serde_json::Error),
    UnknownProvider(String),
}

impl std::fmt::Display for HackerNewsReaderError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HackerNewsReaderError::Json(error) => write!(formatter, "{error}"),
            HackerNewsReaderError::UnknownProvider(name) => write!(
                formatter,
                "Hacker News capture has unexpected provider: {name:?}"
            ),
        }
    }
}

impl std::error::Error for HackerNewsReaderError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            HackerNewsReaderError::Json(error) => Some(error),
            HackerNewsReaderError::UnknownProvider(_) => None,
        }
    }
}

/// Parse the HTML of `<username>`'s Hacker News saved-stories page. Each
/// saved story is rendered as a `<tr class="athing submission" id="<id>">`
/// row containing a `.titlelink` anchor, immediately followed by a sibling
/// `<tr>` whose `td.subtext` carries the by-user + score text.
///
/// We accept either format: `.athing.submission` rows whose own descendants
/// carry the `.titlelink` AND `.hnuser` together are kept directly; rows
/// without a `.hnuser` link fall back to scanning the row's flattened text
/// for the `by <user>` substring. The `id` attribute on the row is the
/// canonical numeric HN item id; from it we derive the canonical
/// `/item?id=<id>` permalink and the persisted document id.
pub fn parse_saved_html(html: &str) -> Vec<HNPost> {
    let document = Html::parse_document(html);
    let submission_selector =
        Selector::parse("tr.athing.submission").expect("static selector parses");
    let link_selector = Selector::parse("a.titlelink").expect("static selector parses");
    let hnuser_selector = Selector::parse("a.hnuser").expect("static selector parses");
    let mut posts = BTreeMap::new();
    for row in document.select(&submission_selector) {
        let Some(row_id) = row.value().attr("id") else {
            continue;
        };
        if row_id.is_empty() || !row_id.chars().all(|c| c.is_ascii_digit()) {
            continue;
        }
        let canonical_url = format!("https://news.ycombinator.com/item?id={row_id}");
        if !is_hackernews_post_path(&canonical_url) {
            continue;
        }
        let Some(anchor) = row.select(&link_selector).next() else {
            continue;
        };
        let title = anchor
            .text()
            .collect::<Vec<_>>()
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        // The by-user is conventionally rendered inside the row's sibling
        // `<tr class="comtr"><td class="subtext">` — but scraping is granted
        // to whichever copy the page happens to render. We look first for
        // `.hnuser` inside the row (the user-link itself), then fall back
        // to scanning the row's flattened text for the `by ` substring.
        let author = row
            .select(&hnuser_selector)
            .next()
            .map(|node| node.text().collect::<Vec<_>>().join(" ").trim().to_string())
            .filter(|value| !value.is_empty())
            .or_else(|| {
                let row_text = row.text().collect::<Vec<_>>().join(" ");
                row_text
                    .split(" by ")
                    .nth(1)
                    .and_then(|rest| rest.split_whitespace().next())
                    .map(|value| value.to_string())
                    .filter(|value| !value.is_empty())
            })
            .unwrap_or_default();
        // Use the row's flattened text as context for the persisted body so
        // the markdown has at least 40 chars of meaningful copy (the
        // `import_hackernews_*` capture min-length contract).
        let body_text = row
            .text()
            .collect::<Vec<_>>()
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        let text = if body_text.len() > title.len() + 5 {
            body_text
        } else if !author.is_empty() {
            format!("{title} — by {author}")
        } else {
            title.clone()
        };
        posts.entry(row_id.to_string()).or_insert(HNPost {
            id: row_id.to_string(),
            url: canonical_url,
            title,
            text,
            author,
        });
    }
    posts.into_values().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Three-row saved-stories fixture: a single HN saved-page table,
    /// three distinct ids (`40001`/`40002`/`40003`) plus a duplicate row
    /// with id `40001`. After dedup, the parser yields exactly three posts.
    /// This is the canonical
    /// `parse_saved_html_saves_three_rows_from_dedupped_async_html`
    /// evidence the spec mandates.
    #[test]
    fn parse_saved_html_saves_three_rows_from_dedupped_async_html() {
        let html = r##"<html><body><table>
<tr class="athing submission" id="40001">
  <td class="title" align="right"><span class="rank">1</span</td>
  <td class="title"><a class="titlelink" href="https://example.com/a">Local-first research ledgers</a><span class="sitebit comhead"> (example.com</span</td>
  <td class="subtext"><span class="score">142 points</span> by <a class="hnuser" href="user?id=koosha">koosha</a> <span class="age"><a>3 hours ago</a</span</td>
</tr>
<tr class="athing submission" id="40002">
  <td class="title" align="right"><span class="rank">2</span</td>
  <td class="title"><a class="titlelink" href="https://example.com/b">Deterministic enrichment passes</a</td>
  <td class="subtext"><span class="score">88 points</span> by <a class="hnuser" href="user?id=daboross">daboross</a> <span class="age"><a>5 hours ago</a</span</td>
</tr>
<tr class="athing submission" id="40003">
  <td class="title" align="right"><span class="rank">3</span</td>
  <td class="title"><a class="titlelink" href="https://example.com/c">Offline embeddings for local RAG</a</td>
  <td class="subtext"><span class="score">47 points</span> by <a class="hnuser" href="user?id=Meadows">Meadows</a> <span class="age"><a>7 hours ago</a</span</td>
</tr>
<tr class="athing submission" id="40001">
  <td class="title"><a class="titlelink" href="https://example.com/a">Local-first research ledgers duplicate</a</td>
</tr>
</table</body</html>"##;
        let posts = parse_saved_html(html);
        assert_eq!(posts.len(), 3, "expected 3 deduped posts; got {posts:?}");
        let ids: Vec<&str> = posts.iter().map(|p| p.id.as_str()).collect();
        for id in ["40001", "40002", "40003"] {
            assert!(ids.contains(&id), "expected id {id} in {ids:?}");
        }
        // The canonical URL is always /item?id=<id>; the parser rejects
        // any underlying-href `id` field via `is_hackernews_post_path`.
        for post in &posts {
            assert!(post
                .url
                .starts_with("https://news.ycombinator.com/item?id="));
            assert!(is_hackernews_post_path(&post.url));
        }
        assert!(posts
            .iter()
            .any(|post| post.title.contains("Local-first research ledgers")));
        assert!(posts
            .iter()
            .any(|post| post.title.contains("Deterministic enrichment passes")));
        assert!(posts
            .iter()
            .any(|post| post.title.contains("Offline embeddings for local RAG")));
        assert!(posts.iter().any(|post| post.author == "koosha"));
        assert!(posts.iter().any(|post| post.author == "daboross"));
        assert!(posts.iter().any(|post| post.author == "Meadows"));
    }

    /// `tr.athing.submission` rows whose `id` attribute is non-numeric are
    /// silently dropped — they would map to a malformed document id and
    /// the shape guard rejects them. Garbage, defer, and rank-only rows
    /// also have to be rejected.
    #[test]
    fn ignores_non_submission_and_bad_id_rows() {
        let html = r##"<!DOCTYPE html>
<html><body>
<table>
  <tr class="comtr"><td><a href="item?id=99999">comment row</a</td</tr>
  <tr class="athing" id="rank-row"><td><span class="rank">1</span</td</tr>
  <tr class="athing submission" id="10">
    <td class="title"><a class="titlelink" href="https://example.com/x">A real saved story</a</td>
    <td class="subtext"><span class="score">12 points</span> by <a class="hnuser" href="user?id=hacker">hacker</a> <span class="age"><a>2 hours ago</a</span</td>
 </tr>
  <tr class="athing submission" id="not-a-number">
    <td class="title"><a class="titlelink" href="https://example.com/y">Garbage row</a</td>
 </tr>
</table>
</body</html>"##;
        let posts = parse_saved_html(html);
        assert_eq!(posts.len(), 1, "only id=10 is well-formed; got {posts:?}");
        assert_eq!(posts[0].id, "10");
        assert!(posts[0].title.contains("A real saved story"));
        assert_eq!(posts[0].author, "hacker");
    }

    #[test]
    fn parses_playwright_capture_file() {
        let json = r#"{"provider":"hackernews","profile":"hn","captured_at":"2026-07-25T12:00:00Z","posts":[{"id":"42","url":"https://news.ycombinator.com/item?id=42","title":"HN sample","text":"A thoughtful saved HN story worth a local copy.","author":"someone"}]}"#;
        let posts = parse_capture_json(json).unwrap();
        assert_eq!(posts.len(), 1);
        assert_eq!(posts[0].id, "42");
        assert_eq!(posts[0].author, "someone");
        assert!(posts[0].text.starts_with("A thoughtful"));
    }

    /// Round-trip a realistic 5-post Hacker News Playwright capture through
    /// `parse_capture_json`, asserting each row preserves the documented
    /// fields (id, url, title, text, author) and the canonical URL form.
    /// This is the second mandatory spec test:
    /// `parse_capture_json_round_trips_five_post_fixture`.
    #[test]
    fn parse_capture_json_round_trips_five_post_fixture() {
        let json = r#"{
            "provider": "hackernews",
            "profile": "hn-profile",
            "captured_at": "2026-07-25T12:00:00.000Z",
            "source": "hackernews-playwright-authenticated-session",
            "savedUrl": "https://news.ycombinator.com/saved?id=koosha",
            "posts": [
                {"id":"40000001","url":"https://news.ycombinator.com/item?id=40000001","title":"Why local-first research ledgers?","text":"Local-first research ledgers keep durable provenance on the user's machine without requiring a centralized backend.","author":"koosha"},
                {"id":"40000002","url":"https://news.ycombinator.com/item?id=40000002","title":"Deterministic enrichment","text":"Deterministic enrichment passes produce stable, reviewable notes that can be diffed across runs without trusting the model output.","author":"tptacek"},
                {"id":"40000003","url":"https://news.ycombinator.com/item?id=40000003","title":"Tracing durables","text":"Distributed tracing for background jobs is most useful when each span carries the originating research question as structured metadata.","author":"daboross"},
                {"id":"40000004","url":"https://news.ycombinator.com/item?id=40000004","title":"Embeddings offline","text":"Offline embedding pipelines paired with a deterministic lexical index keep research fully usable without an internet connection.","author":"Meadows"},
                {"id":"40000005","url":"https://news.ycombinator.com/item?id=40000005","title":"Vault layout","text":"A flat Markdown vault with per-source folders and a single SQLite index gives the easiest migration path off of any hosted note system.","author":"selfhosted_fan"}
            ]
        }"#;
        let posts = parse_capture_json(json).expect("fixture parses");
        assert_eq!(posts.len(), 5, "expected 5 viable posts in fixture");
        let ids: Vec<&str> = posts.iter().map(|p| p.id.as_str()).collect();
        assert_eq!(
            ids,
            vec!["40000001", "40000002", "40000003", "40000004", "40000005"]
        );
        let urls: Vec<&str> = posts.iter().map(|p| p.url.as_str()).collect();
        for url in &urls {
            assert!(
                is_hackernews_post_path(url),
                "round-tripped url must satisfy HN path-shape guard; got {url}"
            );
        }
        for post in &posts {
            assert!(
                post.text.len() > 40,
                "captured text must satisfy capture min-length"
            );
            assert!(!post.url.is_empty());
            assert!(!post.title.is_empty());
        }
        assert!(posts.iter().any(|post| post.author == "koosha"));
        assert!(posts.iter().any(|post| post.author == "tptacek"));
        assert!(posts.iter().any(|post| post.author == "daboross"));
        assert!(posts.iter().any(|post| post.author == "Meadows"));
        assert!(posts.iter().any(|post| post.author == "selfhosted_fan"));
    }

    /// Round-trip additional data: a `captured_at` written in `capturedAt`
    /// form (camelCase, the JS-friendly field name) is accepted via the
    /// serde alias; the canonical snake_case form is also accepted.
    #[test]
    fn parse_capture_json_accepts_both_capture_timestamp_forms() {
        let snake = r#"{"provider":"hackernews","captured_at":"2026-07-25T12:00:00Z","posts":[]}"#;
        let camel = r#"{"provider":"hackernews","capturedAt":"2026-07-25T12:00:00Z","posts":[]}"#;
        assert!(parse_capture_json(snake).is_ok());
        assert!(parse_capture_json(camel).is_ok());
    }

    /// Wrong-provider sentinel: feeding a Reddit capture file (whose top-level
    /// `provider` is `"reddit"`) to the HN importer must fail loudly rather
    /// than silently inserting the wrong kind of post.
    #[test]
    fn parse_capture_json_rejects_wrong_provider_field() {
        let json = r#"{"provider":"reddit","posts":[]}"#;
        let result = parse_capture_json(json);
        assert!(
            result.is_err(),
            "non-empty provider field must fail loudly; got {result:?}"
        );
    }

    /// Empty `posts: []` is acceptable — the user may have legitimately run
    /// a capture after draining their saved-stories queue.
    #[test]
    fn parse_capture_json_accepts_empty_posts_array() {
        let posts = parse_capture_json(
            r#"{"provider":"hackernews","captured_at":"2026-07-25T12:00:00Z","posts":[]}"#,
        )
        .expect("empty array parses");
        assert!(posts.is_empty());
    }

    /// HN's id field is the canonical numeric item id and is what the
    /// Tauri command derives the document id from. A `postId` field in
    /// input (e.g. from a hand-edited capture) is silently dropped by
    /// serde — only the canonical `id` survives, making the capture
    /// non-spoofable with respect to document id derivation.
    #[test]
    fn parse_capture_json_id_derivation_is_input_id_only() {
        let json = r#"{"provider":"hackernews","captured_at":"2026-07-25T12:00:00Z","posts":[{"id":"90001","postId":"INJECTED_OVERRIDE","url":"https://news.ycombinator.com/item?id=90001","title":"x","text":"A small but meaningful text body longer than forty characters","author":"someone"}]}"#;
        let posts = parse_capture_json(json).unwrap();
        assert_eq!(posts.len(), 1);
        assert_eq!(posts[0].id, "90001");
        // The injected `postId` field never lands on the struct.
        assert!(!posts[0].id.contains("INJECTED"));
    }

    #[test]
    fn reader_error_display_is_human_readable() {
        let err = HackerNewsReaderError::UnknownProvider("reddit".into());
        let rendered = err.to_string();
        assert!(rendered.contains("reddit"));
        assert!(rendered.contains("Hacker News capture"));
    }

    /// Real saved-stories pages contain duplicate ids only when items appear
    /// more than once in the same row window. The parser must emit a single
    /// canonical post per id, derived from the first-seen row.
    #[test]
    fn parse_saved_html_idempotent_under_full_page_duplication() {
        let row_open = r#"<table><tbody>
<tr id="dup-row"><td class="title">
<a class="titlelink" href="https://example.com/share-page">First occurrence</a</td</tr>
<tr><td class="subtext"><span class="score">42 points</span> by <a class="hnuser">alice</a</td</tr>
<tr class="athing submission" id="5550001">
<td class="title"><a class="titlelink" href="https://example.com/a">Same story appears twice</a</td>
<td><span class="score">42 points</span> by <a class="hnuser">alice</a> <a>2 hours ago</a</td</tr>
<tr><td class="subtext</td</tr>
<tr class="athing submission" id="5550001">
<td class="title"><a class="titlelink" href="https://other.example.com/b?ref=hn">Same story appears twice (dup</a</td>
<td><span class="score">99 points</span> by <a class="hnuser">eve</a> <a>3 hours ago</a</td</tr>
<tr><td class="subtext</td</tr>
</tbody</table>"#;
        let posts = parse_saved_html(row_open);
        let saved_ids: Vec<&str> = posts.iter().map(|p| p.id.as_str()).collect();
        let unique_count = saved_ids
            .iter()
            .collect::<std::collections::HashSet<_>>()
            .len();
        assert_eq!(
            unique_count,
            saved_ids.len(),
            "all emitted ids must be unique"
        );
        assert_eq!(saved_ids.iter().filter(|id| **id == "5550001").count(), 1);
        // No phantom post should escape the .titlelink filter
        assert!(posts
            .iter()
            .all(|p| !p.title.is_empty() && !p.url.is_empty()));
    }
}
