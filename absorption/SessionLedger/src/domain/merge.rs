//! Duplicate-scoped session merging and lost-work localization.

use super::bundle::{BundleKind, ContinuationBundle};
use super::dedup::{DedupKey, DedupManifest, DedupMember};
use super::session::{Message, Session};
use super::worklog::{project_unfinished_work, UnfinishedWorkItem, WorklogProjection};

/// Message ordering used when combining source sessions.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum MergeMessageOrder {
    /// Sort timestamped messages chronologically, retaining canonical source
    /// order for equal timestamps. Untimestamped messages follow them.
    #[default]
    Chronological,
    /// Concatenate messages in canonical source-session order.
    Session,
}

/// The output of a duplicate-scoped merge.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MergeResult {
    pub session: Session,
    pub manifest: DedupManifest,
}

/// Validation failures from duplicate-scoped session merging.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum MergeError {
    #[error("at least one session is required")]
    EmptySessions,
    #[error("topic slug must not be empty")]
    EmptyTopic,
    #[error("session {session_id} does not share dedup key {expected_key}")]
    ScopeMismatch { session_id: String, expected_key: String },
    #[error("derived dedup key {actual_key} does not match expected key {expected_key}")]
    KeyMismatch { expected_key: String, actual_key: String },
}

/// Deterministically merges sessions that share a dedup scope.
#[derive(Debug, Clone, Copy, Default)]
pub struct MergeExecutor {
    message_order: MergeMessageOrder,
}

impl MergeExecutor {
    /// Create an executor using the requested message order.
    #[must_use]
    pub const fn new(message_order: MergeMessageOrder) -> Self {
        Self { message_order }
    }

    /// Merge sessions using a key derived from their normalized cwd and topic.
    ///
    /// The merged session ID is the dedup key. Its corpus, cwd, and fallback
    /// title come from the first canonical member. The manifest records every
    /// unique `(session_id, corpus)` member so the merge remains reversible.
    ///
    /// # Errors
    /// Returns an error for empty input/topic or sessions in different scopes.
    pub fn merge(self, sessions: &[Session], topic_slug: &str) -> Result<MergeResult, MergeError> {
        self.merge_inner(sessions, topic_slug, None)
    }

    /// Merge sessions while requiring the derived key to match `expected_key`.
    ///
    /// # Errors
    /// Returns the errors documented by [`Self::merge`], plus
    /// [`MergeError::KeyMismatch`] when the supplied key is not the scope key.
    pub fn merge_with_key(
        self,
        sessions: &[Session],
        topic_slug: &str,
        expected_key: &DedupKey,
    ) -> Result<MergeResult, MergeError> {
        self.merge_inner(sessions, topic_slug, Some(expected_key))
    }

    fn merge_inner(
        self,
        sessions: &[Session],
        topic_slug: &str,
        expected_key: Option<&DedupKey>,
    ) -> Result<MergeResult, MergeError> {
        let topic_slug = topic_slug.trim().to_lowercase();
        if topic_slug.is_empty() {
            return Err(MergeError::EmptyTopic);
        }

        let first = sessions.first().ok_or(MergeError::EmptySessions)?;
        let dedup_key = DedupKey::derive(first, &topic_slug);
        if let Some(expected_key) = expected_key {
            if expected_key != &dedup_key {
                return Err(MergeError::KeyMismatch {
                    expected_key: expected_key.as_str().to_owned(),
                    actual_key: dedup_key.as_str().to_owned(),
                });
            }
        }

        for session in sessions {
            if DedupKey::derive(session, &topic_slug) != dedup_key {
                return Err(MergeError::ScopeMismatch {
                    session_id: session.id.clone(),
                    expected_key: dedup_key.as_str().to_owned(),
                });
            }
        }

        let mut canonical = sessions.iter().collect::<Vec<_>>();
        canonical.sort_by(|left, right| {
            left.id.cmp(&right.id).then_with(|| left.corpus.as_str().cmp(right.corpus.as_str()))
        });
        canonical.dedup_by(|left, right| left.id == right.id && left.corpus == right.corpus);

        let canonical_first = canonical[0];
        let mut messages = canonical
            .iter()
            .flat_map(|session| session.messages.iter().cloned())
            .collect::<Vec<Message>>();
        if self.message_order == MergeMessageOrder::Chronological {
            messages.sort_by_key(|message| (message.ts_ms.is_none(), message.ts_ms));
        }

        let members = canonical
            .iter()
            .map(|session| DedupMember { session_id: session.id.clone(), corpus: session.corpus })
            .collect();
        let manifest = DedupManifest {
            dedup_key: dedup_key.clone(),
            topic_slug: topic_slug.clone(),
            sessions: members,
        };
        let session = Session {
            id: dedup_key.as_str().to_owned(),
            corpus: canonical_first.corpus,
            cwd: canonical_first.cwd.clone(),
            title: canonical_first.title.clone().or(Some(topic_slug)),
            messages,
        };

        Ok(MergeResult { session, manifest })
    }
}

/// Failures while reading unfinished-work projections from bundles.
#[derive(Debug, thiserror::Error)]
pub enum LostWorkError {
    #[error("invalid worklog in continuation bundle {source_id}: {source}")]
    InvalidWorklog {
        source_id: String,
        #[source]
        source: serde_json::Error,
    },
}

/// Projects outstanding items from every source in a merge set.
#[derive(Debug, Clone, Copy, Default)]
pub struct LostWorkLocalizer;

impl LostWorkLocalizer {
    /// Localize unfinished work directly from normalized source sessions.
    #[must_use]
    pub fn from_sessions(sessions: &[Session]) -> Vec<UnfinishedWorkItem> {
        canonicalize_items(project_unfinished_work(sessions))
    }

    /// Localize unfinished work from `Worklog` slices in continuation bundles.
    ///
    /// # Errors
    /// Returns an error when a `Worklog` slice is not a valid
    /// [`WorklogProjection`].
    pub fn from_bundles(
        bundles: &[ContinuationBundle],
    ) -> Result<Vec<UnfinishedWorkItem>, LostWorkError> {
        let mut items = Vec::new();
        for bundle in bundles {
            for slice in bundle.bundles.iter().filter(|slice| slice.kind == BundleKind::Worklog) {
                let projection: WorklogProjection = serde_json::from_value(slice.body.clone())
                    .map_err(|source| LostWorkError::InvalidWorklog {
                        source_id: bundle.source_id.clone(),
                        source,
                    })?;
                items.extend(projection.unfinished);
            }
        }
        Ok(canonicalize_items(items))
    }
}

fn canonicalize_items(mut items: Vec<UnfinishedWorkItem>) -> Vec<UnfinishedWorkItem> {
    items.sort_by(|left, right| {
        left.session_id
            .cmp(&right.session_id)
            .then_with(|| left.corpus.as_str().cmp(right.corpus.as_str()))
            .then_with(|| left.summary.cmp(&right.summary))
    });
    items.dedup();
    items
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};

    fn session(id: &str, corpus: Corpus, cwd: &str, messages: &[(&str, Option<i64>)]) -> Session {
        let mut session = Session::new(id, corpus);
        session.cwd = Some(cwd.into());
        session.messages = messages
            .iter()
            .map(|(content, ts_ms)| Message {
                role: Role::User,
                content: (*content).into(),
                ts_ms: *ts_ms,
            })
            .collect();
        session
    }

    #[test]
    fn merge_is_canonical_and_chronological() {
        let beta = session("beta", Corpus::Cursor, "/repo", &[("later", Some(20))]);
        let alpha =
            session("alpha", Corpus::Forge, "/repo", &[("earlier", Some(10)), ("unknown", None)]);

        let result = MergeExecutor::default()
            .merge(&[beta, alpha], " Fix-Login ")
            .expect("same-scope sessions should merge");

        assert_eq!(result.session.id, result.manifest.dedup_key.as_str());
        assert_eq!(result.manifest.topic_slug, "fix-login");
        assert_eq!(
            result
                .manifest
                .sessions
                .iter()
                .map(|member| member.session_id.as_str())
                .collect::<Vec<_>>(),
            ["alpha", "beta"]
        );
        assert_eq!(
            result
                .session
                .messages
                .iter()
                .map(|message| message.content.as_str())
                .collect::<Vec<_>>(),
            ["earlier", "later", "unknown"]
        );
    }

    #[test]
    fn session_order_concatenates_canonical_members() {
        let beta = session("beta", Corpus::Cursor, "/repo", &[("b", Some(1))]);
        let alpha = session("alpha", Corpus::Forge, "/repo", &[("a", Some(2))]);

        let result = MergeExecutor::new(MergeMessageOrder::Session)
            .merge(&[beta, alpha], "topic")
            .expect("same-scope sessions should merge");

        assert_eq!(result.session.messages[0].content, "a");
        assert_eq!(result.session.messages[1].content, "b");
    }

    #[test]
    fn merge_rejects_mixed_scopes_and_wrong_key() {
        let one = session("one", Corpus::Forge, "/one", &[]);
        let two = session("two", Corpus::Forge, "/two", &[]);
        assert!(matches!(
            MergeExecutor::default().merge(&[one.clone(), two], "topic"),
            Err(MergeError::ScopeMismatch { session_id, .. }) if session_id == "two"
        ));

        let wrong_key = DedupKey::derive(&one, "other-topic");
        assert!(matches!(
            MergeExecutor::default().merge_with_key(&[one], "topic", &wrong_key),
            Err(MergeError::KeyMismatch { .. })
        ));
    }

    #[test]
    fn duplicate_members_are_merged_once() {
        let source = session("one", Corpus::Forge, "/repo", &[("once", Some(1))]);
        let result = MergeExecutor::default()
            .merge(&[source.clone(), source], "topic")
            .expect("duplicate inputs should merge");

        assert_eq!(result.manifest.sessions.len(), 1);
        assert_eq!(result.session.messages.len(), 1);
    }

    #[test]
    fn localizer_rejects_invalid_worklog() {
        let mut bundle = ContinuationBundle::new("broken");
        bundle.push(super::super::bundle::Bundle::new(
            BundleKind::Worklog,
            serde_json::json!({"unfinished": "not-a-list"}),
        ));

        assert!(matches!(
            LostWorkLocalizer::from_bundles(&[bundle]),
            Err(LostWorkError::InvalidWorklog { source_id, .. }) if source_id == "broken"
        ));
    }
}
