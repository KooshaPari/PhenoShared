//! Daemon-backed source for web viewer sessions.

use session_ledger::{
    domain::session::{Corpus, Message, Role, Session},
    validate_okf_document, OkfDocument,
};

use crate::daemon_url::daemon_api_url;

/// Return the bounded daemon endpoint used for the viewer's initial bundle load.
///
/// Full OKF documents can be large on a real local corpus. The daemon keeps
/// unparameterized listing available for compatibility, while the interactive
/// viewer requests a bounded first page.
pub fn daemon_bundle_url() -> String {
    daemon_api_url("/api/bundles?limit=100")
}

/// Fetch and project the viewer's bounded initial page from the local daemon.
#[cfg(any(feature = "desktop", feature = "web"))]
pub async fn fetch_daemon_sessions() -> Result<Vec<Session>, String> {
    let response = reqwest::Client::new()
        .get(daemon_bundle_url())
        .send()
        .await
        .map_err(|error| format!("daemon not reachable: {error}"))?;

    if !response.status().is_success() {
        return Err(format!("daemon returned {}", response.status()));
    }

    let body =
        response.text().await.map_err(|error| format!("failed to read daemon bundles: {error}"))?;
    parse_daemon_bundles(&body)
}

/// Parse the `GET /api/bundles` response into the viewer's shared session model.
pub fn parse_daemon_bundles(body: &str) -> Result<Vec<Session>, String> {
    let documents: Vec<serde_json::Value> = serde_json::from_str(body)
        .map_err(|error| format!("failed to parse daemon bundles: {error}"))?;

    let document_count = documents.len();
    let sessions = documents
        .into_iter()
        .filter_map(|document| serde_json::from_value::<OkfDocument>(document).ok())
        .filter_map(|document| session_from_okf(document).ok())
        .collect::<Vec<_>>();

    if document_count > 0 && sessions.is_empty() {
        return Err("failed to parse daemon bundles: no valid sessions".to_owned());
    }

    Ok(sessions)
}

fn session_from_okf(document: OkfDocument) -> Result<Session, String> {
    if !validate_okf_document(&document).is_empty() {
        return Err(format!("failed to parse daemon bundles: invalid OKF {}", document.source_id));
    }

    let corpus = corpus_from_okf(&document.provenance.corpus)?;
    let cwd = entity_property(&document, "resource", "cwd");
    let title = entity_property(&document, "state", "title");
    let messages = document
        .entities
        .iter()
        .filter(|entity| entity.r#type == "intent" && !entity.label.trim().is_empty())
        .map(|entity| Message::new(Role::User, entity.label.clone()))
        .collect();

    Ok(Session { id: document.source_id, corpus, cwd, title, messages })
}

fn entity_property(document: &OkfDocument, entity_type: &str, property: &str) -> Option<String> {
    document
        .entities
        .iter()
        .find(|entity| entity.r#type == entity_type)
        .and_then(|entity| entity.properties.get(property))
        .and_then(serde_json::Value::as_str)
        .map(str::to_owned)
}

fn corpus_from_okf(corpus: &str) -> Result<Corpus, String> {
    match corpus {
        "forge" => Ok(Corpus::Forge),
        "codex" => Ok(Corpus::Codex),
        "claude-code" => Ok(Corpus::ClaudeCode),
        "cursor" => Ok(Corpus::Cursor),
        "factory-droid" => Ok(Corpus::FactoryDroid),
        "chatgpt-web" => Ok(Corpus::ChatGptWeb),
        "claude-web" => Ok(Corpus::ClaudeWeb),
        "gemini-web" => Ok(Corpus::GeminiWeb),
        other => Err(format!("failed to parse daemon bundles: unsupported corpus {other:?}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::session::Corpus;

    #[test]
    fn parses_daemon_documents_into_sessions() {
        let sessions = parse_daemon_bundles(
            r#"[{"okf":"1.0","source_id":"fuzz-a","entities":[{"id":"intent-0","type":"intent","label":"ship it","properties":null},{"id":"resource-1","type":"resource","label":"working-directory","properties":{"cwd":"/tmp/demo"}}],"provenance":{"corpus":"forge","source_id":"fuzz-a"},"tags":[]}]"#,
        )
        .expect("valid daemon document");

        assert_eq!(sessions[0].id, "fuzz-a");
        assert_eq!(sessions[0].corpus, Corpus::Forge);
        assert_eq!(sessions[0].cwd.as_deref(), Some("/tmp/demo"));
        assert_eq!(sessions[0].messages[0].content, "ship it");
    }

    #[test]
    fn rejects_invalid_okf_response_without_mock_fallback() {
        let error = parse_daemon_bundles("not a JSON array")
            .expect_err("a non-JSON daemon response is rejected");

        assert!(error.contains("failed to parse daemon bundles"));
    }

    #[test]
    fn rejects_nonempty_response_without_valid_sessions() {
        let error = parse_daemon_bundles(r#"[{"okf":"2.0"}]"#)
            .expect_err("an entirely invalid daemon response must not look empty");

        assert!(error.contains("no valid sessions"));
    }

    #[test]
    fn preserves_valid_sessions_when_response_contains_invalid_documents() {
        let sessions = parse_daemon_bundles(
            r#"[
                {"okf":"1.0","source_id":"fuzz-a","entities":[],"provenance":{"corpus":"forge","source_id":"fuzz-a"},"tags":[]},
                {"okf":"2.0"}
            ]"#,
        )
        .expect("a malformed bundle must not hide valid daemon bundles");

        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, "fuzz-a");
    }

    #[test]
    fn daemon_bundle_url_requests_a_bounded_initial_page() {
        assert_eq!(daemon_bundle_url(), "http://127.0.0.1:8080/api/bundles?limit=100");
    }
}
