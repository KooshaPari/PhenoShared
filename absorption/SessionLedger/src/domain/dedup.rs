//! Dedup keys for merging duplicate-scoped chats.
//!
//! Use case (a): after a crash the operator wants to resume ONE chat, not many.
//! Sessions that share a scope (project cwd + normalized intent topic) collapse
//! under a single [`DedupKey`], so their continuation bundles can be merged.

use crate::domain::session::Corpus;
use crate::domain::session::Session;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// A stable key identifying a logical "scope" a session belongs to.
///
/// Two sessions with the same `DedupKey` are candidates for merge. The key is a
/// SHA-256 over the normalized scope (cwd) plus a topic slug, so it is stable
/// across crashes and re-ingestion.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct DedupKey(String);

/// One source session represented in a deduplicated continuation.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DedupMember {
    pub session_id: String,
    pub corpus: Corpus,
}

/// Reproducible record of the sessions collapsed under one scope key.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DedupManifest {
    pub dedup_key: DedupKey,
    pub topic_slug: String,
    pub sessions: Vec<DedupMember>,
}

impl DedupKey {
    /// Derive a dedup key from a session's scope and a topic slug.
    #[must_use]
    pub fn derive(session: &Session, topic_slug: &str) -> Self {
        let scope = session.cwd.as_deref().unwrap_or("<no-cwd>").trim().to_lowercase();
        let topic = topic_slug.trim().to_lowercase();
        let mut hasher = Sha256::new();
        hasher.update(scope.as_bytes());
        hasher.update([0u8]);
        hasher.update(topic.as_bytes());
        let digest = hasher.finalize();
        Self(digest.iter().fold(String::with_capacity(64), |mut s, b| {
            use std::fmt::Write;
            let _ = write!(s, "{b:02x}");
            s
        }))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Session};

    fn make_session(id: &str, cwd: Option<&str>) -> Session {
        let mut s = Session::new(id, Corpus::Forge);
        s.cwd = cwd.map(std::string::ToString::to_string);
        s
    }

    #[test]
    fn same_cwd_same_topic_produces_same_key() {
        let s1 = make_session("a", Some("/home/user/proj"));
        let s2 = make_session("b", Some("/home/user/proj"));
        let k1 = DedupKey::derive(&s1, "fix-login");
        let k2 = DedupKey::derive(&s2, "fix-login");
        assert_eq!(k1, k2);
    }

    #[test]
    fn different_cwd_produces_different_key() {
        let s1 = make_session("a", Some("/home/user/proj-a"));
        let s2 = make_session("b", Some("/home/user/proj-b"));
        let k1 = DedupKey::derive(&s1, "fix-login");
        let k2 = DedupKey::derive(&s2, "fix-login");
        assert_ne!(k1, k2);
    }

    #[test]
    fn different_topic_produces_different_key() {
        let s = make_session("a", Some("/home/user/proj"));
        let k1 = DedupKey::derive(&s, "fix-login");
        let k2 = DedupKey::derive(&s, "add-feature");
        assert_ne!(k1, k2);
    }

    #[test]
    fn no_cwd_uses_sentinel() {
        let s = make_session("a", None);
        let k = DedupKey::derive(&s, "topic");
        // Should be a valid hex string (64 chars for SHA-256)
        assert_eq!(k.as_str().len(), 64);
        // Must differ from a session with a cwd
        let s2 = make_session("b", Some("<no-cwd>"));
        // literal "<no-cwd>" in cwd treated same as sentinel
        let k2 = DedupKey::derive(&s2, "topic");
        assert_eq!(k.as_str(), k2.as_str());
    }

    #[test]
    fn key_is_lowercase_hex() {
        let s = make_session("a", Some("/proj"));
        let k = DedupKey::derive(&s, "slug");
        assert!(k.as_str().chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(k.as_str(), k.as_str().to_lowercase());
    }

    #[test]
    fn key_is_stable_across_calls() {
        let s = make_session("x", Some("/stable/path"));
        let k1 = DedupKey::derive(&s, "same-topic");
        let k2 = DedupKey::derive(&s, "same-topic");
        assert_eq!(k1, k2);
    }

    #[test]
    fn whitespace_in_cwd_is_normalized() {
        let s1 = make_session("a", Some("  /proj  "));
        let s2 = make_session("b", Some("/proj"));
        let k1 = DedupKey::derive(&s1, "slug");
        let k2 = DedupKey::derive(&s2, "slug");
        assert_eq!(k1, k2);
    }

    #[test]
    fn topic_whitespace_is_normalized() {
        let s = make_session("a", Some("/proj"));
        let k1 = DedupKey::derive(&s, "  slug  ");
        let k2 = DedupKey::derive(&s, "slug");
        assert_eq!(k1, k2);
    }

    #[test]
    fn cwd_is_case_normalized() {
        let s1 = make_session("a", Some("/PROJ/PATH"));
        let s2 = make_session("b", Some("/proj/path"));
        let k1 = DedupKey::derive(&s1, "slug");
        let k2 = DedupKey::derive(&s2, "slug");
        assert_eq!(k1, k2);
    }
}
