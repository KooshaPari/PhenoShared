//! Local export adapters for hosted chat products.
//!
//! These adapters intentionally read user-provided export files only. They do
//! not automate browsers, access cookies, or scrape authenticated sessions.

use std::path::PathBuf;

use crate::{
    domain::session::{Corpus, Session},
    ingestion::json_source::{JsonCorpusSource, JsonIngestionReport},
    ports::{CorpusSource, PortError},
};

macro_rules! export_source {
    ($name:ident, $corpus:expr, $doc:literal) => {
        #[doc = $doc]
        #[derive(Debug, Clone)]
        pub struct $name {
            source: JsonCorpusSource,
        }
        impl $name {
            /// Create an export adapter rooted at a file or directory.
            #[must_use]
            pub fn new(path: impl Into<PathBuf>) -> Self {
                Self { source: JsonCorpusSource::new(path, $corpus) }
            }
            /// Load one normalized session and its ingestion report.
            ///
            /// # Errors
            ///
            /// Returns a [`PortError`] when the source cannot be opened or parsed.
            pub fn load_with_report(
                &self,
                id: &str,
            ) -> Result<(Session, JsonIngestionReport), PortError> {
                self.source.load_with_report(id)
            }
        }
        impl CorpusSource for $name {
            fn list(&self) -> Result<Vec<String>, PortError> {
                self.source.list()
            }
            fn load(&self, id: &str) -> Result<Session, PortError> {
                self.source.load(id)
            }
        }
    };
}

export_source!(ChatGptExport, Corpus::ChatGptWeb, "`ChatGPT` data-export JSON files.");
export_source!(ClaudeExport, Corpus::ClaudeWeb, "Claude data-export JSON files.");
export_source!(GeminiExport, Corpus::GeminiWeb, "Gemini data-export JSON files.");

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::Role;

    fn export_fixture() -> tempfile::NamedTempFile {
        let file = tempfile::Builder::new().suffix(".json").tempfile().unwrap();
        std::fs::write(
            file.path(),
            serde_json::json!({
                "conversation_id": "web-1",
                "title": "Export",
                "mapping": {
                    "a": {"message": {"author": {"role": "user"}, "content": {"parts": ["hello"]}}},
                    "b": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["hi"]}}}
                }
            })
            .to_string(),
        )
        .unwrap();
        file
    }

    #[test]
    fn chatgpt_export_mapping_is_normalized() {
        let file = export_fixture();
        let source = ChatGptExport::new(file.path());
        let id = source.list().unwrap().remove(0);
        let session = source.load(&id).unwrap();
        assert_eq!(session.corpus, Corpus::ChatGptWeb);
        assert_eq!(session.messages.len(), 2);
        assert_eq!(session.messages[0].role, Role::User);
    }

    #[test]
    fn claude_export_loads_report_and_corpus() {
        let file = export_fixture();
        let source = ClaudeExport::new(file.path());
        let id = source.list().unwrap().remove(0);
        let (session, report) = source.load_with_report(&id).unwrap();
        assert_eq!(session.corpus, Corpus::ClaudeWeb);
        assert_eq!(session.messages.len(), 2);
        assert_eq!(report.ingested, 1);
        assert!(report.is_clean());
    }

    #[test]
    fn gemini_export_loads_and_rejects_unknown_id() {
        let file = export_fixture();
        let source = GeminiExport::new(file.path());
        let id = source.list().unwrap().remove(0);
        let session = source.load(&id).unwrap();
        assert_eq!(session.corpus, Corpus::GeminiWeb);
        assert!(matches!(
            source.load("missing.json"),
            Err(PortError::NotFound(id)) if id == "missing.json"
        ));
    }
}
