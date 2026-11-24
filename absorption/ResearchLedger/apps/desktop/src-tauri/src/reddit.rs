use scraper::{Html, Selector};
use std::collections::BTreeMap;

use crate::provider_html::{ancestor_text, clean_post_href, is_reddit_post_path};

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
pub struct RedditSavedPost {
    pub url: String,
    pub title: String,
    pub text: String,
    pub subreddit: Option<String>,
}

#[derive(Debug, serde::Deserialize)]
pub struct RedditCaptureFile {
    pub posts: Vec<RedditSavedPost>,
}

pub fn parse_capture_json(json: &str) -> Result<Vec<RedditSavedPost>, serde_json::Error> {
    Ok(serde_json::from_str::<RedditCaptureFile>(json)?.posts)
}

/// Parse Reddit's "Saved" page HTML. Reddit renders saved items as anchor tags on
/// post permalinks (`/r/<sub>/comments/<id>/...`). We collect title text from the
/// nearest heading and body text from the closest post container.
pub fn parse_saved_html(html: &str) -> Vec<RedditSavedPost> {
    let document = Html::parse_document(html);
    let link_selector = Selector::parse("a[href*='/comments/']").expect("static selector parses");
    let heading_selector = Selector::parse("h3, h2").expect("static selector parses");
    let mut posts = BTreeMap::new();
    for link in document.select(&link_selector) {
        let Some(raw_href) = link.value().attr("href") else {
            continue;
        };
        let Some(url) = clean_post_href(raw_href, "/comments/", "https://www.reddit.com") else {
            continue;
        };
        if !is_reddit_post_path(&url) {
            continue;
        };
        let title = link
            .ancestors()
            .find_map(|ancestor| {
                let element = scraper::ElementRef::wrap(ancestor)?;
                element.select(&heading_selector).next().map(|node| {
                    node.text()
                        .collect::<Vec<_>>()
                        .join(" ")
                        .split_whitespace()
                        .collect::<Vec<_>>()
                        .join(" ")
                })
            })
            .unwrap_or_default();
        let text = match ancestor_text(link, 40, 20_000) {
            Some(value) if !value.is_empty() => value,
            _ => continue,
        };
        let subreddit = url
            .split("/r/")
            .nth(1)
            .and_then(|rest| rest.split('/').next())
            .map(|value| value.to_string());
        posts.entry(url.clone()).or_insert(RedditSavedPost {
            url,
            title,
            text,
            subreddit,
        });
    }
    posts.into_values().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_unique_post_urls_and_text() {
        let html = r#"<main><article><a href="/r/rust/comments/abc123/why_local_first/">title</a><h3>Why local first?</h3><p>This is a deeply thoughtful post about local-first research ledgers and their tradeoffs.</p></article><a href="/r/rust/comments/abc123/why_local_first/">again</a></main>"#;
        let posts = parse_saved_html(html);
        assert_eq!(posts.len(), 1);
        assert_eq!(
            posts[0].url,
            "https://www.reddit.com/r/rust/comments/abc123/why_local_first"
        );
        assert!(posts[0].text.contains("local-first research ledgers"));
        assert_eq!(posts[0].subreddit.as_deref(), Some("rust"));
    }

    #[test]
    fn rejects_user_comment_activity_urls() {
        // Reddit users have a /user/<name>/comments/ activity feed that ALSO matches
        // /comments/ anchors. The capture path must distinguish post permalinks from
        // user-profile activity.
        let html = r#"<main>
            <article><a href="/user/koosha/comments/abc/why_local_first/">user activity</a><p>noise</p></article>
            <article><a href="/r/rust/comments/abc/why_local_first/">post permalink</a><p>A thoughtful post about local-first research ledgers and the tradeoffs of owning your data.</p></article>
        </main>"#;
        let posts = parse_saved_html(html);
        assert_eq!(
            posts.len(),
            1,
            "user-comment activity must be filtered; got {:?}",
            posts.iter().map(|p| &p.url).collect::<Vec<_>>()
        );
        assert!(posts[0].url.contains("/r/rust/comments/"));
    }

    #[test]
    fn parses_playwright_capture_file() {
        let posts = parse_capture_json(r#"{"version":1,"posts":[{"url":"https://www.reddit.com/r/rust/comments/abc/hi/","title":"hi","text":"A thoughtful saved post about Rust research tooling.","subreddit":"rust"}]}"#).unwrap();
        assert_eq!(posts.len(), 1);
        assert_eq!(posts[0].subreddit.as_deref(), Some("rust"));
        assert!(posts[0].text.starts_with("A thoughtful"));
    }

    /// Round-trip every post in a realistic Playwright capture file through
    /// `parse_capture_json`, asserting each row preserves the documented
    /// fields (`url`, `title`, `text`, `subreddit`). Reproduces the canonical
    /// 5-post fixture used by `src/RedditXSschema.test.ts`.
    #[test]
    fn round_trips_realistic_five_post_capture() {
        let json = r#"{
            "version": 1,
            "capturedAt": "2026-07-25T10:00:00.000Z",
            "source": "reddit-playwright-authenticated-session",
            "savedUrl": "https://www.reddit.com/user/saved",
            "posts": [
                {"subreddit":"rust","postId":"a1b2c3d","slug":"why_local_first","url":"https://www.reddit.com/r/rust/comments/a1b2c3d/why_local_first/","title":"Why local-first?","text":"Local-first research ledgers keep durable provenance on the user's machine without requiring a centralized backend."},
                {"subreddit":"rust","postId":"e4f5g6h","slug":"tracing_pulls","url":"https://www.reddit.com/r/rust/comments/e4f5g6h/tracing_pulls/","title":"Tracing pulls","text":"Distributed tracing for background jobs is most useful when each span carries the originating research question as structured metadata."},
                {"subreddit":"LocalLLaMA","postId":"i7j8k9l","slug":"embeddings_offline","url":"https://www.reddit.com/r/LocalLLaMA/comments/i7j8k9l/embeddings_offline/","title":"Embeddings, offline","text":"Offline embedding pipelines paired with a deterministic lexical index keep research fully usable without an internet connection."},
                {"subreddit":"rust","postId":"m0n1o2p","slug":"deterministic_enrichment","url":"https://www.reddit.com/r/rust/comments/m0n1o2p/deterministic_enrichment/","title":"Deterministic enrichment","text":"Deterministic enrichment passes produce stable, reviewable notes that can be diffed across runs without trusting the model output."},
                {"subreddit":"selfhosted","postId":"q3r4s5t","slug":"vault_layout","url":"https://www.reddit.com/r/selfhosted/comments/q3r4s5t/vault_layout/","title":"Vault layout","text":"A flat Markdown vault with per-source folders and a single SQLite index gives the easiest migration path off of any hosted note system."}
            ]
        }"#;
        let posts = parse_capture_json(json).expect("fixture parses");
        assert_eq!(posts.len(), 5, "expected 5 viable posts in fixture");
        let titles: Vec<&str> = posts.iter().map(|p| p.title.as_str()).collect();
        assert_eq!(
            titles,
            vec![
                "Why local-first?",
                "Tracing pulls",
                "Embeddings, offline",
                "Deterministic enrichment",
                "Vault layout",
            ]
        );
        let subreddits: Vec<Option<&str>> = posts.iter().map(|p| p.subreddit.as_deref()).collect();
        assert_eq!(
            subreddits,
            vec![
                Some("rust"),
                Some("rust"),
                Some("LocalLLaMA"),
                Some("rust"),
                Some("selfhosted"),
            ]
        );
        let urls: Vec<&str> = posts.iter().map(|p| p.url.as_str()).collect();
        assert_eq!(
            urls[0],
            "https://www.reddit.com/r/rust/comments/a1b2c3d/why_local_first/"
        );
        assert!(
            urls.iter()
                .all(|url| crate::provider_html::is_reddit_post_path(url)),
            "all round-tripped urls must satisfy the Reddit post-path shape guard"
        );
        for post in &posts {
            assert!(
                post.text.len() > 40,
                "captured text length must satisfy capture min-length"
            );
            assert!(!post.url.is_empty(), "url must survive capture");
            assert!(!post.title.is_empty(), "title must survive capture");
        }
    }

    /// Reddit path-shape guard: any post whose URL is not under `/r/<sub>/comments/<id>`
    /// must be silently dropped by the persisted document id derivation. We mirror that
    /// here by filtering with `is_reddit_post_path` and asserting the kept post count
    /// equals the number of well-shaped URLs in the input — never more, never less.
    #[test]
    fn reddit_path_shape_guard_drops_malformed_urls() {
        use crate::provider_html::is_reddit_post_path;
        let urls = [
            "https://www.reddit.com/r/rust/comments/abc/well_formed",
            "https://www.reddit.com/user/koosha/comments/abc/not_real_post",
            "https://www.reddit.com/r/rust/comments/",
            "https://www.reddit.com/comments/abc",
            "https://www.reddit.com/r/rust/comments/def/another_well_formed",
        ];
        let kept: Vec<&str> = urls
            .iter()
            .copied()
            .filter(|u| is_reddit_post_path(u))
            .collect();
        assert_eq!(
            kept.len(),
            2,
            "only /r/<sub>/comments/<id> posts survive; got {kept:?}"
        );
        assert!(kept.contains(&"https://www.reddit.com/r/rust/comments/abc/well_formed"));
        assert!(kept.contains(&"https://www.reddit.com/r/rust/comments/def/another_well_formed"));
        assert_eq!(urls.iter().filter(|u| is_reddit_post_path(u)).count(), 2);
    }

    /// `parse_capture_json` returns `Err` (and the import is abandoned) when the
    /// top-level `posts` field is missing. This mirrors the user-visible
    /// "Reddit refused the capture" error path. The reddit.rs schema doesn't
    /// require a top-level `provider` field (the provider is fixed by which
    /// script emitted the file), so the only structural failure surface is a
    /// malformed `posts` array.
    #[test]
    fn reddit_capture_rejects_missing_posts_field() {
        let result = parse_capture_json(r#"{"version":1,"capturedAt":"2026-07-25T10:00:00Z"}"#);
        assert!(
            result.is_err(),
            "missing posts array must fail loudly; got {result:?}"
        );
    }

    /// Empty `posts: []` is a valid capture (zero rows). We do NOT collapse
    /// this to an error because the user may legitimately re-run a capture
    /// after the bookmarks queue is drained.
    #[test]
    fn reddit_capture_accepts_empty_posts_array() {
        let posts = parse_capture_json(r#"{"version":1,"posts":[]}"#).expect("empty posts parses");
        assert!(posts.is_empty(), "empty array must yield zero rows");
    }

    /// The document id is derived from the captured URL — never trusted from
    /// input. The production schema derives stable ids from the captured URL.
    /// uses `post.url.rsplit(':').next().unwrap_or(&post.url)`. A capture JSON that
    /// includes an attacker-controlled `id` field must NOT carry that id through
    /// `parse_capture_json` — only the canonical id derived from the URL remains.
    #[test]
    fn reddit_id_derivation_is_url_only_not_input() {
        // Rust's serde silently ignores unknown fields by default for a typed struct.
        // This test asserts that even when an attacker injects an `id` field with
        // confusing content, it never shows up in `RedditSavedPost` (the struct has
        // no `id` field). Only the URL survives — and that's what downstream id
        // derivation uses.
        let benign = r#"{"posts":[{"url":"https://www.reddit.com/r/rust/comments/abc/post/","title":"t","text":"a thoughtful text body longer than forty chars","subreddit":"rust"}]}"#;
        let poisoned = r#"{"posts":[{"url":"https://www.reddit.com/r/rust/comments/abc/post/","title":"t","text":"a thoughtful text body longer than forty chars","subreddit":"rust","id":"attacker-controlled-INJECTION"}]}"#;
        let benign_posts = parse_capture_json(benign).unwrap();
        let poisoned_posts = parse_capture_json(poisoned).unwrap();
        assert_eq!(benign_posts.len(), 1);
        assert_eq!(poisoned_posts.len(), 1);
        // Url is the only field that determines downstream id derivation; both
        // parses produce the same canonical URL and therefore the same id.
        assert_eq!(benign_posts[0].url, poisoned_posts[0].url);
        // The poisoned `id` field never appears as a struct field.
        assert!(!poisoned_posts[0].url.contains("INJECTION"));
    }
}
