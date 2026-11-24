//! Compiler for a reproducible duplicate-session manifest.

use crate::distill::token_estimator::TokenEstimator;
use crate::domain::bundle::{Bundle, BundleKind};
use crate::domain::dedup::{DedupKey, DedupMember};
use crate::domain::session::Session;

/// Validation failures when compiling sessions into one dedup scope.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum DedupCompileError {
    #[error("at least one session is required")]
    EmptySessions,
    #[error("topic slug must not be empty")]
    EmptyTopic,
    #[error("session {session_id} does not share dedup key {expected_key}")]
    ScopeMismatch { session_id: String, expected_key: String },
}

/// Compiles same-scope sessions into a typed, token-sized Dedup slice.
#[derive(Debug, Clone)]
pub struct DedupCompiler<E> {
    estimator: E,
}

impl<E> DedupCompiler<E>
where
    E: TokenEstimator,
{
    /// Create a compiler backed by the given token estimator.
    pub const fn new(estimator: E) -> Self {
        Self { estimator }
    }

    /// Build a manifest, preserving source order and omitting duplicate members.
    ///
    /// # Errors
    /// Returns an error for an empty input/topic or when sessions span different
    /// working-directory scopes.
    pub fn compile(
        &self,
        sessions: &[Session],
        topic_slug: &str,
    ) -> Result<Bundle, DedupCompileError> {
        let first = sessions.first().ok_or(DedupCompileError::EmptySessions)?;
        let topic_slug = topic_slug.trim().to_lowercase();
        if topic_slug.is_empty() {
            return Err(DedupCompileError::EmptyTopic);
        }

        let dedup_key = DedupKey::derive(first, &topic_slug);
        let mut members = Vec::new();

        for session in sessions {
            if DedupKey::derive(session, &topic_slug) != dedup_key {
                return Err(DedupCompileError::ScopeMismatch {
                    session_id: session.id.clone(),
                    expected_key: dedup_key.as_str().to_owned(),
                });
            }

            let member = DedupMember { session_id: session.id.clone(), corpus: session.corpus };
            if !members.contains(&member) {
                members.push(member);
            }
        }

        let body = serde_json::json!({
            "dedup_key": dedup_key,
            "topic_slug": topic_slug,
            "sessions": members,
        });
        let token_estimate = self.estimator.estimate_json(&body);

        Ok(Bundle { kind: BundleKind::Dedup, token_estimate, body })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distill::token_estimator::CharCountTokenEstimator;
    use crate::domain::dedup::DedupManifest;
    use crate::domain::session::Corpus;

    fn session(id: &str, cwd: &str, corpus: Corpus) -> Session {
        let mut session = Session::new(id, corpus);
        session.cwd = Some(cwd.into());
        session
    }

    #[test]
    fn compiler_emits_structured_manifest() {
        let sessions =
            [session("one", "/repo", Corpus::Forge), session("two", "/repo", Corpus::Cursor)];

        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, " Fix-Login ")
            .expect("same-scope sessions should compile");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");

        assert_eq!(bundle.kind, BundleKind::Dedup);
        assert_eq!(manifest.topic_slug, "fix-login");
        assert_eq!(manifest.sessions.len(), 2);
        assert_eq!(manifest.sessions[0].session_id, "one");
        assert_eq!(manifest.sessions[1].corpus, Corpus::Cursor);
        assert_eq!(manifest.dedup_key.as_str().len(), 64);
        assert!(bundle.token_estimate > 0);
    }

    #[test]
    fn duplicate_member_is_recorded_once() {
        let member = session("one", "/repo", Corpus::Forge);
        let bundle = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&[member.clone(), member], "topic")
            .expect("duplicate input should compile");
        let manifest: DedupManifest =
            serde_json::from_value(bundle.body).expect("manifest should deserialize");

        assert_eq!(manifest.sessions.len(), 1);
    }

    #[test]
    fn compiler_rejects_mixed_scopes() {
        let sessions =
            [session("one", "/repo-a", Corpus::Forge), session("two", "/repo-b", Corpus::Forge)];

        let error = DedupCompiler::new(CharCountTokenEstimator)
            .compile(&sessions, "topic")
            .expect_err("mixed scopes must be rejected");

        assert!(matches!(
            error,
            DedupCompileError::ScopeMismatch { session_id, .. } if session_id == "two"
        ));
    }

    #[test]
    fn compiler_rejects_empty_inputs() {
        let compiler = DedupCompiler::new(CharCountTokenEstimator);
        assert_eq!(compiler.compile(&[], "topic"), Err(DedupCompileError::EmptySessions));
    }

    #[test]
    fn compiler_rejects_blank_topic() {
        let compiler = DedupCompiler::new(CharCountTokenEstimator);
        assert_eq!(
            compiler.compile(&[session("one", "/repo", Corpus::Forge)], "  "),
            Err(DedupCompileError::EmptyTopic)
        );
    }
}
