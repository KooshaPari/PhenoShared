use scraper::{Html, Selector};
use std::collections::BTreeMap;

use crate::provider_html::{ancestor_text, clean_post_href, is_x_post_path};

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize, serde::Serialize)]
pub struct XSavedPost {
    pub url: String,
    pub author: String,
    pub text: String,
}

#[derive(Debug, serde::Deserialize)]
pub struct XCaptureFile {
    pub posts: Vec<XSavedPost>,
}

pub fn parse_capture_json(json: &str) -> Result<Vec<XSavedPost>, serde_json::Error> {
    Ok(serde_json::from_str::<XCaptureFile>(json)?.posts)
}

/// Parse the X "Bookmarks" page. Each bookmark in the modern X timeline is an
/// anchor with an `/status/<id>` permalink. We collect author handle from the
/// nearest `@user` text and body from the closest article container.
pub fn parse_bookmarks_html(html: &str) -> Vec<XSavedPost> {
    let document = Html::parse_document(html);
    let status_selector = Selector::parse("a[href*='/status/']").expect("static selector parses");
    let mut posts = BTreeMap::new();
    for link in document.select(&status_selector) {
        let Some(raw_href) = link.value().attr("href") else {
            continue;
        };
        let Some(url) = clean_post_href(raw_href, "/status/", "https://x.com") else {
            continue;
        };
        if !is_x_post_path(&url) {
            continue;
        }
        let text = match ancestor_text(link, 40, 20_000) {
            Some(value) if !value.is_empty() => value,
            _ => continue,
        };
        let author = text
            .split('@')
            .nth(1)
            .and_then(|rest| {
                rest.chars()
                    .take_while(|character| character.is_alphanumeric() || *character == '_')
                    .collect::<String>()
                    .into()
            })
            .unwrap_or_default();
        posts
            .entry(url.clone())
            .or_insert(XSavedPost { url, author, text });
    }
    posts.into_values().collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extracts_unique_status_urls_and_text() {
        let html = r#"<article><a href="/someone/status/1100000000000000001">permalink</a><div><span>@someone</span><p>This is a thoughtful bookmark about Rust research ledgers and durable provenance.</p></div></article><a href="/someone/status/1100000000000000001">again</a></article>"#;
        let posts = parse_bookmarks_html(html);
        assert_eq!(posts.len(), 1);
        assert_eq!(
            posts[0].url,
            "https://x.com/someone/status/1100000000000000001"
        );
        assert_eq!(posts[0].author, "someone");
        assert!(posts[0].text.contains("durable provenance"));
    }

    #[test]
    fn parses_playwright_capture_file() {
        let posts = parse_capture_json(r#"{"version":1,"posts":[{"url":"https://x.com/someone/status/42","author":"someone","text":"A thoughtful bookmark about local-first research tooling and provenance."}]}"#).unwrap();
        assert_eq!(posts.len(), 1);
        assert_eq!(posts[0].author, "someone");
        assert!(posts[0].text.starts_with("A thoughtful"));
    }

    /// Round-trip every post in a realistic X bookmarks capture file through
    /// `parse_capture_json`, asserting each row preserves the documented
    /// fields (`url`, `author`, `text`). Reproduces the canonical 5-post
    /// fixture used by `src/RedditXSschema.test.ts`.
    #[test]
    fn round_trips_realistic_five_post_capture() {
        let json = r#"{
            "version": 1,
            "capturedAt": "2026-07-25T11:00:00.000Z",
            "source": "x-playwright-authenticated-session",
            "bookmarksUrl": "https://x.com/i/bookmarks",
            "posts": [
                {"user":"koosha","statusId":"1234567890","url":"https://x.com/koosha/status/1234567890","author":"@koosha","text":"A long thread about local-first provenance graphs and how each bookmark can stay durably linked to the source URL it was captured from."},
                {"user":"daboross","statusId":"1234567891","url":"https://x.com/daboross/status/1234567891","author":"@daboross","text":"Rust async trait ergonomics keep improving; pin projects now use full dyn-safety without losing async fn in trait returns for the long term."},
                {"user":"Meadows","statusId":"1234567892","url":"https://x.com/Meadows/status/1234567892","author":"@Meadows","text":"Deterministic enrichment passes produce stable, reviewable notes that can be diffed across runs without trusting the model output."},
                {"user":"polyglot_otter","statusId":"1234567893","url":"https://x.com/polyglot_otter/status/1234567893","author":"@polyglot_otter","text":"A Markdown vault with per-source folders plus a single SQLite index is the easiest migration path off of any hosted note system across devices."},
                {"user":"koosha","statusId":"1234567894","url":"https://x.com/koosha/status/1234567894","author":"@koosha","text":"Offline embedding pipelines paired with deterministic lexical index keep research fully usable without any internet connection at capture time."}
            ]
        }"#;
        let posts = parse_capture_json(json).expect("fixture parses");
        assert_eq!(posts.len(), 5, "expected 5 viable posts in fixture");
        let urls: Vec<&str> = posts.iter().map(|p| p.url.as_str()).collect();
        assert_eq!(
            urls,
            vec![
                "https://x.com/koosha/status/1234567890",
                "https://x.com/daboross/status/1234567891",
                "https://x.com/Meadows/status/1234567892",
                "https://x.com/polyglot_otter/status/1234567893",
                "https://x.com/koosha/status/1234567894",
            ]
        );
        let authors: Vec<&str> = posts.iter().map(|p| p.author.as_str()).collect();
        assert_eq!(
            authors,
            vec![
                "@koosha",
                "@daboross",
                "@Meadows",
                "@polyglot_otter",
                "@koosha",
            ]
        );
        for post in &posts {
            assert!(
                post.text.len() > 40,
                "captured text must satisfy capture min-length"
            );
            assert!(
                crate::provider_html::is_x_post_path(&post.url),
                "all round-tripped urls must satisfy the X post-path shape guard"
            );
        }
        // No post should be authored "intent", "i", "messages", "compose", "home", "settings".
        for post in &posts {
            let user = post
                .url
                .trim_start_matches("https://x.com/")
                .split('/')
                .next()
                .unwrap_or("");
            assert!(
                user != "intent"
                    && user != "i"
                    && user != "messages"
                    && user != "compose"
                    && user != "home"
                    && user != "settings",
                "no permalink under an excluded route should round-trip; got {}",
                post.url
            );
        }
    }

    /// X path-shape guard: posts whose URL is not under `/<user>/status/<numeric-id>`
    /// are silently dropped from the captured set (and therefore never get a
    /// document id). The dropped urls are not fatal — the rest of the capture
    /// proceeds. We assert exactly the well-formed items survive.
    #[test]
    fn x_path_shape_guard_drops_malformed_permalinks() {
        use crate::provider_html::is_x_post_path;
        let urls = vec![
            "https://x.com/koosha/status/1234567890",         // good
            "https://x.com/i/status/1234567890",              // photo route — drop
            "https://x.com/intent/follow?screen_name=foo",    // intent — drop
            "https://x.com/messages/1234-5678",               // DM — drop
            "https://x.com/compose/post",                     // compose — drop
            "https://x.com/home",                             // home — drop
            "https://x.com/settings",                         // settings — drop
            "https://x.com/someone/status/notanumber",        // non-numeric id — drop
            "https://x.com/koosha/status/1234567891/photo/1", // good (extra path segments ok)
        ];
        let kept: Vec<&str> = urls.iter().copied().filter(|u| is_x_post_path(u)).collect();
        assert_eq!(
            kept.len(),
            2,
            "only /<user>/status/<numeric-id> survive; got {kept:?}"
        );
        assert!(kept.contains(&"https://x.com/koosha/status/1234567890"));
        assert!(kept.contains(&"https://x.com/koosha/status/1234567891/photo/1"));
    }

    /// `parse_capture_json` returns `Err` (and the import is abandoned) when
    /// the top-level `posts` field is missing. This mirrors the user-visible
    /// "X refused the capture" error path.
    #[test]
    fn x_capture_rejects_missing_posts_field() {
        let result = parse_capture_json(r#"{"version":1,"capturedAt":"2026-07-25T11:00:00Z"}"#);
        assert!(
            result.is_err(),
            "missing posts array must fail loudly; got {result:?}"
        );
    }

    /// Empty `posts: []` is a valid capture (zero rows). We do NOT collapse
    /// this to an error because the user may legitimately re-run after draining
    /// the bookmarks queue.
    #[test]
    fn x_capture_accepts_empty_posts_array() {
        let posts = parse_capture_json(r#"{"version":1,"posts":[]}"#).expect("empty posts parses");
        assert!(posts.is_empty(), "empty array must yield zero rows");
    }

    /// The X post URL is the only field that determines the downstream
    /// document id. An attacker-controlled `id` field in the captured JSON
    /// must NOT carry through `parse_capture_json` — `XSavedPost` has no
    /// `id` field, only the URL survives.
    #[test]
    fn x_id_derivation_is_url_only_not_input() {
        let benign = r#"{"posts":[{"url":"https://x.com/koosha/status/1234567890","author":"@koosha","text":"a thoughtful body with more than forty characters of useful prose"}]}"#;
        let poisoned = r#"{"posts":[{"url":"https://x.com/koosha/status/1234567890","author":"@koosha","text":"a thoughtful body with more than forty characters of useful prose","id":"TOTALLY_FAKE_INJECTION"}]}"#;
        let benign_posts = parse_capture_json(benign).unwrap();
        let poisoned_posts = parse_capture_json(poisoned).unwrap();
        assert_eq!(benign_posts.len(), 1);
        assert_eq!(poisoned_posts.len(), 1);
        // The URL (and therefore the downstream id) is identical regardless of input `id` field.
        assert_eq!(benign_posts[0].url, poisoned_posts[0].url);
        assert!(!poisoned_posts[0].url.contains("INJECTION"));
        assert!(!poisoned_posts[0].author.contains("INJECTION"));
        assert!(!poisoned_posts[0].text.contains("INJECTION"));
    }

    #[test]
    fn rejects_non_status_permalink_shapes() {
        // /i/status/... is X-internal share format — not a real permalink.
        let html = r#"<article><a href="/i/status/1100000000000000099">share</a><div><span>@someone</span><p>noise that looks like a real post but isn't a permalink anchor.</p></div></article>"#;
        let posts = parse_bookmarks_html(html);
        assert!(posts.is_empty(), "expected zero posts; got {posts:?}");

        // /intent/... (web intent URLs) must be filtered out.
        let html = r#"<article><a href="/intent/like?tweet_id=1100000000000000099">like</a><div><span>@someone</span><p>intent URL noise that must not slip into the bookmarks vault.</p></div></article>"#;
        let posts = parse_bookmarks_html(html);
        assert!(posts.is_empty());

        // /messages/... is a DM thread, not a bookmarked post.
        let html = r#"<article><a href="/messages/1234-5678">DM</a><div><span>@someone</span><p>DM thread noise that must not slip into the bookmarks vault.</p></div></article>"#;
        let posts = parse_bookmarks_html(html);
        assert!(posts.is_empty());
    }
}
