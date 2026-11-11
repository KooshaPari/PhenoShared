//! Shared HTML parsing primitives for the third-party-provider connectors
//! (LinkedIn, Reddit, X, Hacker News). Both the per-provider parsers and tests reuse these
//! helpers to keep dedup-by-canonical-URL logic consistent and to avoid
//! copy-pasted boilerplate across modules.

use scraper::{element_ref::ElementRef, ElementRef as ScraperElementRef};

/// Regex-free shape check: does `cleaned` look like a Reddit post permalink
/// (`/r/<sub>/comments/<id>`), and not a user profile or comment activity URL?
///
/// Rejects:
/// * user profile comments (`/user/<name>/comments/...`)
/// * trailing-slash-only or empty ids (`/comments/`)
/// * anything not under `/r/...`
pub fn is_reddit_post_path(cleaned: &str) -> bool {
    // Strip query/fragment just in case (clean_post_href already strips these
    // but we re-check defensively).
    let path = cleaned
        .split('?')
        .next()
        .unwrap_or(cleaned)
        .split('#')
        .next()
        .unwrap_or(cleaned);
    // A path-shaped URL from another origin must not be attributed to Reddit.
    let after_r = match path
        .strip_prefix("https://www.reddit.com/r/")
        .or_else(|| path.strip_prefix("https://old.reddit.com/r/"))
    {
        Some(rest) => rest,
        None => return false,
    };
    // Must not be `/user/...` masquerading. We already matched `/r/` so this
    // is defensive.
    if after_r.starts_with("user/") {
        return false;
    }
    // Split `/r/<sub>/comments/<id>` and validate pieces.
    let mut parts = after_r.split('/');
    let subreddit = parts.next().unwrap_or("");
    let comments_marker = parts.next().unwrap_or("");
    let id = parts.next().unwrap_or("");
    if subreddit.is_empty()
        || comments_marker != "comments"
        || id.is_empty()
        || !id.chars().all(|c| c.is_ascii_alphanumeric())
    {
        return false;
    }
    true
}

/// Regex-free shape check: does `cleaned` look like a Hacker News item
/// permalink (`/item?id=<numeric-id>`), and not a section listing, login
/// screen, or thread aggregator?
///
/// Rejects:
/// * any path that is not literally `/item`
/// * `/item?id=<non-numeric>` (e.g. `abc`, `12abc`)
/// * `/threads?id=...` and the section listings (`/news`, `/best`, `/show`,
///   `/ask`, `/newcomments`, `/submit`, `/login`, `/about`, `/items`)
/// * the bare homepage `/`
pub fn is_hackernews_post_path(cleaned: &str) -> bool {
    // Strip query/fragment defensively (clean_post_href already strips these
    // but we re-check so the guard accepts either form).
    let path = cleaned
        .split('?')
        .next()
        .unwrap_or(cleaned)
        .split('#')
        .next()
        .unwrap_or(cleaned);
    // Require absolute HN origin so vaguely-shaped paths under other hosts
    // can't slip through.
    let after_origin = match path.strip_prefix("https://news.ycombinator.com") {
        Some(rest) => rest,
        None => return false,
    };
    // Only exactly `/item` is accepted. (`/items` is HN's bulk export route
    // — explicitly rejected below by the empty-id fallback.)
    if after_origin != "/item" {
        return false;
    }
    // Pull the `id` query parameter. We accept either `?id=12345` or the
    // already-cleaned canonical form `https://news.ycombinator.com/item`
    // (in which case `cleaned` would have stripped the query — and we treat
    // that as malformed).
    let query = cleaned
        .split_once('?')
        .map(|(_, query)| query.split('#').next().unwrap_or(""))
        .unwrap_or("");
    let id = query
        .split('&')
        .find_map(|pair| pair.strip_prefix("id="))
        .unwrap_or("");
    // HN item ids are 1-10 digit ints, occasionally with no upper bound. We
    // accept any all-digit positive id — guarded by the `/item` literal match.
    !id.is_empty() && id.chars().all(|c| c.is_ascii_digit())
}

/// Regex-free shape check: does `cleaned` look like an X post permalink
/// (`/<user>/status/<numeric-id>`), and not a settings page, intent URL, or
/// photo/video URL?
///
/// Rejects:
/// * `/i/status/...` (X photo/video route)
/// * `/intent/...` (share intent)
/// * `/messages/...`, `/compose/...`, `/home`
/// * any path that does not have a numeric id (so usernames like `status` are rejected)
pub fn is_x_post_path(cleaned: &str) -> bool {
    let path = cleaned
        .split('?')
        .next()
        .unwrap_or(cleaned)
        .split('#')
        .next()
        .unwrap_or(cleaned);
    let after_slash = match path.strip_prefix("https://x.com/") {
        Some(rest) => rest,
        None => match path.strip_prefix("http://x.com/") {
            Some(rest) => rest,
            None => return false,
        },
    };
    let mut parts = after_slash.split('/');
    let user = parts.next().unwrap_or("");
    let status_marker = parts.next().unwrap_or("");
    let id = parts.next().unwrap_or("");
    if user.is_empty()
        || user.starts_with("i")
        || user == "intent"
        || user == "messages"
        || user == "compose"
        || user == "home"
        || user == "settings"
    {
        return false;
    }
    if status_marker != "status" || id.is_empty() {
        return false;
    }
    // X status ids are 18-20 digits but we accept anything >= 6 digits to be lenient.
    id.len() >= 6 && id.chars().all(|c| c.is_ascii_digit())
}

/// Normalise a raw `href` extracted from a timeline/saved-posts DOM.
///
/// * strips any query string and trailing slash;
/// * if `must_contain` is non-empty, requires the cleaned href to contain it
///   (e.g. `"/comments/"` or `"/status/"` for Reddit / X);
/// * if the href is relative, prefixes `base_url` (e.g. `"https://www.reddit.com"`).
///
/// Returns `Some(cleaned)` when the cleaned href passes the substring check, else `None`.
pub fn clean_post_href(raw_href: &str, must_contain: &str, base_url: &str) -> Option<String> {
    let cleaned = raw_href
        .split('?')
        .next()
        .unwrap_or(raw_href)
        .trim_end_matches('/');
    if cleaned.is_empty() {
        return None;
    }
    if !must_contain.is_empty() && !cleaned.contains(must_contain) {
        return None;
    }
    if cleaned.starts_with("http://") || cleaned.starts_with("https://") {
        Some(cleaned.to_string())
    } else if cleaned.starts_with('/') {
        Some(format!("{base_url}{cleaned}"))
    } else {
        Some(format!("{base_url}/{cleaned}"))
    }
}

/// Walk ancestors of `link` looking for the closest <article>-like container
/// whose collapsed text falls between `min_len` and `max_len` (inclusive
/// bounds). Whitespace is normalised to single spaces.
pub fn ancestor_text(
    link: ScraperElementRef<'_>,
    min_len: usize,
    max_len: usize,
) -> Option<String> {
    link.ancestors().find_map(|ancestor| {
        let element = ElementRef::wrap(ancestor)?;
        let value = element
            .text()
            .collect::<Vec<_>>()
            .join(" ")
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        (value.len() >= min_len && value.len() <= max_len).then_some(value)
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use scraper::{Html, Selector};

    #[test]
    fn cleans_absolute_and_relative_hrefs() {
        assert_eq!(
            clean_post_href(
                "https://x.com/u/status/123?lang=en",
                "/status/",
                "https://x.com"
            ),
            Some("https://x.com/u/status/123".to_string())
        );
        assert_eq!(
            clean_post_href(
                "/r/rust/comments/abc/hi/",
                "/comments/",
                "https://www.reddit.com"
            ),
            Some("https://www.reddit.com/r/rust/comments/abc/hi".to_string())
        );
        assert_eq!(
            clean_post_href("u/status/9", "/status/", "https://x.com"),
            Some("https://x.com/u/status/9".to_string())
        );
    }

    #[test]
    fn rejects_when_substring_missing() {
        assert!(clean_post_href("https://x.com/about", "/status/", "https://x.com").is_none());
    }

    #[test]
    fn ancestor_text_walks_to_first_qualified_container() {
        // Text inside the <article> should be picked up at min_len ≥ 8
        let html = r#"<html><body><article><h2>Title</h2><p>Long enough body text.</p></article></body></html>"#;
        let doc = Html::parse_document(html);
        let sel = Selector::parse("h2").unwrap();
        let h2 = doc.select(&sel).next().unwrap();
        let txt = ancestor_text(h2, 8, 20_000).unwrap();
        assert!(txt.contains("Title"));
        assert!(txt.contains("Long enough body text."));
    }

    #[test]
    fn ancestor_text_rejects_too_short_or_too_long() {
        let html = r#"<html><body><article><p>hi</p></article></body></html>"#;
        let doc = Html::parse_document(html);
        let sel = Selector::parse("p").unwrap();
        let p = doc.select(&sel).next().unwrap();
        // "hi" has length 2 — below min_len=8
        assert!(ancestor_text(p, 8, 20_000).is_none());
    }

    #[test]
    fn reddit_post_path_accepts_post_permalink() {
        assert!(is_reddit_post_path(
            "https://www.reddit.com/r/rust/comments/abc123/why_local_first"
        ));
        assert!(is_reddit_post_path(
            "https://old.reddit.com/r/rust/comments/abc123"
        ));
    }

    #[test]
    fn reddit_post_path_rejects_user_profiles_and_bad_shapes() {
        // user profile comments — must NOT match
        assert!(!is_reddit_post_path(
            "https://www.reddit.com/user/koosha/comments/abc/def"
        ));
        // path-shaped external URLs must not be attributed to Reddit
        assert!(!is_reddit_post_path(
            "https://evil.example/r/rust/comments/abc123/post"
        ));
        // missing id
        assert!(!is_reddit_post_path(
            "https://www.reddit.com/r/rust/comments/"
        ));
        // not under /r/
        assert!(!is_reddit_post_path("https://www.reddit.com/comments/abc"));
        // /r/<sub>/comments/<id>/<id>/comments/<id> — weird path, but still passes shape
        // We accept this because Reddit allows nested comment replies to be permalinked.
        assert!(is_reddit_post_path(
            "https://www.reddit.com/r/rust/comments/abc/nested/comments/xyz"
        ));
    }

    #[test]
    fn x_post_path_accepts_user_status_permalink() {
        assert!(is_x_post_path(
            "https://x.com/someone/status/1100000000000000001"
        ));
        assert!(is_x_post_path("https://x.com/u/status/1234567"));
    }

    #[test]
    fn x_post_path_rejects_intent_photos_and_settings() {
        assert!(!is_x_post_path("https://x.com/i/status/123"));
        assert!(!is_x_post_path(
            "https://x.com/intent/follow?screen_name=foo"
        ));
        assert!(!is_x_post_path("https://x.com/messages/compose"));
        assert!(!is_x_post_path("https://x.com/compose/post"));
        assert!(!is_x_post_path("https://x.com/home"));
        assert!(!is_x_post_path("https://x.com/settings"));
        // status marker but no numeric id (usernames named "status")
        assert!(!is_x_post_path("https://x.com/someone/status/abc"));
    }

    #[test]
    fn hackernews_post_path_accepts_item_query_pair() {
        // Canonical form: /item with `?id=<digits>`.
        assert!(is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=1"
        ));
        assert!(is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=12345"
        ));
        assert!(is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=42380912"
        ));
        assert!(is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=42380912#comment"
        ));
    }

    #[test]
    fn hackernews_post_path_rejects_listings_logins_and_bad_shapes() {
        // Homepage and section listings.
        assert!(!is_hackernews_post_path("https://news.ycombinator.com/"));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/saved?id=koosha"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/news"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/best"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/show"
        ));
        assert!(!is_hackernews_post_path("https://news.ycombinator.com/ask"));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/newcomments"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/submit"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/login"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/about"
        ));
        // Bulk export shape — must not match.
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/items"
        ));
        // Thread aggregator shape — must not match.
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/threads?id=12345"
        ));
        // /item without any query — drop.
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/item"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/item?"
        ));
        // /item?id=non-numeric — drop.
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=abc"
        ));
        assert!(!is_hackernews_post_path(
            "https://news.ycombinator.com/item?id=12abc"
        ));
        // Wrong origin — drop.
        assert!(!is_hackernews_post_path(
            "https://example.com/item?id=12345"
        ));
    }
}
