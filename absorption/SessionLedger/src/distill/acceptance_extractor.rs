//! Heuristic acceptance extraction — the P3 adapter for [`AcceptanceExtractor`].
//!
//! This adapter uses lightweight string matching to extract acceptance evidence
//! — what proof exists that the session's work was verified or completed —
//! from a session's message stream.
//!
//! Acceptance is the *evidence / state of satisfaction*: passing tests, user
//! confirmations, completed goals, error-free runs. This is distinct from
//! [`Contract`](crate::domain::contract::Contract), which holds the *criteria*
//! themselves.

use crate::domain::acceptance::Acceptance;
use crate::domain::session::{Role, Session};
use crate::ports::{AcceptanceExtractor, PortError};

/// Heuristic-based acceptance extractor.
///
/// Scans user and assistant messages for:
/// - **Evidence**: statements about test results, build success, verification.
/// - **User confirmation**: phrases like "looks good", "approved", "ship it".
/// - **Testing evidence**: explicit test-output-like patterns
///   (e.g. "tests pass", "errors: 0", "build succeeded").
///
/// The satisfaction score is derived from the density of positive confirmation
/// signals in the session.
#[derive(Debug, Default, Clone, Copy)]
pub struct HeuristicAcceptanceExtractor;

// Patterns for general completion / verification evidence.
const EVIDENCE_PATTERNS: &[&str] = &[
    "all tests pass",
    "all tests passing",
    "tests pass",
    "tests passing",
    "build succeeded",
    "build passes",
    "build successful",
    "compiles",
    "compilation successful",
    "checks passed",
    "all checks pass",
    "lint passes",
    "lint clean",
    "no errors",
    "errors: 0",
    "0 failures",
    "zero failures",
    "ci passes",
    "ci passed",
    "verification passed",
    "all good",
    "works correctly",
    "everything works",
    "everything compiles",
    "done with",
    "completed",
    "finished",
    "implementation complete",
    "resolved",
    "fixed",
    "this is done",
];

// Patterns for user confirmation signals that specifically indicate acceptance.
const USER_CONFIRMATION_PATTERNS: &[&str] = &[
    "looks good",
    "looks great",
    "looks correct",
    "that's correct",
    "that works",
    "approved",
    "ship it",
    "good to go",
    "lgtm",
    "nice work",
    "perfect",
    "exactly what i wanted",
    "thank you",
    "thanks",
    "confirmed",
    "this works",
    "working",
    "works for me",
    "i'm satisfied",
];

// Patterns for explicit test / verification evidence.
const TESTING_EVIDENCE_PATTERNS: &[&str] = &[
    "test",
    "tests pass",
    "tests passing",
    "test pass",
    "test passing",
    "cargo test",
    "npm test",
    "pytest",
    "verify",
    "verification",
    "assertion",
    "assert",
    "coverage",
    "benchmark",
];

impl HeuristicAcceptanceExtractor {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    /// Heuristically extract acceptance evidence from a session's messages.
    ///
    /// This is factored as a public associated function so it can be used
    /// directly by the compiler without going through the trait when no
    /// adapter injection is needed (P3 default).
    #[must_use]
    pub fn extract_acceptance(session: &Session) -> Acceptance {
        let mut evidence: Vec<String> = Vec::new();
        let mut user_confirmed = false;
        let mut testing_evidence: Vec<String> = Vec::new();
        let mut confirmation_count: usize = 0;

        for msg in &session.messages {
            let lower = msg.content.to_lowercase();

            // --- General evidence ---
            for pat in EVIDENCE_PATTERNS {
                if lower.contains(pat) {
                    let ev = format!("Evidence: '{pat}'");
                    if !evidence.contains(&ev) {
                        evidence.push(ev);
                        // Count toward satisfaction
                        confirmation_count += 1;
                    }
                }
            }

            // --- User confirmation (only user messages) ---
            if msg.role == Role::User {
                for pat in USER_CONFIRMATION_PATTERNS {
                    if lower.contains(pat) {
                        user_confirmed = true;
                        confirmation_count += 1;
                        break; // one confirmation is enough
                    }
                }
            }

            // --- Testing evidence ---
            for pat in TESTING_EVIDENCE_PATTERNS {
                if lower.contains(pat) {
                    let te = format!("Testing: '{pat}'");
                    if !testing_evidence.contains(&te) {
                        testing_evidence.push(te);
                    }
                }
            }
        }

        // Heuristic satisfaction score: clamp to 0–100.
        // Base: 10 per confirmation up to max 100.
        let satisfaction_score: u8 =
            u8::try_from(confirmation_count.saturating_mul(10)).unwrap_or(100).min(100);

        // Dedup testing evidence.
        testing_evidence.sort();
        testing_evidence.dedup();

        // Dedup evidence.
        evidence.sort();
        evidence.dedup();

        Acceptance { evidence, user_confirmed, testing_evidence, satisfaction_score }
    }
}

impl AcceptanceExtractor for HeuristicAcceptanceExtractor {
    fn extract(&self, session: &Session) -> Result<Acceptance, PortError> {
        Ok(Self::extract_acceptance(session))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::session::{Corpus, Message, Role};

    fn fixture_session_with_evidence() -> Session {
        let mut s = Session::new("test-sess-acc", Corpus::Forge);
        s.messages.push(Message::new(Role::Assistant, "All tests pass. Build succeeded."));
        s.messages.push(Message::new(Role::Assistant, "No errors in lint check."));
        s.messages.push(Message::new(Role::User, "Looks good, approved!"));
        s
    }

    fn fixture_session_mixed() -> Session {
        let mut s = Session::new("test-sess-mixed", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "fix the login bug"));
        s.messages.push(Message::new(Role::Assistant, "here's the fix"));
        s.messages.push(Message::new(Role::User, "tests pass now, thanks"));
        s
    }

    fn fixture_session_no_signals() -> Session {
        let mut s = Session::new("test-sess-none", Corpus::Forge);
        s.messages.push(Message::new(Role::User, "can you refactor this module"));
        s.messages.push(Message::new(Role::Assistant, "sure, working on it"));
        s
    }

    #[test]
    fn extracts_evidence_from_test_and_build_signals() {
        let acc =
            HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_with_evidence());
        assert!(acc.evidence.iter().any(|e| e.contains("all tests pass")));
        assert!(acc.evidence.iter().any(|e| e.contains("build succeeded")));
        assert!(acc.evidence.iter().any(|e| e.contains("no errors")));
    }

    #[test]
    fn detects_user_confirmation() {
        let acc =
            HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_with_evidence());
        assert!(acc.user_confirmed, "user said 'looks good, approved'");
    }

    #[test]
    fn extracts_testing_evidence() {
        let acc =
            HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_with_evidence());
        assert!(acc.testing_evidence.iter().any(|t| t.contains("test")));
    }

    #[test]
    fn satisfaction_score_is_nonzero_for_valid_session() {
        let acc =
            HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_with_evidence());
        assert!(acc.satisfaction_score > 0, "score should be > 0 with evidence");
        assert!(acc.satisfaction_score <= 100);
    }

    #[test]
    fn returns_empty_for_no_signals() {
        let acc = HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_no_signals());
        assert!(acc.is_empty());
        assert!(!acc.user_confirmed);
        assert_eq!(acc.satisfaction_score, 0);
    }

    #[test]
    fn detects_confirmation_from_user_messages_only() {
        let acc = HeuristicAcceptanceExtractor::extract_acceptance(&fixture_session_mixed());
        assert!(acc.user_confirmed, "user said 'thanks'");
        assert!(acc.testing_evidence.iter().any(|t| t.contains("test")));
    }

    #[test]
    fn empty_session_returns_empty() {
        let s = Session::new("empty", Corpus::Forge);
        let acc = HeuristicAcceptanceExtractor::extract_acceptance(&s);
        assert!(acc.is_empty());
    }

    #[test]
    fn acceptance_extractor_trait_works() {
        let extractor = HeuristicAcceptanceExtractor::new();
        let acc =
            extractor.extract(&fixture_session_with_evidence()).expect("extraction should succeed");
        assert!(acc.user_confirmed);
    }
}
