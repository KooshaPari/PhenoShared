//! URL routing for the inbox daemon HTTP server.

/// A parsed HTTP route.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Route {
    Health,
    Index,
    InboxForm,
    Answer,
    Done,
    Static(String),
    NotFound,
    Shutdown,
}

/// Parse the URL path into a `(Route, optional_id)` pair.
pub(crate) fn parse_route(target: &str) -> (Route, Option<String>) {
    let path = target.split('?').next().unwrap_or(target).trim_end_matches('/');
    if path == "/health" || path == "/ping" {
        return (Route::Health, None);
    }
    if path == "/shutdown" {
        return (Route::Shutdown, None);
    }
    if path.is_empty() {
        return (Route::Index, None);
    }
    if path == "/inbox" {
        return (Route::Index, None);
    }
    if let Some(rest) = path.strip_prefix("/inbox/") {
        if let Some(rid) = rest.strip_suffix("/answer") {
            return (Route::Answer, Some(rid.to_string()));
        }
        if let Some(rid) = rest.strip_suffix("/done") {
            return (Route::Done, Some(rid.to_string()));
        }
        return (Route::InboxForm, Some(rest.to_string()));
    }
    if let Some(rest) = path.strip_prefix("/answer/") {
        return (Route::Answer, Some(rest.to_string()));
    }
    if let Some(rest) = path.strip_prefix("/static/") {
        return (Route::Static(rest.to_string()), None);
    }
    (Route::NotFound, None)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_route() {
        assert_eq!(parse_route("/health"), (Route::Health, None));
        assert_eq!(parse_route("/ping"), (Route::Health, None));
    }

    #[test]
    fn index_route() {
        assert_eq!(parse_route(""), (Route::Index, None));
        assert_eq!(parse_route("/inbox"), (Route::Index, None));
    }

    #[test]
    fn inbox_form_route() {
        let (route, id) = parse_route("/inbox/abc123");
        assert_eq!(route, Route::InboxForm);
        assert_eq!(id.as_deref(), Some("abc123"));
    }

    #[test]
    fn answer_route() {
        let (route, id) = parse_route("/inbox/abc123/answer");
        assert_eq!(route, Route::Answer);
        assert_eq!(id.as_deref(), Some("abc123"));
    }

    #[test]
    fn done_route() {
        let (route, id) = parse_route("/inbox/abc123/done");
        assert_eq!(route, Route::Done);
        assert_eq!(id.as_deref(), Some("abc123"));
    }

    #[test]
    fn static_route() {
        let (route, _) = parse_route("/static/index.css");
        assert_eq!(route, Route::Static("index.css".into()));
    }

    #[test]
    fn not_found_route() {
        assert_eq!(parse_route("/nope"), (Route::NotFound, None));
    }

    #[test]
    fn shutdown_route() {
        assert_eq!(parse_route("/shutdown"), (Route::Shutdown, None));
    }
}
